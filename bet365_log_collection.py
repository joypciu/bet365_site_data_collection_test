import os
import json
import time
import asyncio
import random
from datetime import datetime, timezone
import re
from patchright.async_api import async_playwright
import logging

# Setup logging to a single file
logging.basicConfig(filename='bet365_scraper.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

async def generate_config():
    logging.info("[*] Generating config using patchright")
    async with async_playwright() as p:
        user_data_dir = "pw_profile"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome",
        )
        page = await browser.new_page()
        logging.info(f"[*] Navigating to {BASE_URL} for config generation")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        logging.info("[*] Please log in manually to bet365 if required.")
        await asyncio.sleep(45)
        cookies_list = await page.context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)
        user_agent = await page.evaluate("() => navigator.userAgent")
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.bet365.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1"
        }
        cfg = {"headers": headers, "cookies": cookie_str}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        logging.info("[+] Generated and saved config.json")
        await browser.close()
        return headers, {c['name']: c['value'] for c in cookies_list}

async def load_config():
    if not os.path.exists(CONFIG_FILE):
        logging.info("[*] Config file not found, generating new one")
        return await generate_config()
    logging.info("[*] Loading existing config")
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
        await route.continue_(headers=headers)
    else:
        await route.continue_()

async def handle_response(response):
    logging.info(f"[*] Handling response: {response.url} (status: {response.status})")
    if "bet365.com" in response.url and any(x in response.url.lower() for x in ["sportsbook", "inplay", "contentapi", "event"]):
        api_urls.add(response.url)
        try:
            content_type = response.headers.get('content-type', '')
            logging.info(f"[*] Content-Type: {content_type}")
            scrappable = False
            data_type = "unknown"
            related_data = f"Status: {response.status}, Headers: {response.headers}"
            if 'text/html' in content_type:
                data_type = "HTML"
                text = await response.text()
                if '<div' in text or '<class' in text:
                    scrappable = True
            elif 'application/json' in content_type:
                data_type = "JSON"
                text = await response.text()
                try:
                    json.loads(text)
                    scrappable = True
                except json.JSONDecodeError:
                    scrappable = False
            elif 'image' in content_type:
                data_type = "Image"
                scrappable = False
            elif 'font' in content_type:
                data_type = "Font"
                scrappable = False
            else:
                data_type = content_type
                scrappable = False

            logging.info(f"URL: {response.url}, Data Type: {data_type}, Scrappable: {scrappable}, Related Data: {related_data}")

            if 'text' in content_type or 'application/json' in content_type:
                text = await response.text()
                if '|' in text or ';' in text:
                    prefix = text[0:2] if len(text) > 1 else ''
                    is_update = prefix in ['C|', 'U|']
                    data_str = text[2:] if prefix in ['I|', 'C|', 'U|'] else text
                    logging.info(f"[*] Parsing Bet365 data (is_update: {is_update})")
                    parse_bet365_data(data_str, is_update)
                    extract_matches(response.url)
        except Exception as e:
            logging.error(f"[!] Error handling response from {response.url}: {e}")

async def handle_websocket(ws):
    logging.info(f"[*] WebSocket opened: {ws.url}")
    if "bet365.com" in ws.url and "push" in ws.url.lower():
        api_urls.add(ws.url)
        async def handle_frame(frame):
            try:
                text = frame if isinstance(frame, str) else frame.decode('utf-8', errors='ignore')
                logging.info(f"[*] WebSocket frame from {ws.url} (first 500 chars): {text[:500]}")
                prefix = text[0:2] if len(text) > 1 else ''
                is_update = prefix in ['C|', 'U|']
                data_str = text[2:] if prefix in ['I|', 'C|', 'U|'] else text
                parse_bet365_data(data_str, is_update)
                extract_matches(ws.url)
            except Exception as e:
                logging.error(f"[!] Error handling WebSocket frame: {e}")
        ws.on("framereceived", handle_frame)

