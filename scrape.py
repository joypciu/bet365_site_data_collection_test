import os
import json
import time
import asyncio
import random
import re
from datetime import datetime, timezone
import logging
from patchright.async_api import async_playwright
import google.genai as genai

# Setup logging with minimal noise
logging.basicConfig(
    filename='bet365_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# User agents for randomization
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
]

CONFIG_FILE = "config.json"
OUTPUT_FILE = "bet365_data.json"
REFRESH_INTERVAL = 30
BASE_URL = "https://www.co.bet365.com/#/HO/"
all_matches = {}
api_urls = set()
ai_call_count = 0
MAX_AI_CALLS = 10  # Limit to avoid quota

# Setup Google AI
with open("api key.txt", "r") as f:
    lines = f.readlines()
    api_key = lines[0].split('=')[1].strip()
client = genai.Client(api_key=api_key)

def test_ai():
    prompt = "Say hello in JSON format: {\"message\": \"hello\"}"
    try:
        response = client.models.generate_content(
            model="gemma-3n-e2b-it",
            contents=prompt
        )
        if response and response.text:
            print(f"AI Response: {response.text}")
            return True
        else:
            print("No response from AI")
            return False
    except Exception as e:
        print(f"AI test failed: {e}")
        return False

def extract_odds_with_ai(html):
    if not html.strip():
        return {}
    prompt = f"""
Extract betting odds from the following sports fixture HTML. Look for odds in aria-label attributes, span elements, and any text containing numbers like -110, +150, 1.5, etc.

The HTML contains elements like:
- <div class="cpm-ParticipantOdds" aria-label="... Spread ... @ ...">
- <span class="cpm-ParticipantOdds_Handicap">+7.5</span><span class="cpm-ParticipantOdds_Odds">-115</span>
- <div class="ovm-ParticipantStackedCentered" aria-label="... Total ... Over ... @ ...">

Extract teams, league if possible, and odds.

Return a JSON object with keys:
- home_team: name of home team
- away_team: name of away team
- league: sport/league if detectable
- home_odds: decimal odds for home team
- away_odds: decimal odds for away team
- spread_home: spread value for home
- spread_home_odds: odds for home spread
- spread_away: spread value for away
- spread_away_odds: odds for away spread
- total_over: over total
- total_over_odds: odds for over
- total_under: under total
- total_under_odds: odds for under
- money_home: moneyline for home
- money_away: moneyline for away

Only include keys that are found. If no data, return empty object {{}}.

HTML: {html}
"""
    try:
        response = client.models.generate_content(
            model="models/gemma-3n-e4b-it",
            contents=prompt
        )
        if response and response.text:
            content = response.text.strip()
        else:
            return {}
        # Remove markdown if present
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        # Try to find JSON in the content
        import re
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        # If still fails, try to extract the first valid JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find the JSON object more aggressively
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                content = content[start:end]
                return json.loads(content)
            raise
    except Exception as e:
        logging.error(f"AI extraction failed: {e}")
        return {}

def get_sport_from_url(url):
    sport_map = {
        'B1': 'Soccer',
        'B2': 'Basketball',
        'B3': 'Cricket',
        'B4': 'Tennis',
        'B5': 'Golf',
        'B6': 'Ice Hockey',
        'B7': 'Snooker',
        'B8': 'American Football',
        'B9': 'Baseball',
        'B10': 'Handball',
        'B11': 'Volleyball',
        'B12': 'Rugby',
        'B13': 'NFL',
        'B14': 'Boxing',
        'B15': 'MMA',
        'B16': 'Formula 1',
        'B17': 'Cycling',
        'B18': 'Darts',
        'B19': 'Bowls',
        'B20': 'Badminton',
        'B21': 'Squash',
        'B22': 'Table Tennis',
    }
    for code, sport in sport_map.items():
        if f'/{code}' in url or f'#{code}' in url:
            return sport
    return 'Unknown'

