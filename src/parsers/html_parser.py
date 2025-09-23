import asyncio
import logging
import re
import time
import uuid
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from ..models.match import Match
from ..models.odds import Odds
from ..utils.dynamic_detection import detect_sport_dynamically, detect_league_dynamically, learn_team_patterns
from ..utils.dynamic_detection import league_detector
from .odds_parser import OddsParser

class HTMLParser:
    """Parse HTML content to extract match and odds data"""
    
    def __init__(self):
        self.odds_parser = OddsParser()
        self.logger = logging.getLogger(__name__)
    
    def _generate_unique_id(self) -> str:
        """Generate a unique identifier"""
        return str(uuid.uuid4())[:8]
    
    def _detect_sport_from_text(self, text: str) -> str:
        """Detect sport from text content"""
        try:
            result = detect_sport_dynamically(text=text, url="", teams=[])
            return result if result != 'Unknown' else 'Unknown'
        except Exception:
            return 'Unknown'
    
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
            # Include both prematch and live game selectors
            match_selectors = [
                '.gl-MarketGroup',
                '.cpm-ParticipantOdds',
                '.ovm-ParticipantStackedCentered',
                '[aria-label*="@"]',
                '[aria-label*=" v "]',
                # Live game specific selectors
                '.ipo-ParticipantOdds',
                '.ipo-Participant',
                '.liv-ParticipantOdds',
                '.live-ParticipantOdds',
                '.inplay-ParticipantOdds',
                '[class*="Live"]',
                '[class*="InPlay"]',
                '[class*="Ipo"]',
                # More general selectors for live games
                '[class*="participant" i][aria-label]',
                '[class*="odds" i][aria-label]',
                '[data-testid*="participant"]',
                '[data-testid*="market"]'
            ]
            
            total_elements = 0
            is_live_page = '/IP/' in source_url
            
            for selector in match_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        total_elements += len(elements)
                        page_type = "LIVE" if is_live_page else "PREMATCH"
                        logging.info(f"[+] {page_type} - Found {len(elements)} elements with selector: {selector}")
                        matches.extend(await self._extract_matches_from_elements(elements, sport, source_url))
                    elif is_live_page:
                        # Log when live pages have no elements for debugging
                        logging.debug(f"[LIVE] No elements found with selector: {selector}")
                except Exception as e:
                    logging.warning(f"Error with selector {selector}: {e}")
                    continue
            
            if is_live_page and total_elements == 0:
                logging.warning(f"[LIVE] No elements found with any selector on {source_url}")
                # Try to get page content for debugging
                try:
                    page_title = await page.title()
                    logging.info(f"[LIVE DEBUG] Page title: {page_title}")
                    
                    # Check for common live game indicators
                    live_indicators = [
                        '.live-indicator',
                        '.in-play-indicator', 
                        '[class*="live" i]',
                        '[data-live="true"]',
                        '.score',
                        '.time-remaining'
                    ]
                    
                    found_live_indicators = []
                    for indicator in live_indicators:
                        try:
                            elements = await page.query_selector_all(indicator)
                            if elements:
                                found_live_indicators.append(f"{indicator}: {len(elements)}")
                        except:
                            continue
                    
                    if found_live_indicators:
                        logging.info(f"[LIVE DEBUG] Found live indicators: {', '.join(found_live_indicators)}")
                    else:
                        logging.info(f"[LIVE DEBUG] No live indicators found")
                    
                    # Check if page loaded properly
                    body_text = await page.locator('body').inner_text()
                    body_lower = body_text.lower()
                    
                    if 'no markets' in body_lower or 'no events' in body_lower:
                        logging.info(f"[LIVE] Page indicates no live events available")
                    elif 'live' in body_lower or 'in-play' in body_lower:
                        logging.info(f"[LIVE] Page contains live content but matches not extracted")
                        # Try alternative extraction methods
                        await self._try_alternative_live_extraction(page, source_url)
                    elif len(body_text.strip()) < 100:
                        logging.warning(f"[LIVE] Page appears empty or blocked")
                    else:
                        logging.info(f"[LIVE] Page loaded but no matches found with current selectors")
                        
                except Exception as e:
                    logging.warning(f"[LIVE DEBUG] Could not analyze page content: {e}")
            
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
    
    async def _try_alternative_live_extraction(self, page, source_url: str):
        """Try alternative methods to extract live games"""
        try:
            logging.info("[LIVE] Attempting alternative live game extraction...")
            
            # Look for any elements with odds-like patterns
            alternative_selectors = [
                '[class*="odd" i]',
                '[class*="price" i]', 
                '[class*="bet" i]',
                '[data-price]',
                '[data-odd]',
                'button[class*="odd" i]',
                'span[class*="odd" i]',
                # More generic selectors
                '[role="button"][aria-label]',
                '.market-group',
                '.event-row',
                '.match-row'
            ]
            
            for selector in alternative_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logging.info(f"[LIVE ALT] Found {len(elements)} elements with: {selector}")
                        # Sample a few elements to see their content
                        for i, element in enumerate(elements[:3]):
                            try:
                                aria_label = await element.get_attribute('aria-label')
                                text_content = await element.inner_text()
                                if aria_label or text_content:
                                    logging.info(f"[LIVE ALT] Sample {i+1}: {aria_label or text_content[:50]}")
                            except:
                                continue
                except Exception as e:
                    continue
                    
        except Exception as e:
            logging.warning(f"[LIVE ALT] Alternative extraction failed: {e}")
    
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
                
                # Extract team names first
                home_team = odds_data.get('home_team', 'Unknown')
                away_team = odds_data.get('away_team', 'Unknown')
                
                if home_team == 'Unknown' or away_team == 'Unknown':
                    continue
                
                # Extract line IDs from element attributes using team names
                line_id = self._extract_line_id(element, aria_label, home_team, away_team)
                money_line_id = self._extract_money_line_id(element, aria_label, home_team, away_team)
                
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
                    
                    # Determine if this is a live match from URL
                    is_live_match = '/IP/' in source_url
                    match_type = 'live' if is_live_match else 'prematch'
                    
                    match = Match.create(
                        home_team=home_team,
                        away_team=away_team,
                        league=detected_league,
                        sport=final_sport,
                        match_time=match_time,
                        source_url=source_url,
                        line_id=line_id,
                        money_line_id=money_line_id,
                        match_type=match_type
                    )
                    
                    # Set live game properties
                    if is_live_match:
                        match.is_live = True
                        match.match_type = 'live'
                    
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
    
    def _extract_line_id(self, element, aria_label: str = "", home_team: str = "", away_team: str = "") -> Optional[str]:
        """Extract line ID from bet365 element attributes or generate human-readable ID"""
        try:
            # Common bet365 line ID attributes - check without await for synchronous access
            for attr in ['data-line-id', 'data-id', 'data-fixture-id', 'data-market-id', 'id']:
                if hasattr(element, 'get') and element.get(attr):
                    return str(element.get(attr))
            
            # For playwright elements, try to access attributes differently
            if hasattr(element, 'evaluate'):
                try:
                    # Get all attributes using JavaScript evaluation
                    attrs_js = """
                    (element) => {
                        const attrs = {};
                        for (let attr of element.attributes) {
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    }
                    """
                    # This is still async, so we'll use a different approach
                    pass
                except:
                    pass
            
            # Try to extract from class names or other text-based attributes
            class_name = ""
            if hasattr(element, 'get'):
                class_name = element.get('class') or ""
            
            if class_name:
                # Look for patterns like "line-123456" or "id123456" in class names
                import re
                id_match = re.search(r'(?:line[-_]|id[-_]?)(\d+)', class_name)
                if id_match:
                    return id_match.group(1)
            
            # Generate human-readable line ID using team names
            if home_team and away_team:
                clean_home = self._clean_team_name_for_id(home_team)
                clean_away = self._clean_team_name_for_id(away_team)
                return f"{clean_away}_{clean_home}_line_bet365"
            
            # Fallback: try to extract team names from aria-label
            if aria_label:
                teams = self._extract_teams_from_aria_label(aria_label)
                if teams and len(teams) == 2:
                    clean_away = self._clean_team_name_for_id(teams[0])
                    clean_home = self._clean_team_name_for_id(teams[1])
                    return f"{clean_away}_{clean_home}_line_bet365"
            
            # Final fallback: generate hash-based ID
            if aria_label:
                import hashlib
                line_id = hashlib.md5(aria_label.encode()).hexdigest()[:8]
                return f"line_{line_id}"
            
            return None
        except Exception as e:
            return None
    
    def _extract_money_line_id(self, element, aria_label: str = "", home_team: str = "", away_team: str = "") -> Optional[str]:
        """Extract money line ID from bet365 element attributes or generate human-readable ID"""
        import re
        try:
            # Common bet365 money line ID attributes - check without await
            for attr in ['data-money-line-id', 'data-ml-id', 'data-moneyline-id', 'data-bet-id']:
                if hasattr(element, 'get') and element.get(attr):
                    return str(element.get(attr))
            
            # Try to extract money line ID from aria-label or other text content
            if not aria_label and hasattr(element, 'get') and element.get('aria-label'):
                aria_label = element.get('aria-label')
            
            if aria_label and ('money' in aria_label.lower() or 'ml' in aria_label.lower()):
                # Extract numbers that might be money line IDs
                ml_match = re.search(r'(?:money|ml)[-_]?(\d+)', aria_label, re.IGNORECASE)
                if ml_match:
                    return ml_match.group(1)
            
            # Generate human-readable money line ID if we can identify money line odds
            if aria_label:
                # Look for money line patterns in odds (e.g., "+150", "-110")
                money_pattern = r'[+-]\d+(?!\.\d)'  # Match +150, -110 but not +1.5
                money_matches = re.findall(money_pattern, aria_label)
                if len(money_matches) >= 2:  # At least home and away money lines
                    # Generate human-readable money line ID using team names
                    if home_team and away_team:
                        clean_home = self._clean_team_name_for_id(home_team)
                        clean_away = self._clean_team_name_for_id(away_team)
                        return f"{clean_away}_{clean_home}_moneyline_bet365"
                    
                    # Fallback: try to extract team names from aria-label
                    teams = self._extract_teams_from_aria_label(aria_label)
                    if teams and len(teams) == 2:
                        clean_away = self._clean_team_name_for_id(teams[0])
                        clean_home = self._clean_team_name_for_id(teams[1])
                        return f"{clean_away}_{clean_home}_moneyline_bet365"
                    
                    # Final fallback: hash-based ID
                    import hashlib
                    ml_text = ''.join(money_matches)
                    ml_id = hashlib.md5(ml_text.encode()).hexdigest()[:8]
                    return f"ml_{ml_id}"
            
            return None
        except Exception as e:
            return None
    
    def _clean_team_name_for_id(self, team_name: str) -> str:
        """Clean team name specifically for use in IDs"""
        import re
        if not team_name:
            return ""
        
        # Remove common prefixes and suffixes
        cleaned = team_name.strip()
        
        # Remove parenthetical content like "(M McGreevy)"
        cleaned = re.sub(r'\([^)]*\)', '', cleaned).strip()
        
        # Convert to title case and handle common abbreviations
        words = cleaned.split()
        result_words = []
        
        # Handle multi-word city names first
        text = ' '.join(words)
        city_abbrev_map = {
            'Los Angeles': 'LA', 'New York': 'NY', 'San Francisco': 'SF',
            'San Antonio': 'SA', 'Golden State': 'GS', 'Oklahoma City': 'OKC',
            'New Orleans': 'NO', 'Las Vegas': 'LV'
        }
        
        # Check for multi-word cities
        for city, abbrev in city_abbrev_map.items():
            if text.startswith(city):
                text = text.replace(city, abbrev, 1)
                break
        
        words = text.split()
        
        for word in words:
            word = word.strip()
            if not word:
                continue
                
            # Handle remaining single-word abbreviations
            single_abbrev_map = {
                'Portland': 'POR', 'Sacramento': 'SAC', 'Minnesota': 'MIN', 
                'Milwaukee': 'MIL', 'Philadelphia': 'PHI', 'Brooklyn': 'BKN', 
                'Charlotte': 'CHA', 'Washington': 'WAS', 'Phoenix': 'PHX', 
                'Denver': 'DEN', 'Cleveland': 'CLE', 'Detroit': 'DET', 
                'Indiana': 'IND', 'Chicago': 'CHI', 'Boston': 'BOS', 
                'Miami': 'MIA', 'Orlando': 'ORL', 'Atlanta': 'ATL', 
                'Toronto': 'TOR', 'Memphis': 'MEM', 'Dallas': 'DAL', 
                'Houston': 'HOU', 'Utah': 'UTA', 'Connecticut': 'CONN', 
                'Seattle': 'SEA'
            }
            
            if word in single_abbrev_map:
                result_words.append(single_abbrev_map[word])
            else:
                # Keep team names (Lakers, Warriors, etc.) as is
                result_words.append(word)
        
        # Join with no spaces and limit length
        result = ''.join(result_words)
        
        # Remove any remaining special characters except letters and numbers
        result = re.sub(r'[^a-zA-Z0-9]', '', result)
        
        # Limit to reasonable length
        return result[:15] if len(result) > 15 else result
    
    def _extract_teams_from_aria_label(self, aria_label: str) -> Optional[list]:
        """Extract team names from aria-label text"""
        import re
        if not aria_label:
            return None
        
        try:
            # Common patterns for team names in aria-label
            # Look for "Team1 vs Team2" or "Team1 v Team2" or "Team1 @ Team2"
            vs_patterns = [
                r'([A-Za-z\s\.]+?)\s+(?:vs\.?|v\.?|@|\-)\s+([A-Za-z\s\.]+?)(?:\s|$|,)',
                r'([A-Za-z\s\.]+?)\s+(?:versus|against)\s+([A-Za-z\s\.]+?)(?:\s|$|,)',
            ]
            
            for pattern in vs_patterns:
                match = re.search(pattern, aria_label, re.IGNORECASE)
                if match:
                    team1 = match.group(1).strip()
                    team2 = match.group(2).strip()
                    
                    # Filter out common non-team words
                    non_team_words = ['spread', 'total', 'over', 'under', 'money', 'line', 'bet', 'odds']
                    if not any(word.lower() in team1.lower() for word in non_team_words) and \
                       not any(word.lower() in team2.lower() for word in non_team_words):
                        return [team1, team2]
            
            return None
        except Exception:
            return None

    async def parse_live_streaming(self, content: str) -> List[Dict]:
        """Parse live streaming events"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            streaming_events = []
            
            # Look for streaming elements - these may have specific classes
            streaming_selectors = [
                '.streaming-event',
                '.live-stream',
                '.watch-live',
                '[data-streaming="true"]',
                '.video-player',
                '.stream-item'
            ]
            
            for selector in streaming_selectors:
                events = soup.select(selector)
                for event in events:
                    try:
                        event_data = {
                            'id': self._generate_unique_id(),
                            'type': 'live_streaming',
                            'title': event.get_text(strip=True) if event else 'Unknown Event',
                            'url': event.get('href', ''),
                            'sport': self._detect_sport_from_text(event.get_text(strip=True)),
                            'timestamp': time.time()
                        }
                        
                        if event_data['title'] and event_data['title'] != 'Unknown Event':
                            streaming_events.append(event_data)
                            
                    except Exception as e:
                        self.logger.error(f"Error parsing streaming event: {e}")
                        continue
            
            return streaming_events
            
        except Exception as e:
            self.logger.error(f"Error parsing live streaming content: {e}")
            return []

    async def parse_live_schedule(self, content: str) -> List[Dict]:
        """Parse live schedule events"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            schedule_events = []
            
            # Look for schedule elements
            schedule_selectors = [
                '.schedule-item',
                '.upcoming-event',
                '.event-schedule',
                '[data-schedule="true"]',
                '.fixture',
                '.match-schedule'
            ]
            
            for selector in schedule_selectors:
                events = soup.select(selector)
                for event in events:
                    try:
                        event_data = {
                            'id': self._generate_unique_id(),
                            'type': 'live_schedule',
                            'title': event.get_text(strip=True) if event else 'Unknown Event',
                            'url': event.get('href', ''),
                            'sport': self._detect_sport_from_text(event.get_text(strip=True)),
                            'timestamp': time.time()
                        }
                        
                        # Try to extract time information
                        time_elem = event.select_one('.time, .start-time, .kick-off, .schedule-time')
                        if time_elem:
                            event_data['scheduled_time'] = time_elem.get_text(strip=True)
                        
                        if event_data['title'] and event_data['title'] != 'Unknown Event':
                            schedule_events.append(event_data)
                            
                    except Exception as e:
                        self.logger.error(f"Error parsing schedule event: {e}")
                        continue
            
            return schedule_events
            
        except Exception as e:
            self.logger.error(f"Error parsing live schedule content: {e}")
            return []