async def collect_sports(page):
    global sports_list
    try:
        logging.info("[*] Collecting sports dynamically")
        title = await page.title()
        logging.info(f"[*] Page title: {title}")
        content_length = len(await page.content())
        logging.info(f"[*] Page content length: {content_length}")

        # Extract important divs, classes, selectors
        page_details = await page.evaluate("""
            () => {
                const allClasses = new Set();
                const allIds = new Set();
                const allSelectors = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.className) {
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
        logging.info(f"Important classes for {page.url}: {', '.join(page_details['classes'][:50])}")  # Limit to 50 for brevity
        logging.info(f"Important IDs for {page.url}: {', '.join(page_details['ids'][:50])}")

        # Dynamic sports collection
        sports = await page.evaluate("""
            () => {
                const commonSports = ['Soccer', 'Tennis', 'Basketball', 'Baseball', 'American Football', 'Ice Hockey', 'Golf', 'Boxing', 'MMA', 'Cricket', 'Rugby', 'Darts', 'Snooker', 'Table Tennis', 'Volleyball', 'Handball', 'Esports', 'Cycling', 'Motor Sports', 'Horse Racing', 'Greyhounds'];
                const allElements = document.querySelectorAll('a, div, li, span');
                let foundSports = [];
                allElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (commonSports.includes(text) && el.closest('nav, .menu, .sidebar, .header')) {
                        foundSports.push(text);
                    }
                });
                return [...new Set(foundSports)];
            }
        """)
        sports_list = sports
        logging.info(f"[+] Collected {len(sports_list)} sports dynamically: {', '.join(sports_list)}")
        # Scrappability: if found sports or classes
        scrappable = len(sports_list) > 0 or len(page_details['classes']) > 0
        logging.info(f"URL: {page.url}, Data Type: HTML, Scrappable: {scrappable}, Related Data: Title - {title}, Content Length - {content_length}")
    except Exception as e:
        logging.error(f"[!] Error collecting sports dynamically: {e}")

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

def parse_bet365_data(data_str, is_update=False):
    logging.info(f"[*] Parsing Bet365 data, is_update={is_update}, data_str length={len(data_str)}")
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
                            pass
            if not home or not away or home.isdigit() or away.isdigit():
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
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(list(all_matches.values()), f, indent=4)
        logging.info(f"[+] Saved {len(all_matches)} matches ({match_type}) with odds")

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

        logging.info(f"[*] Navigating to {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        await collect_sports(page)

        sports_paths = [
            f"#/IP/B{sid}" for sid in range(1, 100)
        ] + [
            f"#/AS/B{sid}" for sid in range(1, 100)
        ]
        for path in sports_paths:
            try:
                logging.info(f"[*] Navigating to {BASE_URL + path}")
                await page.goto(BASE_URL + path, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(5)
            except:
                logging.error(f"[!] Navigation to {path} failed")
                continue

        logging.info(f"[+] Discovered {len(api_urls)} API/WebSocket URLs:")
        for url in sorted(api_urls):
            logging.info(url)
        logging.info(f"[+] Discovered {len(sports_list)} sports:")
        logging.info(", ".join(sports_list))
        logging.info("[+] Data collected: Matches (prematch and inplay), odds, leagues, timestamps")

        await browser.close()

async def main():
    headers, cookies = await load_config()
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="pw_profile",
            headless=False,
            channel="chrome"
        )
        context = browser
        await context.add_cookies([{"name": k, "value": v, "domain": ".bet365.com", "path": "/"} for k, v in cookies.items()])
        page = await context.new_page()
        await page.route("**/*", intercept_request)
        page.on("response", handle_response)
        page.on("websocket", handle_websocket)

        logging.info("[*] Navigating to in-play soccer")
        await page.goto(BASE_URL + "#/IP/B1", wait_until="networkidle", timeout=60000)
        await collect_sports(page)
        logging.info("[*] Navigating to prematch soccer")
        await page.goto(BASE_URL + "#/AS/B1", wait_until="networkidle", timeout=60000)

        start_time = time.time()
        while True:
            await asyncio.sleep(1)
            if time.time() - start_time > REFRESH_INTERVAL:
                extract_matches("manual_periodic")
                logging.info(f"[*] Periodic save: {len(all_matches)} matches")
                start_time = time.time()

if __name__ == "__main__":
    asyncio.run(discover_urls_and_sports())
    asyncio.run(main())