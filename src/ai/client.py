import os
import logging
import google.genai as genai
from typing import Optional

class AIClient:
    """Google AI client for odds extraction"""
    
    def __init__(self, api_key_file: str = "api key.txt", max_calls: int = 10):
        self.client = None
        self.max_calls = max_calls
        self.call_count = 0
        self.setup_client(api_key_file)
    
    def setup_client(self, api_key_file: str):
        """Initialize the AI client with API key"""
        try:
            if not os.path.exists(api_key_file):
                logging.error(f"[!] API key file {api_key_file} not found")
                return
            
            with open(api_key_file, "r") as f:
                lines = f.readlines()
                if not lines:
                    logging.error("[!] API key file is empty")
                    return
                
                # Handle different API key file formats
                api_key = None
                for line in lines:
                    line = line.strip()
                    if '=' in line:
                        api_key = line.split('=')[1].strip()
                        break
                    elif line and not line.startswith('#'):
                        api_key = line
                        break
                
                if not api_key:
                    logging.error("[!] Could not parse API key from file")
                    return
                
            self.client = genai.Client(api_key=api_key)
            logging.info("[+] AI client initialized successfully")
            
        except Exception as e:
            logging.error(f"[!] Failed to setup AI client: {e}")
            self.client = None
    
    def test_connection(self) -> bool:
        """Test AI client connection"""
        if not self.client:
            return False
        
        try:
            prompt = "Say hello in JSON format: {\"message\": \"hello\"}"
            response = self.client.models.generate_content(
                model='gemma-3n-e2b-it',
                contents=prompt
            )
            
            if response and response.text:
                logging.info("[+] AI client test successful")
                return True
            else:
                logging.error("[!] AI client test failed - no response")
                return False
                
        except Exception as e:
            logging.error(f"[!] AI client test failed: {e}")
            return False
    
    def generate_content(self, prompt: str) -> Optional[str]:
        """Generate content using AI client with rate limiting"""
        if not self.client:
            logging.warning("[!] AI client not available")
            return None
        
        if self.call_count >= self.max_calls:
            logging.warning(f"[!] AI call limit reached ({self.max_calls})")
            return None
        
        try:
            self.call_count += 1
            response = self.client.models.generate_content(
                model='gemma-3n-e2b-it',
                contents=prompt
            )
            
            if response and response.text:
                logging.info(f"[+] AI call successful ({self.call_count}/{self.max_calls})")
                return response.text
            else:
                logging.warning("[!] AI response empty")
                return None
                
        except Exception as e:
            logging.error(f"[!] AI generation failed: {e}")
            return None
    
    def reset_call_count(self):
        """Reset the AI call counter"""
        self.call_count = 0
        logging.info("[*] AI call counter reset")
    
    def get_remaining_calls(self) -> int:
        """Get remaining AI calls"""
        return max(0, self.max_calls - self.call_count)
    
    def is_available(self) -> bool:
        """Check if AI client is available and has calls remaining"""
        return self.client is not None and self.call_count < self.max_calls