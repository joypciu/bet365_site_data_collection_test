import asyncio
import random
import time
import hashlib
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

class RetryHelper:
    """Helper for retry logic with exponential backoff"""
    
    @staticmethod
    async def retry_async(func, max_retries: int = 3, delay: float = 1.0, 
                         backoff_factor: float = 2.0, *args, **kwargs):
        """Retry an async function with exponential backoff"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = delay * (backoff_factor ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                break
        
        # If all retries failed, raise the last exception
        if last_exception:
            raise last_exception

class DataHelper:
    """Helper functions for data manipulation"""
    
    @staticmethod
    def generate_match_id(home_team: str, away_team: str, league: str, 
                         match_time: str = "unknown") -> str:
        """Generate consistent match ID from team data"""
        data_string = f"{league}_{home_team}_{away_team}_{match_time}"
        normalized = data_string.replace(' ', '_').lower()
        # Add hash to ensure uniqueness while keeping readability
        hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"{normalized}_{hash_suffix}"
    
    @staticmethod
    def normalize_team_name(team_name: str) -> str:
        """Normalize team name for consistent matching"""
        if not team_name:
            return ""
        
        # Remove common prefixes/suffixes
        normalized = team_name.strip()
        
        # Remove trailing city/state abbreviations in parentheses
        if '(' in normalized and ')' in normalized:
            normalized = normalized.split('(')[0].strip()
        
        # Replace multiple spaces with single space
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    @staticmethod
    def merge_odds_data(existing: Dict, new_data: Dict) -> Dict:
        """Merge odds data, keeping non-None values"""
        merged = existing.copy()
        
        for key, value in new_data.items():
            if value is not None and value != "":
                merged[key] = value
        
        return merged
    
    @staticmethod
    def remove_duplicates_by_key(items: List[Dict], key: str) -> List[Dict]:
        """Remove duplicates from list of dictionaries by key"""
        seen = set()
        unique_items = []
        
        for item in items:
            if isinstance(item, dict) and key in item:
                identifier = item[key]
                if identifier not in seen:
                    seen.add(identifier)
                    unique_items.append(item)
            else:
                unique_items.append(item)
        
        return unique_items

class URLHelper:
    """Helper functions for URL manipulation"""
    
    @staticmethod
    def extract_sport_code(url: str) -> str:
        """Extract sport code from bet365 URL"""
        sport_codes = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10',
                      'B11', 'B12', 'B13', 'B14', 'B15', 'B16', 'B17', 'B18', 'B19', 'B20',
                      'B21', 'B22']
        
        for code in sport_codes:
            if code in url:
                return code
        return "Unknown"
    
    @staticmethod
    def build_bet365_url(base_url: str, sport_code: str, market_type: str = "AS") -> str:
        """Build bet365 URL for specific sport and market"""
        return f"{base_url}#{market_type}/{sport_code}"
    
    @staticmethod
    def extract_query_params(url: str) -> Dict[str, str]:
        """Extract query parameters from URL"""
        parsed_url = urlparse(url)
        return {k: v[0] if v else "" for k, v in parse_qs(parsed_url.query).items()}

class DelayHelper:
    """Helper for adding delays and randomization"""
    
    @staticmethod
    async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay between min and max seconds"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def progressive_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0):
        """Progressive delay that increases with attempt number"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        await asyncio.sleep(delay)
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get a random user agent string"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
        ]
        return random.choice(user_agents)

class TextHelper:
    """Helper functions for text processing"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        cleaned = ' '.join(text.split())
        
        # Remove special characters that might cause issues
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        return cleaned.strip()
    
    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """Extract all numbers from text"""
        import re
        return re.findall(r'[+-]?\d+(?:\.\d+)?', text)
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

class TimeHelper:
    """Helper functions for time operations"""
    
    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def get_formatted_time() -> str:
        """Get formatted current time for logging"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def time_since(start_time: float) -> str:
        """Get formatted time elapsed since start_time"""
        elapsed = time.time() - start_time
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        elif elapsed < 3600:
            return f"{elapsed/60:.1f}m"
        else:
            return f"{elapsed/3600:.1f}h"