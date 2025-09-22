import logging
import sys
from datetime import datetime

class Logger:
    """Custom logger configuration for bet365 scraper"""
    
    @staticmethod
    def setup_logger(name: str = "bet365_scraper", log_file: str = "bet365_scraper.log", 
                    level: int = logging.INFO) -> logging.Logger:
        """Setup and configure logger"""
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers to prevent duplicates
        logger.handlers.clear()
        
        # Prevent propagation to avoid duplicate messages
        logger.propagate = False
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def log_with_prefix(logger: logging.Logger, level: int, prefix: str, message: str):
        """Log message with custom prefix"""
        formatted_message = f"[{prefix}] {message}"
        logger.log(level, formatted_message)
    
    @staticmethod
    def log_match_info(logger: logging.Logger, match_count: int, source: str = ""):
        """Log match extraction information"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"Extracted {match_count} matches"
        if source:
            message += f" from {source}"
        message += f" at {timestamp}"
        logger.info(f"[MATCHES] {message}")
    
    @staticmethod
    def log_odds_info(logger: logging.Logger, odds_type: str, success: bool, details: str = ""):
        """Log odds extraction information"""
        status = "SUCCESS" if success else "FAILED"
        message = f"{odds_type} extraction {status}"
        if details:
            message += f" - {details}"
        logger.info(f"[ODDS] {message}")
    
    @staticmethod
    def log_error_with_context(logger: logging.Logger, error: Exception, context: str = ""):
        """Log error with additional context"""
        error_message = f"Error: {str(error)}"
        if context:
            error_message = f"{context} - {error_message}"
        logger.error(f"[ERROR] {error_message}")
    
    @staticmethod
    def log_api_call(logger: logging.Logger, call_count: int, max_calls: int, success: bool = True):
        """Log API call information"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"[AI] API call {status} ({call_count}/{max_calls})")
    
    @staticmethod
    def log_navigation(logger: logging.Logger, url: str, success: bool = True, retry_count: int = 0):
        """Log navigation attempts"""
        status = "SUCCESS" if success else "FAILED"
        message = f"Navigation to {url} {status}"
        if retry_count > 0:
            message += f" (retry #{retry_count})"
        logger.info(f"[NAV] {message}")
    
    @staticmethod
    def log_data_save(logger: logging.Logger, filename: str, record_count: int):
        """Log data saving information"""
        logger.info(f"[SAVE] Saved {record_count} records to {filename}")
    
    @staticmethod
    def log_config_load(logger: logging.Logger, config_file: str, success: bool = True):
        """Log configuration loading"""
        status = "loaded" if success else "failed to load"
        logger.info(f"[CONFIG] Configuration {status} from {config_file}")
    
    @staticmethod
    def get_default_logger() -> logging.Logger:
        """Get default configured logger"""
        return Logger.setup_logger()