def detect_league_from_teams(home_team, away_team):
    teams = f"{home_team} {away_team}".lower()
    if any(word in teams for word in ['bengals', 'vikings', 'patriots', 'raiders', 'browns', 'jets', 'colts', 'titans', 'falcons', 'panthers', 'texans', 'jaguars', 'broncos', 'chargers', 'saints', 'seahawks', 'cowboys', 'bears', 'cardinals', '49ers', 'chiefs', 'giants', 'lions', 'ravens']):
        return 'American Football'
    if any(word in teams for word in ['yankees', 'orioles', 'athletics', 'pirates', 'braves', 'tigers', 'nationals', 'mets', 'cubs', 'reds', 'blue jays', 'royals', 'guardians', 'twins', 'padres', 'white sox', 'brewers', 'cardinals', 'marlins', 'rangers', 'angels', 'rockies', 'dodgers', 'phillies', 'mariners', 'astros', 'red sox', 'rays']):
        return 'Baseball'
    if any(word in teams for word in ['arsenal', 'man city', 'chelsea', 'liverpool', 'man united', 'tottenham', 'newcastle', 'aston villa', 'birmingham', 'blackburn', 'bolton', 'bournemouth', 'brighton', 'burnley', 'cardiff', 'charlton', 'coventry', 'crystal palace', 'derby', 'everton', 'fulham', 'huddersfield', 'hull', 'ipswich', 'leeds', 'leicester', 'middlesbrough', 'millwall', 'norwich', 'nottingham forest', 'plymouth', 'portsmouth', 'preston', 'qpr', 'reading', 'sheffield united', 'southampton', 'stoke', 'sunderland', 'sunderland', 'swansea', 'watford', 'west brom', 'west ham', 'wigan', 'wolves', 'wrexham', 'barcelona', 'real madrid', 'atletico madrid', 'valencia', 'sevilla', 'villarreal', 'real sociedad', 'athletic bilbao', 'real betis', 'celta vigo', 'granada', 'levante', 'mallorca', 'osasuna', 'rayo vallecano', 'getafe', 'cadiz', 'almeria', 'girona', 'las palmas', 'alaves', 'vallecano', 'betis', 'psv', 'ajax', 'feyenoord', 'az', 'utrecht', 'vitesse', 'twente', 'groningen', 'heerenveen', 'willem ii', 'nac breda', 'roda jc', 'sparta rotterdam', 'excelsior', 'fortuna sittard', 'go ahead eagles', 'heracles almelo', 'pec zwolle', 'cambuur', 'volendam', 'emmen', 'monaco', 'marseille', 'paris saint-germain', 'lyon', 'nice', 'lille', 'saint-etienne', 'nantes', 'montpellier', 'rennes', 'angers', 'brest', 'metz', 'dijon', 'nimes', 'toulouse', 'reims', 'strasbourg', 'lorient', 'clermont', 'auxerre', 'troyes', 'ajaccio', 'le havre', 'lens', 'eintracht frankfurt', 'union berlin', 'bayern munich', 'borussia dortmund', 'rb leipzig', 'bayer leverkusen', 'wolfsburg', 'eintracht frankfurt', 'borussia monchengladbach', 'hertha berlin', 'werder bremen', 'schalke 04', 'mainz 05', 'augsburg', 'vfb stuttgart', 'hoffenheim', 'freiburg', 'bayer leverkusen', 'union berlin', 'koln', 'bochum', 'greuther furth', 'darmstadt', 'heidenheim', 'lazio', 'roma', 'juventus', 'inter milan', 'ac milan', 'napoli', 'atalanta', 'fiorentina', 'torino', 'sassuolo', 'udinese', 'sampdoria', 'genoa', 'bologna', 'cagliari', 'spezia', 'venezia', 'cremonese', 'lecce', 'hellas verona', 'empoli', 'monza', 'salernitana', 'frosinone', 'parma', 'palermo', 'bari', 'brescia', 'cittadella', 'como', 'cosenza', 'modena', 'pisa', 'reggiana', 'sudtirol', 'ternana', 'trapani', 'vicenza']):
        return 'Soccer'
    if any(word in teams for word in ['lakers', 'knicks', 'celtics', 'heat', 'bulls', 'raptors', 'warriors', 'clippers', 'nets', '76ers', 'bucks', 'pacers', 'cavaliers', 'pistons', 'hawks', 'hornets', 'wizards', 'magic', 'thunder', 'trail blazers', 'jazz', 'nuggets', 'timberwolves', 'pelicans', 'grizzlies', 'spurs', 'mavericks', 'rockets', 'kings', 'suns']):
        return 'Basketball'
    if any(word in teams for word in ['bruins', 'maple leafs', 'canadiens', 'rangers', 'penguins', 'capitals', 'blackhawks', 'red wings', 'flyers', 'devils', 'islanders', 'oilers', 'flames', 'canucks', 'golden knights', 'kings', 'ducks', 'stars', 'wild', 'predators', 'blues', 'jets', 'avalanche', 'coyotes', 'panthers', 'lightning', 'hurricanes', 'sabres', 'senators', 'sharks']):
        return 'Ice Hockey'
    if any(word in teams for word in ['alcaraz', 'djokovic', 'nadal', 'federer', 'medvedev', 'rublev', 'zverev', 'tsitsipas', 'berrettini', 'sinner', 'ruud', 'murray', 'wawrinka', 'gasquet', 'monfils', 'pouille', 'herbert', 'mahut', 'klaasen', 'ram', 'bublik', 'shevchenko', 'daniel', 'musetti', 'basilashvili', 'giraldi', 'nakashima', 'giron', 'royer', 'tien', 'mensik', 'de minaur', 'fritz', 'cerundolo', 'alcaraz', 'ruud', 'michelsen', 'opelka', 'mensik', 'de minaur', 'zverev', 'fritz', 'alcaraz', 'cerundolo', 'musetti', 'basilashvili', 'wu', 'medvedev', 'daniel', 'shevchenko', 'svrcina', 'bublik']):
        return 'Tennis'
    if any(word in teams for word in ['fever', 'aces', 'mercury', 'lynx', 'storm', 'sun', 'wings', 'dream', 'liberty', 'mystics', 'spark']):
        return 'Basketball'
    return 'Unknown'

