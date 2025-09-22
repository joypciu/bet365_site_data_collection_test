import random

class BrowserConfig:
    """Browser configuration and user agents"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random user agent string"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_browser_options(cls):
        """Get browser launch options"""
        return {
            "headless": False,
            "channel": "chrome",
            "no_viewport": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor"
            ]
        }