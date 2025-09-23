import random
import asyncio

class BrowserConfig:
    """Enhanced browser configuration with stealth capabilities"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random user agent string"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_browser_options(cls):
        """Get enhanced browser launch options with stealth capabilities"""
        return {
            "headless": False,
            "user_data_dir": "pw_profile",
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions-except",
                "--disable-plugins-discovery",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ],
            "viewport": {'width': 1920, 'height': 1080},
            "java_script_enabled": True,
            "ignore_https_errors": True
        }
    
    @classmethod
    def get_context_options(cls):
        """Get context options with stealth headers"""
        return {
            "user_agent": cls.get_random_user_agent(),
            "extra_http_headers": {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        }
    
    @classmethod
    async def add_stealth_scripts(cls, page):
        """Add stealth JavaScript to avoid detection"""
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock languages and plugins
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: 'granted' }) :
                    originalQuery(parameters)
            );
            
            // Mock chrome object
            window.chrome = {
                runtime: {}
            };
        """)
    
    @classmethod
    async def human_like_delay(cls, min_delay=1.5, max_delay=3.5):
        """Add random delays to simulate human behavior"""
        await asyncio.sleep(random.uniform(min_delay, max_delay))
    
    @classmethod
    async def simulate_human_interaction(cls, page):
        """Simulate human-like interactions on the page"""
        try:
            # Random scroll to simulate reading
            await page.evaluate("window.scrollTo(0, Math.random() * 500)")
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Move mouse randomly
            await page.mouse.move(
                random.randint(100, 800), 
                random.randint(100, 600)
            )
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
        except Exception:
            pass