async def generate_config():
    logging.info("[*] Generating config using patchright")
    async with async_playwright() as p:
        user_data_dir = "pw_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome",
            no_viewport=True
        )
        page = await browser.new_page()
        config_url = BASE_URL + "#HO"
        logging.info(f"[*] Navigating to {config_url} for config")
        try:
            await page.goto(config_url, wait_until="networkidle", timeout=60000)
            cookies_list = await page.context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)
            user_agent = await page.evaluate("() => navigator.userAgent")
            headers = {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.bet365.com/",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            cfg = {"headers": headers, "cookies": cookie_str}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            logging.info("[+] Saved config.json")
            await browser.close()
            return headers, {c['name']: c['value'] for c in cookies_list}
        except Exception as e:
            logging.error(f"[!] Error generating config: {e}")
            await browser.close()
            return None, None

async def load_config():
    if not os.path.exists(CONFIG_FILE):
        logging.info("[*] Config file not found, generating new one")
        return await generate_config()
    logging.info("[*] Loading config")
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        headers = cfg.get("headers", {})
        cookie_str = cfg.get("cookies", "")
        cookies = {}
        if cookie_str:
            for pair in cookie_str.split("; "):
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    cookies[key] = val
        return headers, cookies
    except Exception as e:
        logging.error(f"[!] Error loading config: {e}, regenerating")
        return await generate_config()

async def intercept_request(route, request):
    if route is None:
        return
    if "bet365.com" in request.url:
        api_urls.add(request.url)
        headers = request.headers
        headers["User-Agent"] = random.choice(user_agents)
        headers["Accept"] = "*/*"
        headers["Accept-Language"] = "en-US,en;q=0.9"
        try:
            await route.continue_(headers=headers)
        except Exception as e:
            logging.error(f"[!] Error in intercept_request for {request.url}: {e}")
    else:
        await route.continue_()

def parse_aria_label_odds(aria_label):
    """Parse odds from aria-label with improved patterns"""
    odds_data = {}
    
    # Pattern for spread: "GB Packers v CLE Browns Spread CLE Browns +7.5 @ -115"
    spread_match = re.search(r'(.+?) v (.+?) Spread (.+?) ([+-]?\d+\.?\d*) @ ([+-]?\d+)', aria_label)
    if spread_match:
        home_team = spread_match.group(1).strip()
        away_team = spread_match.group(2).strip()
        bet_team = spread_match.group(3).strip()
        handicap = spread_match.group(4)
        odds_val = spread_match.group(5)
        
        # Determine which team has the spread
        if bet_team in away_team or away_team in bet_team:
            odds_data['spread_away'] = handicap
            odds_data['spread_away_odds'] = odds_val
            # Calculate opposite spread for home team
            try:
                opposite_handicap = float(handicap) * -1
                odds_data['spread_home'] = f"{opposite_handicap:+g}"
            except:
                pass
        elif bet_team in home_team or home_team in bet_team:
            odds_data['spread_home'] = handicap
            odds_data['spread_home_odds'] = odds_val
            # Calculate opposite spread for away team
            try:
                opposite_handicap = float(handicap) * -1
                odds_data['spread_away'] = f"{opposite_handicap:+g}"
            except:
                pass
        
        odds_data['home_team'] = home_team
        odds_data['away_team'] = away_team
        return odds_data
    
    # Pattern for total: "Hanshin Tigers @ Yakult Swallows Total Home Over 5.5 @ -140"
    total_match = re.search(r'(.+?) @ (.+?) Total .* (Over|Under) ([+-]?\d+\.?\d*) @ ([+-]?\d+)', aria_label)
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
    
    # Pattern for moneyline: "Team A v Team B Moneyline Team A @ +150"
    money_match = re.search(r'(.+?) v (.+?) Money(?:line)? (.+?) @ ([+-]?\d+)', aria_label)
    if money_match:
        home_team = money_match.group(1).strip()
        away_team = money_match.group(2).strip()
        bet_team = money_match.group(3).strip()
        odds_val = money_match.group(4)
        
        if bet_team in home_team or home_team in bet_team:
            odds_data['money_home'] = odds_val
        elif bet_team in away_team or away_team in bet_team:
            odds_data['money_away'] = odds_val
        
        odds_data['home_team'] = home_team
        odds_data['away_team'] = away_team
        return odds_data
    
    return odds_data

async def parse_html_data(page, source_url):
    logging.info(f"[*] Parsing HTML from {source_url}")
    try:
        # Wait for potential content to load
        await page.wait_for_timeout(2000)
        title = await page.title()
        logging.info(f"[*] Page title: {title}")
        
        try:
            await page.wait_for_selector('.gl-MarketGroup, .srb-MarketGroup, .ovm-Classification, .wn-Classification', timeout=10000)
        except Exception as e:
            logging.warning(f"[!] Selectors not found on {source_url}: {e}")
        
        try:
            result = await page.evaluate("""
                () => {
                    const matches = [];
                    const allOddsElements = [];
                    
                    // Collect all odds elements with their context
                    const oddsSelectors = [
                        '.cpm-ParticipantOdds',
                        '.ovm-ParticipantStackedCentered'
                    ];
                    
                    oddsSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const ariaLabel = el.getAttribute('aria-label');
                            const handicapSpan = el.querySelector('.cpm-ParticipantOdds_Handicap, .ovm-ParticipantStackedCentered_Handicap');
                            const oddsSpan = el.querySelector('.cpm-ParticipantOdds_Odds, .ovm-ParticipantStackedCentered_Odds');
                            
                            if (ariaLabel || (handicapSpan && oddsSpan)) {
                                allOddsElements.push({
                                    ariaLabel: ariaLabel,
                                    handicap: handicapSpan ? handicapSpan.textContent.trim() : null,
                                    odds: oddsSpan ? oddsSpan.textContent.trim() : null,
                                    outerHTML: el.outerHTML,
                                    url: window.location.href
                                });
                            }
                        });
                    });
                    
                    // Find fixtures and try to match them with odds
                    let classifications = document.querySelectorAll('.gl-MarketGroup, .srb-MarketGroup, .ovm-Classification, .wn-Classification');
                    if (classifications.length === 0) {
                        classifications = document.querySelectorAll('[class*="MarketGroup"], [class*="Classification"]');
                    }
                    
                    classifications.forEach(classification => {
                        const league = classification.querySelector('.cpm-MarketFixtureDateHeader')?.textContent.trim() || 'unknown';
                        const fixtures = classification.querySelectorAll('[class*="ParticipantFixtureDetails"]');
                        
                        fixtures.forEach(fixture => {
                            let homeTeam = '';
                            let awayTeam = '';
                            
                            // Try different selectors for team names
                            const teamNames = fixture.querySelector('.cpm-ParticipantFixtureDetailsAmericanFootball_TeamNames, .cpm-ParticipantFixtureDetailsSoccer_TeamNames, [class*="TeamNames"]');
                            if (teamNames) {
                                const teams = teamNames.querySelectorAll('div');
                                if (teams.length >= 2) {
                                    homeTeam = teams[0]?.textContent.trim();
                                    awayTeam = teams[1]?.textContent.trim();
                                }
                            }
                            
                            // Fallback to aria-label
                            if (!homeTeam || !awayTeam) {
                                const ariaLabel = fixture.querySelector('[aria-label]')?.getAttribute('aria-label');
                                if (ariaLabel) {
                                    const match = ariaLabel.match(/^(.+?) v (.+?)$/);
                                    if (match) {
                                        homeTeam = match[1].trim();
                                        awayTeam = match[2].trim();
                                    }
                                }
                            }
                            
                            if (homeTeam && awayTeam && homeTeam !== awayTeam) {
                                const fixtureText = fixture.textContent.trim();
                                const timeMatch = fixtureText.match(/(\\d{1,2}:\\d{2}\\s?[AP]M|Q\\d+\\s+\\d{1,2}:\\d{2}|\\d+\\s+\\d+\\s+Q\\d+\\s+\\d{1,2}:\\d{2}|\\d{1,2}:\\d{2})/);
                                
                                matches.push({
                                    home_team: homeTeam,
                                    away_team: awayTeam,
                                    league: 'unknown',
                                    match_time: timeMatch ? timeMatch[0] : 'unknown',
                                    fixture_html: fixture.outerHTML,
                                    fixture_text: fixtureText,
                                    type: window.location.href.includes('IP') ? 'inplay' : 'prematch',
                                    url: window.location.href
                                });
                            }
                        });
                    });
                    
                    return {
                        matches: matches,
                        allOddsElements: allOddsElements,
                        debug: {
                            classifications: classifications.length,
                            totalOddsElements: allOddsElements.length
                        }
                    };
                }
            """)
        except Exception as e:
            logging.error(f"[!] Error in page.evaluate: {e}")
            result = {'matches': [], 'allOddsElements': [], 'debug': {'classifications': 0, 'totalOddsElements': 0}}
        
        matches = result['matches']
        all_odds_elements = result['allOddsElements']
        debug = result['debug']
        
        logging.info(f"[*] Debug: classifications={debug['classifications']}, total odds elements={debug['totalOddsElements']}")
        logging.info(f"[*] Found {len(matches)} raw matches and {len(all_odds_elements)} odds elements")
        
        # Process matches and try to attach odds
        match_odds_map = {}
        
        # First, parse all odds elements and group by teams
        for odds_element in all_odds_elements:
            if odds_element['ariaLabel']:
                parsed_odds = parse_aria_label_odds(odds_element['ariaLabel'])
                if parsed_odds.get('home_team') and parsed_odds.get('away_team'):
                    # Create a match key
                    match_key = f"{parsed_odds['home_team']}_{parsed_odds['away_team']}"
                    if match_key not in match_odds_map:
                        match_odds_map[match_key] = {
                            'home_team': parsed_odds['home_team'],
                            'away_team': parsed_odds['away_team'],
                            'odds': {}
                        }
                    
                    # Add the odds to this match
                    for key, value in parsed_odds.items():
                        if key not in ['home_team', 'away_team'] and value:
                            match_odds_map[match_key]['odds'][key] = value
                            
                    logging.info(f"[*] Extracted odds for {parsed_odds['home_team']} vs {parsed_odds['away_team']}: {list(parsed_odds.keys())}")
        
        updated = False
        
        # Process matches from HTML structure
        for match in matches:
            if not match.get('home_team') or not match.get('away_team'):
                continue
                
            league = get_sport_from_url(match.get('url', ''))
            if league == 'Unknown':
                league = detect_league_from_teams(match['home_team'], match['away_team'])
            
            match_id = f"{league}_{match['home_team']}_{match['away_team']}_{match['match_time'] or 'unknown'}".replace(' ', '_').lower()
            
            # Try to find matching odds
            match_key = f"{match['home_team']}_{match['away_team']}"
            odds = {}
            
            if match_key in match_odds_map:
                odds = match_odds_map[match_key]['odds']
                logging.info(f"[*] Found odds for {match['home_team']} vs {match['away_team']}: {len(odds)} odds types")
            else:
                # Try reverse match (away vs home)
                reverse_key = f"{match['away_team']}_{match['home_team']}"
                if reverse_key in match_odds_map:
                    odds = match_odds_map[reverse_key]['odds']
                    logging.info(f"[*] Found reverse odds for {match['home_team']} vs {match['away_team']}: {len(odds)} odds types")
            
            match_data = {
                "match_id": match_id,
                "home_team": match['home_team'],
                "away_team": match['away_team'],
                "league": league,
                "match_time": match['match_time'],
                "odds": odds,
                "type": match['type'],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Use AI for intelligent odds extraction if traditional methods failed and we have remaining calls
            global ai_call_count
            if not match_data['odds'] and ai_call_count < MAX_AI_CALLS:
                ai_call_count += 1
                ai_result = extract_odds_with_ai(match.get('fixture_html', ''))
                if ai_result:
                    # Update teams and league if AI provided better data
                    if 'home_team' in ai_result and ai_result['home_team']:
                        match_data['home_team'] = ai_result['home_team']
                    if 'away_team' in ai_result and ai_result['away_team']:
                        match_data['away_team'] = ai_result['away_team']
                    if 'league' in ai_result and ai_result['league']:
                        match_data['league'] = ai_result['league']
                    # Extract odds
                    odds_keys = ['home_odds', 'away_odds', 'spread_home', 'spread_home_odds', 'spread_away', 'spread_away_odds', 'total_over', 'total_over_odds', 'total_under', 'total_under_odds', 'money_home', 'money_away']
                    for key in odds_keys:
                        if key in ai_result and ai_result[key]:
                            match_data['odds'][key] = ai_result[key]
                    logging.info(f"[*] AI extracted data for {match_data['home_team']} vs {match_data['away_team']}")
            
            if match_id not in all_matches or json.dumps(all_matches[match_id]['odds'], sort_keys=True) != json.dumps(match_data['odds'], sort_keys=True):
                all_matches[match_id] = match_data
                updated = True
                odds_info = f" with {len(match_data['odds'])} odds" if match_data['odds'] else " (no odds)"
                logging.info(f"[*] Added/Updated match: {match_data['home_team']} vs {match_data['away_team']} in {league}{odds_info}")
        
        # Process standalone odds elements that weren't matched to fixtures
        for match_key, match_info in match_odds_map.items():
            # Check if this match was already processed above
            found_in_fixtures = False
            for match in matches:
                if (match.get('home_team') == match_info['home_team'] and match.get('away_team') == match_info['away_team']) or \
                   (match.get('away_team') == match_info['home_team'] and match.get('home_team') == match_info['away_team']):
                    found_in_fixtures = True
                    break
            
            if not found_in_fixtures and match_info['odds']:
                # Create match from odds data
                league = get_sport_from_url(source_url)
                if league == 'Unknown':
                    league = detect_league_from_teams(match_info['home_team'], match_info['away_team'])
                
                match_time = 'unknown'
                match_id = f"{league}_{match_info['home_team']}_{match_info['away_team']}_{match_time}".replace(' ', '_').lower()
                type_match = 'inplay' if 'IP' in source_url else 'prematch'
                
                match_data = {
                    "match_id": match_id,
                    "home_team": match_info['home_team'],
                    "away_team": match_info['away_team'],
                    "league": league,
                    "match_time": match_time,
                    "odds": match_info['odds'],
                    "type": type_match,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if match_id not in all_matches or json.dumps(all_matches[match_id]['odds'], sort_keys=True) != json.dumps(match_data['odds'], sort_keys=True):
                    all_matches[match_id] = match_data
                    updated = True
                    logging.info(f"[*] Added standalone odds match: {match_data['home_team']} vs {match_data['away_team']} with {len(match_data['odds'])} odds")
        
        if updated and all_matches:
            try:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(list(all_matches.values()), f, indent=4, sort_keys=True)
                logging.info(f"[+] Saved {len(all_matches)} unique matches to {OUTPUT_FILE}")
            except Exception as e:
                logging.error(f"[!] Error saving to {OUTPUT_FILE}: {e}")
        else:
            logging.info("[*] No new/unique data, skipping save")
            
    except Exception as e:
        logging.error(f"[!] Error parsing HTML from {source_url}: {e}")

async def handle_response(response, page):
    content_type = response.headers.get('content-type', '')
    if 'text/html' in content_type:
        try:
            text = await response.text()
            if '<div' in text:
                await parse_html_data(page, response.url)
        except Exception as e:
            logging.error(f"[!] Error reading HTML from {response.url}: {e}")
    elif 'application/json' in content_type:
        try:
            json_data = await response.json()
            logging.info(f"[*] JSON response from {response.url}: {json.dumps(json_data, indent=2)[:500]}...")  # Log first 500 chars
            # TODO: Parse match data from JSON if it contains odds/events
            # For now, just log to identify useful endpoints
        except Exception as e:
            logging.error(f"[!] Error reading JSON from {response.url}: {e}")

async def navigate_with_retry(page, url, retries=3):
    for attempt in range(retries):
        try:
            logging.info(f"[*] Navigating to {url} (attempt {attempt + 1}/{retries})")
            # For SPA, first go to base URL, then set hash
            base_url = url.split('#')[0]
            hash_part = '#/' + url.split('#', 1)[1] if '#' in url else ''
            await page.goto(base_url, wait_until="load", timeout=60000)
            if hash_part:
                await page.evaluate(f"window.location.hash = '{hash_part}'")
            await page.wait_for_timeout(5000)  # Wait for SPA to load content
            return True
        except Exception as e:
            logging.error(f"[!] Navigation to {url} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(1, 3))
    return False

async def main():
    # Test AI
    if test_ai():
        logging.info("[*] AI is working")
    else:
        logging.info("[*] AI is not working")
    
    headers, cookies = await load_config()
    if not headers or not cookies:
        logging.error("[!] Failed to load/generate config, exiting")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="pw_profile",
            headless=False,
            channel="chrome",
            no_viewport=True
        )
        context = browser
        
        try:
            await context.add_cookies([{"name": k, "value": v, "domain": ".bet365.com", "path": "/"} for k, v in cookies.items()])
            page = await context.new_page()
            await page.route("**/*", intercept_request)
            page.on("response", lambda response: handle_response(response, page))

            # Focus on key pages with high data likelihood - expanded for more sports
            key_paths = ["#HO", "#IP/B1", "#AS/B1", "#IP/B16", "#AS/B12", "#IP/B8", "#AS/B8", "#IP/B18", "#AS/B18",
                         "#AS/B2", "#AS/B13", "#AS/B3", "#AS/B4", "#AS/B5", "#AS/B6", "#AS/B7", "#AS/B9", "#AS/B10",
                         "#AS/B11", "#AS/B14", "#AS/B15", "#AS/B17", "#AS/B19", "#AS/B20", "#AS/B21", "#AS/B22",
                         "#IP/B2", "#IP/B13", "#IP/B3", "#IP/B4", "#IP/B5", "#IP/B6", "#IP/B7", "#IP/B9", "#IP/B10",
                         "#IP/B11", "#IP/B14", "#IP/B15", "#IP/B17", "#IP/B19", "#IP/B20", "#IP/B21", "#IP/B22"]
            
            for path in key_paths:
                full_url = BASE_URL + path
                if not await navigate_with_retry(page, full_url):
                    logging.error(f"[!] Failed to navigate to {path}")
                    continue
                await parse_html_data(page, full_url)
                await asyncio.sleep(random.uniform(2, 5))

            start_time = time.time()
            total_start = time.time()
            max_runtime = 300  # 5 minutes for proper data collection
            
            while True:
                if time.time() - total_start > max_runtime:
                    logging.info("[*] Runtime completed, stopping")
                    break
                
                try:
                    await asyncio.sleep(1)
                    if time.time() - start_time > REFRESH_INTERVAL:
                        random.shuffle(key_paths)
                        for path in key_paths[:15]:  # Check more paths for better coverage
                            full_url = BASE_URL + path
                            if await navigate_with_retry(page, full_url):
                                await parse_html_data(page, full_url)
                                await asyncio.sleep(random.uniform(1, 3))
                        logging.info(f"[*] Periodic check: {len(all_matches)} unique matches")
                        start_time = time.time()
                except Exception as e:
                    logging.error(f"[!] Error in periodic loop: {e}")
                    if "TargetClosedError" in str(e):
                        logging.info("[*] Browser context closed, restarting...")
                        break  # Exit loop to restart
                    await asyncio.sleep(5)  # Wait before retry
                    
        except Exception as e:
            logging.error(f"[!] Error in main loop: {e}")
        finally:
            logging.info(f"[*] Collected {len(api_urls)} API URLs")
            await browser.close()

if __name__ == "__main__":
    logging.info("[*] Starting Bet365 data scraper")
    asyncio.run(main())