<<<<<<< HEAD
"""
Bet365 Odds Scraper - Main Entry Point

This is the refactored, modular version of the bet365 odds scraper.
Run this file to start the scraping process.

Usage:
    python main.py [options]
    
Options:
    --sports: Comma-separated list of sport codes (default: B1,B2,B8,B9,B13)
    --interval: Refresh interval in seconds (default: 30)
    --no-inplay: Skip in-play markets (default: include both pre-match and in-play)
    --single-run: Run once instead of continuous loop
    --log-level: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

import asyncio
import argparse
import logging
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.scraper.bet365_scraper import Bet365Scraper
from src.config.settings import Config
from src.utils.logger import Logger
from src.utils.constants import DEFAULT_SPORT_CODES, SPORT_CODES

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Bet365 Odds Scraper')
    
    parser.add_argument(
        '--sports',
        type=str,
        default=','.join(DEFAULT_SPORT_CODES),
        help='Comma-separated list of sport codes (e.g., B1,B2,B8)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Refresh interval in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--no-inplay',
        action='store_true',
        help='Skip in-play markets, only scrape pre-match'
    )
    
    parser.add_argument(
        '--single-run',
        action='store_true',
        help='Run once instead of continuous loop'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--list-sports',
        action='store_true',
        help='List available sport codes and exit'
    )
    
    return parser.parse_args()

def list_available_sports():
    """List all available sport codes"""
    print("\\nAvailable Sport Codes:")
    print("=" * 50)
    for code, sport in SPORT_CODES.items():
        print(f"{code}: {sport}")
    print(f"\\nDefault sports: {', '.join(DEFAULT_SPORT_CODES)}")
    print("=" * 50)

def validate_sport_codes(sport_codes_str: str) -> list:
    """Validate and return list of sport codes"""
    sport_codes = [code.strip().upper() for code in sport_codes_str.split(',')]
    
    invalid_codes = [code for code in sport_codes if code not in SPORT_CODES]
    if invalid_codes:
        print(f"Warning: Invalid sport codes: {', '.join(invalid_codes)}")
        print("Use --list-sports to see available codes")
    
    valid_codes = [code for code in sport_codes if code in SPORT_CODES]
    
    if not valid_codes:
        print("No valid sport codes provided, using defaults")
        return DEFAULT_SPORT_CODES
    
    return valid_codes

async def run_single_scrape(scraper: Bet365Scraper, sport_codes: list, include_inplay: bool):
    """Run a single scraping session"""
    logger = Logger.get_default_logger()
    
    try:
        # Initialize scraper
        if not await scraper.initialize():
            logger.error("Failed to initialize scraper")
            return False
        
        # Start browser
        if not await scraper.start_browser():
            logger.error("Failed to start browser")
            return False
        
        # Scrape data
        matches = await scraper.scrape_all_sports(sport_codes, include_inplay)
        
        # Save data
        await scraper.save_data()
        
        # Print statistics
        stats = scraper.get_stats()
        logger.info(f"\\n=== Scraping Complete ===")
        logger.info(f"Total unique matches: {stats['total_matches']}")
        logger.info(f"API URLs discovered: {stats['api_urls_discovered']}")
        logger.info(f"AI calls used: {stats['ai_calls_used']}/{stats['ai_calls_used'] + stats['ai_calls_remaining']}")
        logger.info(f"Runtime: {stats['runtime_seconds']:.1f}s")
        logger.info(f"Matches per minute: {stats['matches_per_minute']:.1f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Single scrape failed: {e}")
        return False
    finally:
        await scraper.cleanup()

async def run_continuous_scrape(scraper: Bet365Scraper, sport_codes: list, 
                              include_inplay: bool, refresh_interval: int):
    """Run continuous scraping"""
    try:
        await scraper.run_continuous(
            sport_codes=sport_codes,
            refresh_interval=refresh_interval
        )
    except KeyboardInterrupt:
        print("\\nStopping scraper...")
    except Exception as e:
        logger = Logger.get_default_logger()
        logger.error(f"Continuous scrape failed: {e}")
    finally:
        await scraper.cleanup()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Handle list sports command
    if args.list_sports:
        list_available_sports()
        return
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    logger = Logger.setup_logger(level=log_level)
    
    # Validate sport codes
    sport_codes = validate_sport_codes(args.sports)
    include_inplay = not args.no_inplay
    
    # Print configuration
    logger.info("=== Bet365 Scraper Configuration ===")
    logger.info(f"Sport codes: {', '.join(sport_codes)}")
    logger.info(f"Sports: {', '.join([SPORT_CODES[code] for code in sport_codes])}")
    logger.info(f"Include in-play: {include_inplay}")
    logger.info(f"Refresh interval: {args.interval}s")
    logger.info(f"Mode: {'Single run' if args.single_run else 'Continuous'}")
    logger.info(f"Log level: {args.log_level}")
    logger.info("=" * 40)
    
    # Create scraper instance
    config = Config()
    config.refresh_interval = args.interval
    scraper = Bet365Scraper(config)
    
    # Run scraper
    try:
        if args.single_run:
            asyncio.run(run_single_scrape(scraper, sport_codes, include_inplay))
        else:
            asyncio.run(run_continuous_scrape(scraper, sport_codes, include_inplay, args.interval))
    except KeyboardInterrupt:
        logger.info("\\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
=======
import os
import json
import time
import traceback
import asyncio
from datetime import datetime, timezone

import httpx
import patchright
from patchright.async_api import async_playwright

CONFIG_FILE = "config.json"
OUTPUT_FILE = "bet365_data.json"
REFRESH_INTERVAL = 30  # seconds
LOGIN_URL = "https://www.bet365.com/#/IP/B1"

def load_config():
    """Load headers + cookies from config.json, create skeleton if missing."""
    if not os.path.exists(CONFIG_FILE):
        template = {
            "headers": {
                "User-Agent": "",
                "Accept": "application/json",
                "Referer": "https://www.bet365.com/"
            },
            "cookies": ""
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4)
        print(f"[!] config.json created. Please run to auto-capture, or fill manually.")
        return None, None

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    headers = cfg.get("headers", {})
    cookie_str = cfg.get("cookies", "")
    cookies = {}
    if cookie_str:
        for pair in cookie_str.split(";"):
            if "=" in pair:
                key, val = pair.strip().split("=", 1)
                cookies[key] = val
    return headers, cookies

async def capture_headers_and_cookies():
    """Use patchright to launch a persistent Playwright browser, capture cookies & headers."""
    # Ensure patchright installed Chromium
    # In your environment: `patchright install chromium` before running this script

    async with async_playwright() as p:
        # Note: patchright modifies Playwright under the hood, so using patchright's import is enough.
        # Launch a persistent context (user_data_dir) to mimic a real browser profile
        user_data_dir = "pw_profile"  # directory to save profile data
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome",  # or "chromium" depending on what's installed
            # Do NOT override user agent, viewport, or other obvious flags
            # patchright ensures stealth patches
        )

        page = await browser.new_page()
        print("[*] Please log in manually to bet365 if required.")
        await page.goto(LOGIN_URL)
        # Wait long enough for you to log in; adjust as needed
        await asyncio.sleep(45)

        # After login/site loaded, capture cookies and headers
        cookies_list = await browser.cookies()  # persistent context cookies
        # Build cookie header string
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies_list)

        # Get a realistic user agent from the browser
        user_agent = await page.evaluate("() => navigator.userAgent")

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Referer": "https://www.bet365.com/"
        }

        cfg = {"headers": headers, "cookies": cookie_str}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

        print("[+] Saved session headers & cookies to config.json")

        # We can close browser after capturing
        await browser.close()

        return headers, cookies_list

def fetch_inplay_events(headers, cookies):
    url = "https://www.bet365.com/SportsBook.API/web?zid=0&pd=%23AC%23B1&cid=171&ctid=171"
    resp = httpx.get(url, headers=headers, cookies=cookies, timeout=20)
    resp.raise_for_status()
    return resp.json()

def parse_event(e):
    event_id = e.get("ID") or e.get("FI") or e.get("EventId") or ""
    name = e.get("NA", "")
    if " v " in name:
        home, away = name.split(" v ", 1)
    else:
        home = name
        away = ""
    league = ""
    # Try different possible paths
    if "CL" in e:
        cl = e.get("CL")
        # sometimes CL is dict with NA
        league = cl.get("NA", "") if isinstance(cl, dict) else str(cl)
    if not league:
        league = "unknown"
    ts = e.get("TS")
    match_time = None
    if isinstance(ts, (int, float)):
        match_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return {
        "match_id": event_id,
        "home_team": home.strip(),
        "away_team": away.strip(),
        "league": league.strip(),
        "match_time": match_time,
        "odds": {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def fetch_markets_for_event(event_id, headers, cookies):
    # The parameter “pd” or some API path might differ; you may need to adjust based on what you observe in network traffic
    url = f"https://www.bet365.com/SportsBook.API/web?zid=0&pd=%23AC%23B1C%23{event_id}&cid=171&ctid=171"
    resp = httpx.get(url, headers=headers, cookies=cookies, timeout=20)
    resp.raise_for_status()
    return resp.json()

def parse_markets(event_data, mj):
    odds = {}
    if not mj:
        return
    # Different API structures: sometimes markets in “Markets”, sometimes nested
    markets = mj.get("Markets") or mj.get("Market") or []
    for m in markets:
        m_name = m.get("NA", "")
        if not m_name:
            continue
        key_m = m_name.lower().replace(" ", "_")
        parts = m.get("Participants") or m.get("PA") or []
        for p in parts:
            p_name = p.get("NA", "")
            price = p.get("OD") or p.get("Price") or p.get("Value")
            if p_name and price is not None:
                try:
                    price_f = float(price)
                except:
                    continue
                key = f"{key_m}:{p_name.lower().replace(' ', '_')}"
                odds[key] = price_f
    event_data["odds"] = odds

async def main():
    headers, cookies = load_config()
    cookies_dict = {}
    if not headers or not cookies:
        headers, cookies_list = await capture_headers_and_cookies()
        cookies_dict = {c["name"]: c["value"] for c in cookies_list}
    else:
        cookies_dict = cookies

    all_matches = {}

    while True:
        try:
            print(f"[*] {datetime.now(timezone.utc).isoformat()} ‒ fetching in-play events")
            data = fetch_inplay_events(headers, cookies_dict)
            events = data.get("Events") or data.get("events") or []
            for e in events:
                parsed = parse_event(e)
                if not parsed["match_id"]:
                    continue
                # update or insert
                all_matches[parsed["match_id"]] = parsed

                # fetch odds / markets
                try:
                    mj = fetch_markets_for_event(parsed["match_id"], headers, cookies_dict)
                    parse_markets(parsed, mj)
                except Exception as ex:
                    print(f"[!] error fetching markets for {parsed['match_id']}: {ex}")

            # Save
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(list(all_matches.values()), f, indent=4)

            print(f"[+] saved {len(all_matches)} matches with odds")

            time.sleep(REFRESH_INTERVAL)

        except httpx.HTTPStatusError as httpe:
            print(f"[!] HTTP error {httpe.response.status_code} – probably needs re-login or cookies expired")
            # renew cookies
            headers, cookies_list = await capture_headers_and_cookies()
            cookies_dict = {c["name"]: c["value"] for c in cookies_list}

        except Exception as e:
            print("[!] Unexpected error:", e)
            traceback.print_exc()
            time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> a8ab2463fd11289d44fe84ccf468ee58ed3b9907
