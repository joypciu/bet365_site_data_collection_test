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
    print("\nAvailable Sport Codes:")
    print("=" * 50)
    for code, sport in SPORT_CODES.items():
        print(f"{code}: {sport}")
    print(f"\nDefault sports: {', '.join(DEFAULT_SPORT_CODES)}")
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
        logger.info(f"\n=== Scraping Complete ===")
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
        print("\nStopping scraper...")
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
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
