import asyncio
import logging
import time
from typing import Dict, List, Optional
from patchright.async_api import async_playwright

# Import our modules
from ..config.settings import Config
from ..config.browser_config import BrowserConfig
from ..models.match import Match
from ..parsers.html_parser import HTMLParser
from ..ai.client import AIClient
from ..ai.extractor import AIExtractor
from ..utils.logger import Logger
from ..utils.helpers import RetryHelper, DelayHelper, DataHelper
from ..utils.constants import (
    SPORT_CODES, DEFAULT_SPORT_CODES, MARKET_TYPES, 
    BROWSER_CONFIG, RETRY_CONFIG
)
from ..utils.dynamic_detection import get_dynamic_stats

class Bet365Scraper:
    """Main scraper class for bet365 odds data"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.logger = Logger.setup_logger()
        self.html_parser = HTMLParser()
        self.ai_client = AIClient(max_calls=self.config.max_ai_calls)
        self.ai_extractor = AIExtractor(self.ai_client)
        
        # State management
        self.all_matches: Dict[str, Match] = {}
        self.api_urls: List[str] = []
        self.session_start_time = time.time()
        
        # Browser instances
        self.browser = None
        self.page = None
    
    async def initialize(self):
        """Initialize the scraper"""
        try:
            # Load configuration
            headers, cookies = await self.config.load_config()
            if not headers or not cookies:
                self.logger.error("[!] Failed to load configuration")
                return False
            
            # Test AI connection
            if self.ai_client.is_available():
                ai_test = self.ai_client.test_connection()
                if ai_test:
                    self.logger.info("[+] AI client initialized and tested successfully")
                else:
                    self.logger.warning("[!] AI client test failed, continuing without AI")
            
            self.logger.info("[+] Scraper initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[!] Initialization failed: {e}")
            return False
    
    async def start_browser(self):
        """Start browser with persistent context"""
        try:
            playwright = await async_playwright().start()
            
            browser_options = BrowserConfig.get_browser_options()
            browser_options['user_data_dir'] = BROWSER_CONFIG['user_data_dir']
            
            self.browser = await playwright.chromium.launch_persistent_context(**browser_options)
            
            # Setup request interception for API discovery
            await self._setup_request_interception()
            
            self.page = await self.browser.new_page()
            
            # Set random user agent
            user_agent = DelayHelper.get_random_user_agent()
            await self.page.set_extra_http_headers({
                'User-Agent': user_agent
            })
            
            self.logger.info("[+] Browser started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[!] Failed to start browser: {e}")
            return False
    
    async def _setup_request_interception(self):
        """Setup request interception to capture API URLs"""
        async def handle_response(response):
            try:
                url = response.url
                if any(pattern in url for pattern in ['config/api', 'prematch/api', 'inplay/api']):
                    if url not in self.api_urls:
                        self.api_urls.append(url)
                        self.logger.info(f"[+] Captured API URL: {url}")
                        
                        # Try to get response data
                        if response.status == 200:
                            try:
                                json_data = await response.json()
                                await self._process_api_response(json_data, url)
                            except Exception as e:
                                self.logger.debug(f"[*] Could not parse response as JSON: {e}")
                                
            except Exception as e:
                self.logger.debug(f"[*] Response handling error: {e}")
        
        if self.browser:
            self.browser.on('response', handle_response)
    
    async def _process_api_response(self, data: Dict, url: str):
        """Process API response data to extract matches"""
        try:
            if not isinstance(data, dict):
                return
            
            # Look for match data in various API response structures
            matches_found = 0
            
            # Common API response patterns
            if 'fixtures' in data:
                matches_found += await self._extract_from_fixtures(data['fixtures'], url)
            elif 'events' in data:
                matches_found += await self._extract_from_events(data['events'], url)
            elif 'markets' in data:
                matches_found += await self._extract_from_markets(data['markets'], url)
            
            if matches_found > 0:
                self.logger.info(f"[+] Extracted {matches_found} matches from API response")
                
        except Exception as e:
            self.logger.error(f"[!] Error processing API response: {e}")
    
    async def _extract_from_fixtures(self, fixtures: List, source_url: str) -> int:
        """Extract matches from fixtures API data"""
        matches_found = 0
        
        for fixture in fixtures:
            try:
                if not isinstance(fixture, dict):
                    continue
                
                # Extract basic match info
                home_team = fixture.get('homeTeam', {}).get('name', 'Unknown')
                away_team = fixture.get('awayTeam', {}).get('name', 'Unknown')
                
                if home_team == 'Unknown' or away_team == 'Unknown':
                    continue
                
                # Create match
                sport = self._get_sport_from_url(source_url)
                league = fixture.get('competition', {}).get('name', 'Unknown')
                
                match = Match.create(
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    sport=sport,
                    source_url=source_url
                )
                
                # Extract odds if available
                if 'markets' in fixture:
                    odds_data = self._extract_odds_from_markets(fixture['markets'])
                    match.update_odds(odds_data)
                
                self.all_matches[match.match_id] = match
                matches_found += 1
                
            except Exception as e:
                self.logger.warning(f"Error processing fixture: {e}")
                continue
        
        return matches_found
    
    async def _extract_from_events(self, events: List, source_url: str) -> int:
        """Extract matches from events API data"""
        # Similar implementation for events structure
        return 0
    
    async def _extract_from_markets(self, markets: List, source_url: str) -> int:
        """Extract matches from markets API data"""
        # Similar implementation for markets structure
        return 0
    
    def _extract_odds_from_markets(self, markets: List) -> Dict:
        """Extract odds data from markets array"""
        odds_data = {}
        
        for market in markets:
            try:
                market_type = market.get('type', '').lower()
                
                if 'moneyline' in market_type or 'match' in market_type:
                    selections = market.get('selections', [])
                    if len(selections) >= 2:
                        odds_data['home_odds'] = selections[0].get('price')
                        odds_data['away_odds'] = selections[1].get('price')
                
                elif 'spread' in market_type or 'handicap' in market_type:
                    selections = market.get('selections', [])
                    for selection in selections:
                        if selection.get('handicap'):
                            team_type = 'home' if selection.get('index') == 0 else 'away'
                            odds_data[f'spread_{team_type}'] = selection.get('handicap')
                            odds_data[f'spread_{team_type}_odds'] = selection.get('price')
                
                elif 'total' in market_type or 'over' in market_type:
                    selections = market.get('selections', [])
                    for selection in selections:
                        selection_type = selection.get('type', '').lower()
                        if 'over' in selection_type:
                            odds_data['total_over'] = selection.get('handicap')
                            odds_data['total_over_odds'] = selection.get('price')
                        elif 'under' in selection_type:
                            odds_data['total_under'] = selection.get('handicap')
                            odds_data['total_under_odds'] = selection.get('price')
                            
            except Exception as e:
                self.logger.warning(f"Error extracting odds from market: {e}")
                continue
        
        return odds_data
    
    async def navigate_to_sport(self, sport_code: str, market_type: str = "AS"):
        """Navigate to specific sport page"""
        url = f"{self.config.base_url}{market_type}/{sport_code}"
        
        return await RetryHelper.retry_async(
            self._navigate_with_retry,
            max_retries=RETRY_CONFIG['max_retries'],
            delay=RETRY_CONFIG['base_delay'],
            backoff_factor=RETRY_CONFIG['backoff_factor'],
            url=url
        )
    
    async def _navigate_with_retry(self, url: str):
        """Navigate to URL with retry logic"""
        if not self.page:
            raise Exception("Page not initialized")
            
        try:
            # Add random delay before navigation
            await DelayHelper.random_delay(0.5, 2.0)
            
            await self.page.goto(url, wait_until=BROWSER_CONFIG['wait_for'], 
                               timeout=BROWSER_CONFIG['timeout'])
            
            # Wait for content to load
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            self.logger.info(f"[+] Successfully navigated to {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"[!] Navigation failed for {url}: {e}")
            raise
    
    async def scrape_sport(self, sport_code: str, market_type: str = "AS") -> List[Match]:
        """Scrape matches for a specific sport"""
        try:
            # Navigate to sport page
            success = await self.navigate_to_sport(sport_code, market_type)
            if not success:
                return []
            
            # Get current URL for context
            current_url = self.page.url if self.page else ""
            
            # Get sport name for this sport code
            sport_name = self._get_sport_from_url(current_url)
            
            # Parse HTML content
            matches = await self.html_parser.parse_html_data(self.page, current_url, sport_name)
            
            # Try AI extraction if HTML parsing found limited results OR if we want to test enhanced markets
            if len(matches) < 50 and self.ai_client.is_available() and self.page:  # Increased threshold to force AI extraction
                html_content = await self.page.content()
                ai_matches = await self._extract_with_ai(html_content, current_url)
                matches.extend(ai_matches)
            
            # Update internal matches collection with deduplication
            new_matches_count = 0
            for match in matches:
                if match.match_id not in self.all_matches:
                    self.all_matches[match.match_id] = match
                    new_matches_count += 1
                else:
                    # Merge odds from existing match
                    existing_match = self.all_matches[match.match_id]
                    existing_match.update_odds(match.odds)
            
            sport_name = SPORT_CODES.get(sport_code, sport_code)
            self.logger.info(f"[+] Scraped {len(matches)} matches from {sport_name} ({market_type}), {new_matches_count} new")
            
            return matches
            
        except Exception as e:
            self.logger.error(f"[!] Error scraping {sport_code}: {e}")
            return []
    
    async def _extract_with_ai(self, html_content: str, source_url: str) -> List[Match]:
        """Extract matches using AI"""
        try:
            odds_data = self.ai_extractor.extract_odds_with_ai(html_content)
            
            if not odds_data:
                return []
            
            # Convert AI extracted data to matches
            home_team = odds_data.get('home_team')
            away_team = odds_data.get('away_team')
            
            if not home_team or not away_team or home_team == 'Unknown' or away_team == 'Unknown':
                return []
            
            sport = self._get_sport_from_url(source_url)
            league = odds_data.get('league', 'Unknown')
            
            match = Match.create(
                home_team=home_team,
                away_team=away_team,
                league=league,
                sport=sport,
                source_url=source_url
            )
            
            # Handle live betting fields
            if odds_data.get('is_live'):
                match.is_live = True
                match.current_score = odds_data.get('current_score')
                match.time_remaining = odds_data.get('time_remaining')
                match.match_type = 'live'
            
            match.update_odds(odds_data)
            
            return [match]
            
        except Exception as e:
            self.logger.error(f"[!] AI extraction failed: {e}")
            return []
    
    def _get_sport_from_url(self, url: str) -> str:
        """Extract sport name from URL"""
        if not url:
            return 'Unknown'
        import re
        found_codes = re.findall(r'B\d+', url)
        for code in reversed(found_codes):
            if code in SPORT_CODES:
                return SPORT_CODES[code]
        return 'Unknown'
    
    async def scrape_all_sports(self, sport_codes: Optional[List[str]] = None, 
                              include_inplay: bool = True) -> Dict[str, Match]:
        """Scrape all specified sports"""
        if sport_codes is None:
            sport_codes = DEFAULT_SPORT_CODES
        
        total_matches = 0
        
        for sport_code in sport_codes:
            try:
                # Scrape pre-match
                prematch_matches = await self.scrape_sport(sport_code, "AS")
                total_matches += len(prematch_matches)
                
                # Scrape in-play if requested
                if include_inplay:
                    await DelayHelper.random_delay(2, 4)  # Longer delay between market types
                    inplay_matches = await self.scrape_sport(sport_code, "IP")
                    total_matches += len(inplay_matches)
                
                # Add delay between sports
                await DelayHelper.random_delay(1, 3)
                
            except Exception as e:
                self.logger.error(f"[!] Error scraping sport {sport_code}: {e}")
                continue
        
        self.logger.info(f"[+] Total matches scraped: {total_matches}")
        
        # Log dynamic detection statistics
        stats = get_dynamic_stats()
        self.logger.info(f"[STATS] Dynamic Detection Summary:")
        self.logger.info(f"  - Discovered Sports: {stats.get('discovered_sports', [])}")
        self.logger.info(f"  - Discovered Leagues: {stats.get('discovered_leagues', [])}")
        self.logger.info(f"  - Teams by Sport: {stats.get('team_counts_by_sport', {})}")
        self.logger.info(f"  - Teams by League: {stats.get('team_counts_by_league', {})}")
        
        return self.all_matches
    
    async def save_data(self):
        """Save scraped data to file"""
        try:
            # Convert matches to serializable format
            data = {match_id: match.to_dict() for match_id, match in self.all_matches.items()}
            
            self.config.save_data(data)
            
            Logger.log_data_save(self.logger, self.config.output_file, len(data))
            
        except Exception as e:
            self.logger.error(f"[!] Error saving data: {e}")
    
    async def run_continuous(self, sport_codes: Optional[List[str]] = None, 
                           refresh_interval: Optional[int] = None):
        """Run continuous scraping loop"""
        if not await self.initialize():
            return
        
        if not await self.start_browser():
            return
        
        refresh_interval = refresh_interval or self.config.refresh_interval
        
        try:
            self.logger.info(f"[*] Starting continuous scraping (refresh every {refresh_interval}s)")
            
            while True:
                loop_start = time.time()
                
                # Reset AI call counter for each loop
                self.ai_client.reset_call_count()
                
                # Scrape all sports
                await self.scrape_all_sports(sport_codes)
                
                # Save data
                await self.save_data()
                
                loop_time = time.time() - loop_start
                self.logger.info(f"[*] Loop completed in {loop_time:.1f}s, waiting {refresh_interval}s")
                
                # Wait for next iteration
                await asyncio.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            self.logger.info("[*] Stopping scraper...")
        except Exception as e:
            self.logger.error(f"[!] Unexpected error in continuous loop: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            # Small delay to allow cleanup
            await asyncio.sleep(0.5)
            
            self.logger.info("[+] Browser closed")
        except Exception as e:
            self.logger.error(f"[!] Error during cleanup: {e}")
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        runtime = time.time() - self.session_start_time
        
        return {
            'total_matches': len(self.all_matches),
            'api_urls_discovered': len(self.api_urls),
            'ai_calls_used': self.ai_client.call_count,
            'ai_calls_remaining': self.ai_client.get_remaining_calls(),
            'runtime_seconds': runtime,
            'matches_per_minute': len(self.all_matches) / (runtime / 60) if runtime > 0 else 0
        }