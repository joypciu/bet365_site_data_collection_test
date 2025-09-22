import asyncio
import logging
import re
from typing import Dict, List, Optional
from ..models.match import Match
from ..models.odds import Odds
from ..utils.dynamic_detection import detect_sport_dynamically, detect_league_dynamically, learn_team_patterns
from ..utils.dynamic_detection import league_detector
from .odds_parser import OddsParser

class HTMLParser:
    """Parse HTML content to extract match and odds data"""
    
    def __init__(self):
        self.odds_parser = OddsParser()
    
    async def parse_html_data(self, page, source_url: str, sport: Optional[str] = None) -> List[Match]:
        """Parse HTML page data to extract matches and odds"""
        matches = []
        
        try:
            # Wait for page to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Use sport parameter if provided, otherwise extract from URL
            if not sport:
                sport = self._get_sport_from_url(source_url)
                logging.debug(f"[DEBUG] Extracted sport from URL {source_url}: {sport}")
            else:
                logging.debug(f"[DEBUG] Using provided sport parameter: {sport}")
            
            # Look for match containers with various selectors
            match_selectors = [
                '.gl-MarketGroup',
                '.cpm-ParticipantOdds',
                '.ovm-ParticipantStackedCentered',
                '[aria-label*="@"]',
                '[aria-label*=" v "]'
            ]
            
            total_elements = 0
            for selector in match_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        total_elements += len(elements)
                        logging.info(f"[+] Found {len(elements)} elements with selector: {selector}")
                        matches.extend(await self._extract_matches_from_elements(elements, sport, source_url))
                except Exception as e:
                    logging.warning(f"Error with selector {selector}: {e}")
                    continue
            
            # Remove duplicates based on match_id
            unique_matches = {}
            for match in matches:
                if match.match_id not in unique_matches:
                    unique_matches[match.match_id] = match
                else:
                    # Merge odds if same match found multiple times
                    existing_match = unique_matches[match.match_id]
                    existing_match.update_odds(match.odds)
            
            logging.info(f"[+] Found {total_elements} total elements, extracted {len(unique_matches)} unique matches from {source_url}")
            return list(unique_matches.values())
            
        except Exception as e:
            logging.error(f"[!] Error parsing HTML data: {e}")
            return []
    
    async def _extract_matches_from_elements(self, elements, sport: str, source_url: str) -> List[Match]:
        """Extract matches from HTML elements"""
        matches = []
        processed_matches = {}  # Track unique matches by team pairs
        
        for i, element in enumerate(elements):
            try:
                # Get aria-label for odds parsing
                aria_label = await element.get_attribute('aria-label')
                if not aria_label:
                    continue
                
                # Skip if aria-label doesn't contain team information
                if not ('@' in aria_label or ' v ' in aria_label):
                    continue
                
                # Parse odds from aria-label
                odds_data = self.odds_parser.parse_aria_label_odds(aria_label)
                if not odds_data:
                    continue
                
                # Extract team names
                home_team = odds_data.get('home_team', 'Unknown')
                away_team = odds_data.get('away_team', 'Unknown')
                
                if home_team == 'Unknown' or away_team == 'Unknown':
                    continue
                
                # Clean team names
                home_team = self._clean_team_name(home_team)
                away_team = self._clean_team_name(away_team)
                
                # Skip if team names are invalid after cleaning
                if home_team == 'Unknown' or away_team == 'Unknown':
                    continue
                
                # Skip if teams are the same (invalid data)
                if home_team.lower() == away_team.lower():
                    continue
                
                # Create unique match identifier based on teams
                team_pair = tuple(sorted([home_team.lower(), away_team.lower()]))
                
                # Dynamically detect sport and league
                detected_sport = detect_sport_dynamically(
                    text=aria_label, 
                    url=source_url, 
                    teams=[home_team, away_team]
                )
                final_sport = detected_sport if detected_sport != 'Unknown' else (sport or 'Unknown')
                
                detected_league = detect_league_dynamically(
                    home_team=home_team,
                    away_team=away_team,
                    sport=final_sport,
                    context=aria_label
                )

                # If league implies a different sport (e.g., NBA) adjust sport
                implied_sport = league_detector.get_sport_for_league(detected_league)
                if implied_sport and implied_sport != final_sport:
                    final_sport = implied_sport

                # If source_url explicitly only contains one sport code (e.g., B13 for Soccer)
                # and implied sport differs, we may choose to skip to enforce purity
                import re
                found_codes = re.findall(r'B\d+', source_url)
                single_code_only = len(found_codes) == 1 and found_codes[0] == 'B13'
                if single_code_only and final_sport != 'Soccer':
                    # Skip cross-sport noise for a single-sport scrape
                    continue
                
                # Learn patterns for future detection
                learn_team_patterns(final_sport, home_team, away_team, detected_league)
                
                # Check if we already have this match
                if team_pair in processed_matches:
                    # Merge odds into existing match
                    existing_match = processed_matches[team_pair]
                    existing_match.update_odds(odds_data)
                else:
                    # Create new match
                    # Extract match time heuristic
                    match_time = self._extract_match_time(aria_label)
                    match = Match.create(
                        home_team=home_team,
                        away_team=away_team,
                        league=detected_league,
                        sport=final_sport,
                        match_time=match_time,
                        source_url=source_url
                    )
                    
                    # Add odds to match
                    match.update_odds(odds_data)
                    processed_matches[team_pair] = match
                    matches.append(match)
                    
                    logging.debug(f"[DYNAMIC] {home_team} vs {away_team} -> Sport: {final_sport}, League: {detected_league}")
                
            except Exception as e:
                logging.warning(f"Error extracting match from element {i}: {e}")
                continue
        
        return matches
    
    def _clean_team_name(self, team_name: str) -> str:
        """Clean and normalize team names"""
        if not team_name:
            return "Unknown"
        
        # Check for parsing errors - if team name contains betting terms, it's likely an error
        betting_terms = ['total', 'over', 'under', 'spread', 'moneyline', 'money', 'point', '@', '+', '-']
        team_lower = team_name.lower()
        
        # If the team name contains multiple betting terms or is very long, it's likely a parsing error
        betting_term_count = sum(1 for term in betting_terms if term in team_lower)
        if betting_term_count > 1 or len(team_name) > 30:
            return "Unknown"
        
        # Reject if it's just a number or short betting term
        if re.match(r'^\s*[+-]?\d+(\.\d+)?\s*$', team_name.strip()):
            return "Unknown"
        
        # Reject very short names that are just numbers or single characters
        cleaned = team_name.strip()
        if len(cleaned) < 2 or re.match(r'^\d+$', cleaned):
            return "Unknown"
        
        # Clean the name
        cleaned = team_name.strip()
        
        # Remove content in parentheses (may appear multiple times like ((Pitcher)))
        cleaned = re.sub(r'\([^)]*\)', '', cleaned).strip()
        # Collapse multiple spaces
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        
        # Remove trailing odds-like patterns
        cleaned = re.sub(r'\s+[+-]?\d+(?:\.\d+)?$', '', cleaned)
        
        # Reject overly short fragments (e.g., 'CLE', 'ATL') when they are just 2-3 letters and not standard team abbreviations we want.
        # Allow three-letter if part of pattern like 'WAS Nationals' handled earlier; here we check if it's only the fragment.
        if len(cleaned) <= 3 and cleaned.isalpha() and not any(keyword in team_lower for keyword in ['psg', 'psv', 'ac', 'fc', 'sc', 'fc']):
            return "Unknown"
        
        return cleaned.strip() if cleaned.strip() else "Unknown"
    
    def _get_sport_from_url(self, url: str) -> str:
        """Extract sport from URL"""
        from ..utils.constants import SPORT_CODES
        if not url:
            return 'Unknown'
        import re
        found_codes = re.findall(r'B\d+', url)
        for code in reversed(found_codes):
            if code in SPORT_CODES:
                return SPORT_CODES[code]
        return 'Unknown'

    def _extract_match_time(self, text: str) -> str:
        """Heuristic extraction of match time from aria-label text"""
        import re
        # Common time patterns: 12:30, 7:05 PM, 19:30, 7:05 ET, Today 15:00, Tomorrow 20:00
        time_patterns = [
            r'\b(?:Today|Tomorrow|Yesterday)\s+(\d{1,2}:\d{2})\b',
            r'\b(\d{1,2}:\d{2}\s?(?:AM|PM|ET|GMT|UTC)?)\b',
            r'\b(\d{1,2}:\d{2})\b'
        ]
        for pattern in time_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                time_str = m.group(1) if len(m.groups()) == 1 else m.group(2)
                return time_str.upper()
        
        # Look for date/time patterns like "2025-09-22 15:00"
        date_time_pattern = r'\b(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})\b'
        m = re.search(date_time_pattern, text)
        if m:
            return m.group(1)
        
        # Look for time patterns with different formats
        extended_patterns = [
            r'(\d{1,2}:\d{2}(?:\s?[AP]M)?)',  # 3:30 PM, 15:30
            r'(\d{1,2}(?::\d{2})?\s?(?:AM|PM|ET|GMT|UTC))',  # 3 PM, 3:30 PM
            r'(?:at|starts?)\s+(\d{1,2}:\d{2})',  # "at 15:30", "starts 20:00"
        ]
        
        for pattern in extended_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                time_str = m.group(1)
                return time_str.upper()
            
        return 'unknown'