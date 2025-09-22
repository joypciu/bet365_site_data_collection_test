import os
import json
import logging
from typing import Dict, Tuple, Optional

class Config:
    """Configuration manager for bet365 scraper"""
    
    def __init__(self):
        self.config_file = "config.json"
        self.output_file = "bet365_data.json"
        self.refresh_interval = 30
        self.base_url = "https://www.co.bet365.com/#/HO/"
        self.max_ai_calls = 10
        self.headers = {}
        self.cookies = {}
        
    async def load_config(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Load configuration from file or generate new one"""
        if not os.path.exists(self.config_file):
            logging.info("[*] Config file not found, generating new one")
            return await self.generate_config()
        
        logging.info("[*] Loading config")
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
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
            return await self.generate_config()
    
    async def generate_config(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Generate new configuration using browser automation"""
        from patchright.async_api import async_playwright
        
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
            config_url = self.base_url + "#HO"
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
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)
                logging.info("[+] Saved config.json")
                await browser.close()
                return headers, {c['name']: c['value'] for c in cookies_list}
            except Exception as e:
                logging.error(f"[!] Error generating config: {e}")
                await browser.close()
                return None, None
    
    def save_data(self, data: Dict):
        """Save scraped data to output file"""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logging.info(f"[+] Saved {len(data)} matches to {self.output_file}")
        except Exception as e:
            logging.error(f"[!] Error saving data: {e}")