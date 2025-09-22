import json
import re
import logging
from typing import Dict, Optional
from .client import AIClient

class AIExtractor:
    """AI-powered odds extraction from HTML content"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    def extract_odds_with_ai(self, html: str) -> Dict:
        """Extract betting odds from HTML using AI"""
        if not html or not html.strip():
            logging.warning("[!] Empty HTML provided to AI extractor")
            return {}
        
        if not self.ai_client.is_available():
            logging.warning("[!] AI client not available for extraction")
            return {}
        
        prompt = self._build_extraction_prompt(html)
        
        try:
            response = self.ai_client.generate_content(prompt)
            if not response:
                logging.warning("[!] No response from AI")
                return {}
            
            # Clean and parse JSON response
            cleaned_response = self._clean_ai_response(response)
            odds_data = self._parse_ai_response(cleaned_response)
            
            if odds_data:
                logging.info(f"[+] AI extracted odds for: {odds_data.get('home_team', 'Unknown')} vs {odds_data.get('away_team', 'Unknown')}")
                return odds_data
            else:
                logging.warning("[!] AI failed to extract valid odds data")
                return {}
                
        except Exception as e:
            logging.error(f"[!] AI extraction error: {e}")
            return {}
    
    def _build_extraction_prompt(self, html: str) -> str:
        """Build the AI prompt for odds extraction"""
        # Truncate HTML if too long to avoid token limits
        if len(html) > 8000:
            html = html[:8000] + "..."
        
        prompt = f"""
Extract betting odds from the following sports fixture HTML. Look for odds in aria-label attributes, span elements, and any text containing numbers like -110, +150, 1.5, etc.

The HTML contains elements like:
- <div class="cpm-ParticipantOdds" aria-label="... Spread ... @ ...">
- <span class="cpm-ParticipantOdds_Handicap">+7.5</span><span class="cpm-ParticipantOdds_Odds">-115</span>
- <div class="ovm-ParticipantStackedCentered" aria-label="... Total ... Over ... @ ...">

Extract teams, league if possible, and ALL available odds. Focus on:
1. Team names (home and away)
2. Moneyline odds (including draw for soccer)
3. Spread/Handicap betting (including Asian Handicap)
4. Totals/Over-Under betting (including goal lines)
5. Both Teams To Score (BTTS)
6. Double Chance (1X, X2, 12)
7. Draw No Bet
8. Correct Score markets
9. Player props and special markets
10. Live betting indicators

Return ONLY a JSON object with these keys (include only if found):
- home_team: name of home team
- away_team: name of away team
- league: specific league name (e.g., "Premier League", "NFL", "NBA") - NOT the sport type
- moneyline_home: moneyline odds for home team
- moneyline_away: moneyline odds for away team
- moneyline_draw: draw odds (for soccer)
- spread_home: spread value for home team
- spread_home_odds: odds for home spread
- spread_away: spread value for away team
- spread_away_odds: odds for away spread
- asian_handicap_home: Asian handicap value for home
- asian_handicap_home_odds: odds for Asian handicap home
- asian_handicap_away: Asian handicap value for away
- asian_handicap_away_odds: odds for Asian handicap away
- total_over: over total value
- total_over_odds: odds for over
- total_under: under total value
- total_under_odds: odds for under
- btts_yes: Both Teams To Score Yes odds
- btts_no: Both Teams To Score No odds
- double_chance_1x: Double Chance Home or Draw odds
- double_chance_x2: Double Chance Draw or Away odds
- double_chance_12: Double Chance Home or Away odds
- draw_no_bet_home: Draw No Bet home odds
- draw_no_bet_away: Draw No Bet away odds
- correct_score_options: array of correct score options with odds
- player_props: array of player prop objects with player name, prop type, line, and odds
- is_live: boolean indicating if this is live betting
- current_score: current score if live (format: "1-0")
- time_remaining: time remaining if live

If no betting data is found, return empty object {{}}.

HTML: {html}
"""
        return prompt
    
    def _clean_ai_response(self, response: str) -> str:
        """Clean AI response to extract JSON"""
        # Remove markdown code blocks
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Remove any text before the first {
        json_start = response.find('{')
        if json_start != -1:
            response = response[json_start:]
        
        # Remove any text after the last }
        json_end = response.rfind('}')
        if json_end != -1:
            response = response[:json_end + 1]
        
        return response.strip()
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response as JSON"""
        try:
            data = json.loads(response)
            
            # Validate that it's a dictionary
            if not isinstance(data, dict):
                logging.warning("[!] AI response is not a dictionary")
                return {}
            
            # Clean up the data
            cleaned_data = {}
            for key, value in data.items():
                if value is not None and value != "":
                    # Convert to string and clean
                    cleaned_value = str(value).strip()
                    if cleaned_value:
                        cleaned_data[key] = cleaned_value
            
            return cleaned_data
            
        except json.JSONDecodeError as e:
            logging.warning(f"[!] Failed to parse AI response as JSON: {e}")
            # Try to extract data using regex as fallback
            return self._extract_data_with_regex(response)
        except Exception as e:
            logging.error(f"[!] Error parsing AI response: {e}")
            return {}
    
    def _extract_data_with_regex(self, response: str) -> Dict:
        """Fallback: extract data using regex patterns"""
        data = {}
        
        try:
            # Look for team names
            team_pattern = r'"(?:home_team|away_team)":\s*"([^"]+)"'
            teams = re.findall(team_pattern, response)
            if len(teams) >= 2:
                data['home_team'] = teams[0]
                data['away_team'] = teams[1]
            
            # Look for odds values
            odds_pattern = r'"([^"]*odds?[^"]*)":\s*"?([+-]?\d+(?:\.\d+)?)"?'
            odds_matches = re.findall(odds_pattern, response, re.IGNORECASE)
            for key, value in odds_matches:
                data[key] = value
            
            # Look for spread values
            spread_pattern = r'"(spread[^"]*)":\s*"?([+-]?\d+(?:\.\d+)?)"?'
            spread_matches = re.findall(spread_pattern, response, re.IGNORECASE)
            for key, value in spread_matches:
                data[key] = value
            
            logging.info(f"[+] Extracted {len(data)} fields using regex fallback")
            return data
            
        except Exception as e:
            logging.error(f"[!] Regex extraction failed: {e}")
            return {}
    
    def extract_minimal_data(self, html: str) -> Dict:
        """Extract minimal data using a shorter prompt"""
        if not self.ai_client.is_available():
            return {}
        
        # Truncate HTML more aggressively for minimal extraction
        if len(html) > 4000:
            html = html[:4000] + "..."
        
        prompt = f"""
Extract only team names and basic odds from this HTML. Return JSON with:
- home_team: home team name
- away_team: away team name
- Any odds found (with descriptive keys)

HTML: {html}
"""
        
        try:
            response = self.ai_client.generate_content(prompt)
            if response:
                cleaned_response = self._clean_ai_response(response)
                return self._parse_ai_response(cleaned_response)
            return {}
        except Exception as e:
            logging.error(f"[!] Minimal AI extraction failed: {e}")
            return {}