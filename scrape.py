import os
import json
import time
import asyncio
import random
from datetime import datetime, timezone
import re
import logging
from patchright.async_api import async_playwright

# Setup logging to a single file
logging.basicConfig(
    filename='bet365_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# User agents for randomization
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

CONFIG_FILE = "config.json"
OUTPUT_FILE = "bet365_data.json"
REFRESH_INTERVAL = 30
BASE_URL = "https://www.bet365.com/"
all_matches = {}
entities = {"leagues": {}}
api_urls = set()
sports_list = []
captured_selectors = set()

async def generate_config():
    logging.info("[*] Generating config using patchright")
    async with async_playwright() as p:
        user_data_dir = "pw_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome"
        )
        page = await browser.new_page()
        logging.info(f"[*] Navigating to {BASE_URL} for config generation")
        try:
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            logging.info("[*] Please log in manually to bet365 if required.")
            await asyncio.sleep(45)  # Allow time for manual login
            cookies_list = await page.context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)
            user_agent = await page.evaluate("() => navigator.userAgent")
            headers = {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.bet365.com/",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            cfg = {"headers": headers, "cookies": cookie_str}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            logging.info("[+] Generated and saved config.json")
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
    logging.info("[*] Loading existing config")
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
        logging.error(f"[!] Error loading config: {e}")
        return None, None

async def intercept_request(route, request):
    if route is None:
        logging.warning("[!] Warning: Route is None, skipping interception")
        return
    logging.info(f"[*] Intercepting request: {request.url}")
    if "bet365.com" in request.url:
        api_urls.add(request.url)
        headers = request.headers
        headers["User-Agent"] = random.choice(user_agents)
        headers["Accept"] = "*/*"
        headers["Accept-Language"] = "en-US,en;q=0.9"
        headers["Accept-Encoding"] = "gzip, deflate, br"
        headers["Cache-Control"] = "no-cache"
        headers["Pragma"] = "no-cache"
        headers["Connection"] = "keep-alive"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Site"] = "same-origin"
        try:
            await route.continue_(headers=headers)
        except Exception as e:
            logging.error(f"[!] Error in intercept_request for {request.url}: {e}")
    else:
        try:
            await route.continue_()
        except Exception as e:
            logging.error(f"[!] Error continuing non-bet365 route for {request.url}: {e}")

async def handle_response(response):
    content_type = response.headers.get('content-type', '')
    if 'image' in content_type:
        return
    logging.info(f"[*] Handling response: {response.url} (status: {response.status})")
    logging.info(f"[*] Content-Type: {content_type}")
    scrappable = False
    data_type = "unknown"
    related_data = f"Status: {response.status}, Headers: {response.headers}"
    
    if 'text/html' in content_type:
        data_type = "HTML"
        try:
            text = await response.text()
            scrappable = '<div' in text or '<class' in text
            logging.info(f"URL: {response.url}, Data Type: {data_type}, Scrappable: {scrappable}, Related Data: {related_data}")
        except Exception as e:
            logging.error(f"[!] Error reading HTML response from {response.url}: {e}")
    elif 'application/json' in content_type:
        data_type = "JSON"
        try:
            text = await response.text()
            json_data = json.loads(text)
            scrappable = True
            logging.info(f"URL: {response.url}, Data Type: {data_type}, Scrappable: {scrappable}, Related Data: {related_data}, First 1000 chars: {text[:1000]}")
            if isinstance(json_data, dict) and 'data' in json_data:
                parse_json_data(json_data['data'])
        except json.JSONDecodeError:
            scrappable = False
            logging.warning(f"[!] JSON decode error for {response.url}: {text[:1000]}")
        except Exception as e:
            logging.error(f"[!] Error reading JSON response from {response.url}: {e}")
    elif 'font' in content_type:
        data_type = "Font"
        scrappable = False
        logging.info(f"URL: {response.url}, Data Type: {data_type}, Scrappable: {scrappable}, Related Data: {related_data}")
    else:
        data_type = content_type
        scrappable = False
        logging.info(f"URL: {response.url}, Data Type: {data_type}, Scrappable: {scrappable}, Related Data: {related_data}")
    
    if "bet365.com" in response.url and any(x in response.url.lower() for x in ["sportsbook", "inplay", "contentapi", "event", "pullpodapi", "leftnavcontentapi"]):
        api_urls.add(response.url)
        try:
            if 'text' in content_type or 'application/json' in content_type:
                try:
                    text = await response.text()
                except UnicodeDecodeError:
                    logging.warning(f"[!] UnicodeDecodeError for {response.url}, attempting binary read")
                    text = (await response.body()).decode('utf-8', errors='ignore')
                if '|' in text or ';' in text:
                    prefix = text[0:2] if len(text) > 1 else ''
                    is_update = prefix in ['C|', 'U|']
                    data_str = text[2:] if prefix in ['I|', 'C|', 'U|'] else text
                    logging.info(f"[*] Parsing Bet365 pipe-delimited data (is_update: {is_update}, length: {len(data_str)})")
                    parse_bet365_data(data_str, is_update)
                    extract_matches(response.url)
                else:
                    logging.info(f"[*] No pipe-delimited data found in {response.url}, raw content: {text[:1000]}")
        except Exception as e:
            logging.error(f"[!] Error handling response from {response.url}: {e}")

async def handle_websocket(ws):
    logging.info(f"[*] WebSocket opened: {ws.url}")
    if "bet365.com" in ws.url and "push" in ws.url.lower():
        api_urls.add(ws.url)
        async def handle_frame(frame):
            try:
                text = frame if isinstance(frame, str) else frame.decode('utf-8', errors='ignore')
                logging.info(f"[*] WebSocket frame from {ws.url} (first 1000 chars): {text[:1000]}")
                logging.info(f"URL: {ws.url}, Data Type: WebSocket, Scrappable: True, Related Data: Frame length - {len(text)}")
                prefix = text[0:2] if len(text) > 1 else ''
                is_update = prefix in ['C|', 'U|']
                data_str = text[2:] if prefix in ['I|', 'C|', 'U|'] else text
                parse_bet365_data(data_str, is_update)
                extract_matches(ws.url)
            except Exception as e:
                logging.error(f"[!] Error handling WebSocket frame from {ws.url}: {e}")
        ws.on("framereceived", handle_frame)

async def generate_selectors(page):
    global captured_selectors
    try:
        logging.info("[*] Generating selectors dynamically")
        common_sports = [
            'Soccer', 'Tennis', 'Basketball', 'Baseball', 'American Football', 'Ice Hockey', 'Golf',
            'Boxing', 'MMA', 'Cricket', 'Rugby League', 'Rugby Union', 'Darts', 'Snooker', 'Table Tennis',
            'Volleyball', 'Handball', 'Esports', 'Cycling', 'Motor Sports', 'Horse Racing', 'Greyhounds'
        ]
        selectors = await page.evaluate("""
            (commonSports) => {
                const selectors = [];
                const elements = document.querySelectorAll('a, div, span, li');
                elements.forEach(el => {
                    const text = el.textContent.trim();
                    const hasSport = commonSports.some(sport => text.toLowerCase().includes(sport.toLowerCase()));
                    const hasMatch = text.includes(' v ') || text.includes(' - ');
                    if (hasSport || hasMatch || el.hasAttribute('data-sport-id') || el.className.includes('ovm-Classification') || el.className.includes('wn-Classification')) {
                        let selector = '';
                        if (el.id) {
                            selector = `#${el.id}`;
                        } else if (el.className && typeof el.className === 'string' && el.className.trim()) {
                            const classes = el.className.split(' ').filter(cls => cls).join('.');
                            selector = `${el.tagName.toLowerCase()}.${classes}`;
                        } else if (el.hasAttribute('data-sport-id')) {
                            selector = `[data-sport-id="${el.getAttribute('data-sport-id')}"]`;
                        } else if (el.hasAttribute('href') && (el.getAttribute('href').includes('/#/IP/') || el.getAttribute('href').includes('/#/AS/'))) {
                            selector = `a[href*="${el.getAttribute('href').split('#')[1]}"]`;
                        } else {
                            selector = `${el.tagName.toLowerCase()}[data-selector="${text.replace(/[^a-zA-Z0-9]/g, '_')}"]`;
                            el.setAttribute('data-selector', text.replace(/[^a-zA-Z0-9]/g, '_'));
                        }
                        selectors.push({
                            selector: selector,
                            text: text,
                            tag: el.tagName.toLowerCase(),
                            attributes: Object.fromEntries([...el.attributes].map(attr => [attr.name, attr.value]))
                        });
                    }
                });
                return selectors;
            }
        """, common_sports)
        for sel in selectors:
            captured_selectors.add(sel['selector'])
        logging.info(f"[*] Generated {len(selectors)} selectors: {json.dumps(selectors[:50], indent=2)}")
        return selectors
    except Exception as e:
        logging.error(f"[!] Error generating selectors: {e}")
        return []

async def collect_sports(page):
    global sports_list
    try:
        logging.info("[*] Collecting sports dynamically")
        title = await page.title()
        content_length = len(await page.content())
        logging.info(f"[*] Page title: {title}")
        logging.info(f"[*] Page content length: {content_length}")

        try:
            await page.wait_for_selector("nav, .menu, .sidebar, .header, .ovm-Classification, .wn-Classification, [data-sport-id]", timeout=15000)
        except Exception as e:
            logging.warning(f"[!] Timeout waiting for navigation selectors: {e}")

        page_details = await page.evaluate("""
            () => {
                const allClasses = new Set();
                const allIds = new Set();
                document.querySelectorAll('*').forEach(el => {
                    if (el.className && typeof el.className === 'string') {
                        el.className.split(' ').forEach(cls => {
                            if (cls) allClasses.add('.' + cls);
                        });
                    }
                    if (el.id) allIds.add('#' + el.id);
                });
                return {
                    classes: Array.from(allClasses),
                    ids: Array.from(allIds)
                };
            }
        """)
        logging.info(f"Important classes for {page.url}: {', '.join(page_details['classes'][:50])}")
        logging.info(f"Important IDs for {page.url}: {', '.join(page_details['ids'][:50])}")

        await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        await asyncio.sleep(random.uniform(0.5, 1.5))

        selectors = await generate_selectors(page)
        sports = []
        for sel in selectors:
            text = sel['text']
            if any(sport.lower() in text.lower() for sport in [
                'Soccer', 'Tennis', 'Basketball', 'Baseball', 'American Football', 'Ice Hockey', 'Golf',
                'Boxing', 'MMA', 'Cricket', 'Rugby League', 'Rugby Union', 'Darts', 'Snooker'
            ]):
                sports.append(text)
        sports_list = list(set(sports_list + sports))
        scrappable = len(sports_list) > 0 or len(page_details['classes']) > 0
        logging.info(f"[+] Collected {len(sports_list)} sports dynamically: {', '.join(sports_list)}")
        logging.info(f"URL: {page.url}, Data Type: HTML, Scrappable: {scrappable}, Related Data: Title - {title}, Content Length - {content_length}")

        dom_snippet = await page.evaluate("() => document.body.outerHTML.substring(0, 1000)")
        logging.info(f"[*] DOM snippet (first 1000 chars): {dom_snippet}")
    except Exception as e:
        logging.error(f"[!] Error collecting sports dynamically for {page.url}: {e}")

def parse_json_data(data):
    logging.info("[*] Attempting to parse JSON data")
    try:
        if isinstance(data, list):
            for item in data:
                if 'name' in item and 'events' in item:
                    league_name = item.get('name', 'unknown')
                    for event in item.get('events', []):
                        event_id = event.get('id')
                        name = event.get('name', '')
                        home = away = ''
                        if ' v ' in name:
                            home, away = name.split(' v ', 1)
                        elif '-' in name:
                            home, away = name.split('-', 1)
                        match_time = event.get('startTime') or event.get('time')
                        odds = {}
                        for market in event.get('markets', []):
                            m_name = market.get('name', '').lower().replace(' ', '_')
                            for outcome in market.get('outcomes', []):
                                o_name = outcome.get('name', '').lower().replace(' ', '_')
                                od = outcome.get('odds')
                                if od:
                                    try:
                                        odds[f"{m_name}:{o_name}"] = round(float(od), 2)
                                    except (ValueError, TypeError):
                                        logging.warning(f"[!] Invalid odds format in JSON: {od}")
                        if not home or not away:
                            continue
                        match_data = {
                            "match_id": event_id,
                            "home_team": home.strip(),
                            "away_team": away.strip(),
                            "league": league_name,
                            "match_time": match_time,
                            "odds": odds,
                            "type": "prematch",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        all_matches[event_id] = match_data
    except Exception as e:
        logging.error(f"[!] Error parsing JSON data: {e}")

def parse_bet365_data(data_str, is_update=False):
    logging.info(f"[*] Parsing Bet365 pipe-delimited data, is_update={is_update}, data_str length={len(data_str)}")
    global entities
    if not is_update:
        entities = {"leagues": {}}
    current_cl = None
    current_fi = None
    current_ma = None
    segments = data_str.split('|')
    for seg in segments:
        if not seg:
            continue
        parts = seg.split(';')
        if is_update:
            if len(parts) > 0:
                first = parts[0]
                match = re.match(r'([A-Z]+)(\d+)', first)
                if match:
                    type_ = match.group(1)
                    id_ = match.group(2)
                    attrs = {}
                    for p in parts[1:]:
                        if '=' in p:
                            k, v = p.split('=', 1)
                            attrs[k] = v
                    update_tree(type_, id_, attrs)
                    continue
        else:
            if len(parts) == 0:
                continue
            type_ = parts[0]
            attrs = {}
            for p in parts[1:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    attrs[k] = v
            if type_ == 'CL':
                id_ = attrs.get('ID')
                if id_:
                    entities['leagues'][id_] = {'events': {}, **attrs}
                    current_cl = id_
                current_fi = None
                current_ma = None
            elif type_ == 'FI':
                id_ = attrs.get('FI') or attrs.get('ID')
                if id_ and current_cl:
                    entities['leagues'][current_cl]['events'][id_] = {'markets': {}, **attrs}
                    current_fi = id_
                current_ma = None
            elif type_ == 'MA':
                id_ = attrs.get('ID')
                if id_ and current_fi and current_cl:
                    entities['leagues'][current_cl]['events'][current_fi]['markets'][id_] = {'participants': [], **attrs}
                    current_ma = id_
            elif type_ == 'PA':
                if current_ma and current_fi and current_cl:
                    entities['leagues'][current_cl]['events'][current_fi]['markets'][current_ma]['participants'].append(attrs)

def update_tree(type_, id_, attrs):
    logging.info(f"[*] Updating tree: type={type_}, id={id_}, attrs={attrs}")
    if type_ == 'CL':
        if id_ not in entities['leagues']:
            entities['leagues'][id_] = {'events': {}}
        entities['leagues'][id_].update(attrs)
    elif type_ == 'FI':
        for league in entities['leagues'].values():
            if 'events' in league and id_ in league['events']:
                league['events'][id_].update(attrs)
                return
        if entities['leagues']:
            first_league = next(iter(entities['leagues']))
            entities['leagues'][first_league]['events'][id_] = {'markets': {}, **attrs}
    elif type_ == 'MA':
        for league in entities['leagues'].values():
            for event in league.get('events', {}).values():
                if 'markets' in event and id_ in event['markets']:
                    event['markets'][id_].update(attrs)
                    return
    elif type_ == 'PA':
        for league in entities['leagues'].values():
            for event in league.get('events', {}).values():
                for market in event.get('markets', {}).values():
                    for i, p in enumerate(market.get('participants', [])):
                        if p.get('ID') == id_:
                            market['participants'][i].update(attrs)
                            return

def extract_matches(source_url):
    logging.info(f"[*] Extracting matches from {source_url}")
    global all_matches
    updated = False
    match_type = 'inplay' if 'inplay' in source_url.lower() else 'prematch'
    for league_id, league in entities['leagues'].items():
        league_name = league.get('NA', 'unknown').strip()
        for event_id, event in league.get('events', {}).items():
            name = event.get('NA', '')
            home = away = ''
            if ' v ' in name:
                home, away = name.split(' v ', 1)
            elif '-' in name:
                home, away = name.split('-', 1)
            match_time = event.get('TS')
            if match_time and str(match_time).isdigit():
                match_time = datetime.fromtimestamp(int(match_time), tz=timezone.utc).isoformat()
            else:
                match_time = event.get('TT') or event.get('SM') or None
            odds = {}
            for market_id, market in event.get('markets', {}).items():
                m_name = market.get('NA', '').lower().replace(' ', '_')
                for p in market.get('participants', []):
                    p_name = p.get('NA', '').lower().replace(' ', '_')
                    od = p.get('OD')
                    if od:
                        try:
                            if '/' in od:
                                n, d = map(float, od.split('/'))
                                decimal_odd = n / d + 1
                            else:
                                decimal_odd = float(od)
                            odds[f"{m_name}:{p_name}"] = round(decimal_odd, 2)
                        except (ValueError, TypeError):
                            logging.warning(f"[!] Invalid odds format for market {m_name}, participant {p_name}: {od}")
                            continue
            if not home or not away or home.isdigit() or away.isdigit():
                logging.info(f"[*] Skipping invalid match: {name}")
                continue
            match_data = {
                "match_id": event_id,
                "home_team": home.strip(),
                "away_team": away.strip(),
                "league": league_name,
                "match_time": match_time,
                "odds": odds,
                "type": match_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if event_id not in all_matches or all_matches[event_id]['odds'] != odds:
                all_matches[event_id] = match_data
                updated = True
    if updated:
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(list(all_matches.values()), f, indent=4)
            logging.info(f"[+] Saved {len(all_matches)} matches ({match_type}) with odds to {OUTPUT_FILE}")
        except Exception as e:
            logging.error(f"[!] Error saving matches to {OUTPUT_FILE}: {e}")

async def navigate_with_retry(page, url, retries=3):
    for attempt in range(retries):
        try:
            logging.info(f"[*] Navigating to {url} (attempt {attempt + 1}/{retries})")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            return True
        except Exception as e:
            logging.error(f"[!] Navigation to {url} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(2, 5))
            continue
    return False

async def discover_urls_and_sports():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="pw_profile",
            headless=False,
            channel="chrome"
        )
        page = await browser.new_page()
        await page.route("**/*", intercept_request)
        page.on("response", handle_response)
        page.on("websocket", handle_websocket)

        if not await navigate_with_retry(page, BASE_URL):
            logging.error("[!] Failed to navigate to main page after retries")
            await browser.close()
            return
        await collect_sports(page)

        specific_paths = ["#/IP/B1", "#/AS/B1"]
        for path in specific_paths:
            if not await navigate_with_retry(page, BASE_URL + path):
                continue
            await collect_sports(page)

        sports_paths = (
            [f"#/IP/B{sid}" for sid in range(1, 30)] +
            [f"#/AS/B{sid}" for sid in range(1, 30)]
        )
        random.shuffle(sports_paths)
        for path in sports_paths:
            if not await navigate_with_retry(page, BASE_URL + path):
                continue
            await collect_sports(page)
            await asyncio.sleep(random.uniform(3, 7))

        logging.info(f"[+] Discovered {len(api_urls)} API/WebSocket URLs:")
        for url in sorted(api_urls):
            logging.info(url)
        logging.info(f"[+] Discovered {len(sports_list)} sports:")
        logging.info(", ".join(sports_list) if sports_list else "None")
        logging.info(f"[+] Captured {len(captured_selectors)} selectors:")
        logging.info(", ".join(list(captured_selectors)[:50]))
        logging.info("[+] Data collected: Matches (prematch and inplay), odds, leagues, timestamps")

        await browser.close()

async def main():
    headers, cookies = await load_config()
    if not headers or not cookies:
        logging.error("[!] Failed to load or generate config, exiting")
        return
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="pw_profile",
            headless=False,
            channel="chrome"
        )
        context = browser
        try:
            await context.add_cookies([{"name": k, "value": v, "domain": ".bet365.com", "path": "/"} for k, v in cookies.items()])
            page = await context.new_page()
            await page.route("**/*", intercept_request)
            page.on("response", handle_response)
            page.on("websocket", handle_websocket)

            for path in ["#/IP/B1", "#/AS/B1"]:
                if not await navigate_with_retry(page, BASE_URL + path):
                    logging.error(f"[!] Failed to navigate to {path} after retries")
                    continue
                await collect_sports(page)

            start_time = time.time()
            while True:
                await asyncio.sleep(1)
                if time.time() - start_time > REFRESH_INTERVAL:
                    extract_matches("manual_periodic")
                    logging.info(f"[*] Periodic save: {len(all_matches)} matches")
                    start_time = time.time()
        except Exception as e:
            logging.error(f"[!] Error in main loop: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    logging.info("[*] Starting Bet365 data scraper")
    asyncio.run(discover_urls_and_sports())
    asyncio.run(main())