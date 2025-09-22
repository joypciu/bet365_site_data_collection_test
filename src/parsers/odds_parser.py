import re
import logging
from typing import Dict, List, Optional
from ..models.odds import Odds

class OddsParser:
    """Parse odds from various text formats and HTML elements"""
    
    @staticmethod
    def parse_aria_label_odds(aria_label: str) -> Dict:
        """Parse odds from aria-label with improved patterns"""
        odds_data = {}
        
        if not aria_label:
            return odds_data
        
        # Clean the aria-label
        aria_label = aria_label.strip()
        
        # Pattern 1: Spread betting - "Team A v Team B Spread Team A +7.5 @ -110"
        spread_pattern = r'(.+?)\s+v\s+(.+?)\s+Spread\s+(.+?)\s+([+-]?\d+\.?\d*)\s+@\s+([+-]?\d+)'
        spread_match = re.search(spread_pattern, aria_label)
        if spread_match:
            home_team = spread_match.group(1).strip()
            away_team = spread_match.group(2).strip()
            bet_team = spread_match.group(3).strip()
            handicap = spread_match.group(4)
            odds_val = spread_match.group(5)
            
            # Determine which team has the spread
            if bet_team.lower() in away_team.lower() or away_team.lower() in bet_team.lower():
                odds_data['spread_away'] = handicap
                odds_data['spread_away_odds'] = odds_val
                # Calculate opposite spread for home team
                try:
                    opposite_handicap = float(handicap) * -1
                    odds_data['spread_home'] = f"{opposite_handicap:+g}"
                except ValueError:
                    pass
            elif bet_team.lower() in home_team.lower() or home_team.lower() in bet_team.lower():
                odds_data['spread_home'] = handicap
                odds_data['spread_home_odds'] = odds_val
                # Calculate opposite spread for away team
                try:
                    opposite_handicap = float(handicap) * -1
                    odds_data['spread_away'] = f"{opposite_handicap:+g}"
                except ValueError:
                    pass
            
            odds_data['home_team'] = home_team
            odds_data['away_team'] = away_team
            return odds_data
        
        # Pattern 2: Total/Over-Under - "Team A @ Team B Total Over 53.0 @ -110"
        total_pattern = r'(.+?)\s+@\s+(.+?)\s+Total.*?\s+(Over|Under)\s+([+-]?\d+\.?\d*)\s+@\s+([+-]?\d+)'
        total_match = re.search(total_pattern, aria_label)
        if total_match:
            home_team = total_match.group(1).strip()
            away_team = total_match.group(2).strip()
            over_under = total_match.group(3)
            total_val = total_match.group(4)
            odds_val = total_match.group(5)
            
            if over_under == 'Over':
                odds_data['total_over'] = total_val
                odds_data['total_over_odds'] = odds_val
            else:
                odds_data['total_under'] = total_val
                odds_data['total_under_odds'] = odds_val
            
            odds_data['home_team'] = home_team
            odds_data['away_team'] = away_team
            return odds_data
        
        # Pattern 3: Moneyline - "Team A v Team B Moneyline Team A @ +150"
        money_pattern = r'(.+?)\s+v\s+(.+?)\s+Money(?:line)?\s+(.+?)\s+@\s+([+-]?\d+)'
        money_match = re.search(money_pattern, aria_label)
        if money_match:
            home_team = money_match.group(1).strip()
            away_team = money_match.group(2).strip()
            bet_team = money_match.group(3).strip()
            odds_val = money_match.group(4)
            
            if bet_team.lower() in home_team.lower() or home_team.lower() in bet_team.lower():
                odds_data['money_home'] = odds_val
            elif bet_team.lower() in away_team.lower() or away_team.lower() in bet_team.lower():
                odds_data['money_away'] = odds_val
            
            odds_data['home_team'] = home_team
            odds_data['away_team'] = away_team
            return odds_data
        
        # Pattern 4: Basic team vs team with @ symbol - "Team A @ Team B"
        vs_pattern = r'(.+?)\s+@\s+(.+?)(?:\s|$)'
        vs_match = re.search(vs_pattern, aria_label)
        if vs_match:
            home_team = vs_match.group(1).strip()
            away_team = vs_match.group(2).strip()
            
            # Remove any trailing odds or numbers from team names
            home_team = re.sub(r'\s+[+-]?\d+(?:\.\d+)?$', '', home_team)
            away_team = re.sub(r'\s+[+-]?\d+(?:\.\d+)?$', '', away_team)
            
            # Look for odds values in the rest of the string
            odds_pattern = re.findall(r'([+-]?\d+)', aria_label)
            if len(odds_pattern) >= 1:
                # Try to determine what type of odds these are based on context
                if 'spread' in aria_label.lower():
                    odds_data['spread_home_odds'] = odds_pattern[0] if odds_pattern else None
                elif 'total' in aria_label.lower() or 'over' in aria_label.lower():
                    odds_data['total_over_odds'] = odds_pattern[0] if odds_pattern else None
                else:
                    odds_data['home_odds'] = odds_pattern[0] if odds_pattern else None
            
            odds_data['home_team'] = home_team
            odds_data['away_team'] = away_team
            return odds_data
        
        # Pattern 5: Simple "v" format - "Team A v Team B"
        simple_v_pattern = r'(.+?)\s+v\s+(.+?)(?:\s|$)'
        simple_v_match = re.search(simple_v_pattern, aria_label)
        if simple_v_match:
            home_team = simple_v_match.group(1).strip()
            away_team = simple_v_match.group(2).strip()

            # Guard: If away_team looks like an odds value (+200, -250) treat this as malformed and return empty
            if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', away_team):
                return {}
            # Guard: If the entire aria_label has only one ' v ' and also contains parentheses suggesting tennis matchup later handled elsewhere, allow; otherwise proceed
            
            # Clean team names of any trailing odds
            home_team = re.sub(r'\s+[+-]?\d+(?:\.\d+)?$', '', home_team)
            away_team = re.sub(r'\s+[+-]?\d+(?:\.\d+)?$', '', away_team)
            
            odds_data['home_team'] = home_team
            odds_data['away_team'] = away_team
            return odds_data
        
        return odds_data
    
    @staticmethod
    def extract_odds_from_elements(elements: List) -> List[Dict]:
        """Extract odds from a list of HTML elements"""
        odds_list = []
        
        for element in elements:
            try:
                # Get aria-label attribute
                aria_label = element.get_attribute('aria-label')
                if aria_label:
                    odds_data = OddsParser.parse_aria_label_odds(aria_label)
                    if odds_data:
                        odds_list.append(odds_data)
                
                # Get text content and look for odds patterns
                text_content = element.text_content()
                if text_content:
                    odds_data = OddsParser.parse_text_odds(text_content)
                    if odds_data:
                        odds_list.append(odds_data)
                        
            except Exception as e:
                logging.warning(f"Error extracting odds from element: {e}")
                continue
        
        return odds_list
    
    @staticmethod
    def parse_text_odds(text: str) -> Dict:
        """Parse odds from plain text"""
        odds_data = {}
        
        # Look for American odds patterns
        american_odds = re.findall(r'([+-]\d+)', text)
        if american_odds:
            odds_data['raw_odds'] = american_odds
        
        # Look for decimal odds patterns
        decimal_odds = re.findall(r'(\d+\.\d+)', text)
        if decimal_odds:
            odds_data['decimal_odds'] = decimal_odds
        
        # Look for spread patterns
        spread_pattern = re.search(r'([+-]?\d+\.?\d*)', text)
        if spread_pattern:
            odds_data['spread'] = spread_pattern.group(1)
        
        return odds_data
    
    @staticmethod
    def normalize_odds_format(odds_str: str) -> Optional[str]:
        """Normalize odds to a consistent format"""
        if not odds_str:
            return None
        
        try:
            # Remove any non-numeric characters except +, -, and .
            cleaned = re.sub(r'[^\d+\-.]', '', str(odds_str))
            
            # Handle American odds
            if '+' in cleaned or (cleaned.startswith('-') and len(cleaned) > 3):
                return cleaned
            
            # Handle decimal odds
            if '.' in cleaned:
                return cleaned
            
            # Default return
            return cleaned
        except Exception:
            return None