# Bet365 Live Data Scraper

This project is a Python-based web scraper that collects real-time betting data from Bet365. It uses Playwright for browser automation to extract live match information, odds, and other betting data across multiple sports including NFL, Soccer, Basketball, Baseball, and more.

## Features

- **Real-time Data Collection**: Scrapes live and pre-match data from Bet365 across multiple sports
- **AI-Enhanced Extraction**: Uses Google Gemini AI to extract complex odds data from HTML
- **Multi-Sport Support**: Covers NFL, Soccer, Basketball, Baseball, Tennis, Hockey, and more
- **Comprehensive Odds**: Extracts moneyline, spread, and total (over/under) odds
- **Deduplication**: Prevents duplicate entries using unique match identifiers
- **Auto-Config Generation**: Automatically generates browser configuration and cookies
- **Persistent Browser**: Uses saved browser profile for session continuity

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser (for Playwright)
- Google Gemini API key (for AI-enhanced odds extraction)
- Internet connection

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd bet365_site_data_collection_test-main
   ```

2. **Install Python dependencies**:
   ```bash
   pip install playwright google-genai
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

4. **Set up Google Gemini API**:
   - Create an `api key.txt` file in the project root
   - Add your Google Gemini API key in the format: `API_KEY=your_api_key_here`

## Usage

1. **Run the main scraper**:
   ```bash
   python scrape.py
   ```

2. **Monitor the output**: The script will:
   - Launch a Chrome browser with persistent profile
   - Navigate to Bet365's various sports sections (live and pre-match)
   - Extract match data using both HTML parsing and AI assistance
   - Save processed data to `bet365_data.json`
   - Generate detailed logs in `bet365_scraper.log`

3. **Configuration**: The script automatically generates `config.json` with browser headers and cookies on first run.

4. **Duration**: The script runs for 15 seconds by default for testing. Modify `max_runtime` in the code to change duration.

## Output Files

### bet365_data.json
Contains processed match data with the following structure:
```json
{
  "match_id": "american_football_gb_packers_cle_browns_unknown",
  "home_team": "GB Packers",
  "away_team": "CLE Browns",
  "league": "American Football",
  "match_time": "14:30",
  "odds": {
    "money_home": "-150",
    "money_away": "+130",
    "spread_home": "-7.5",
    "spread_home_odds": "-110",
    "spread_away": "+7.5",
    "spread_away_odds": "-110",
    "total_over": "45.5",
    "total_over_odds": "-110",
    "total_under": "45.5",
    "total_under_odds": "-110"
  },
  "type": "prematch",
  "timestamp": "2025-09-21T16:09:50.215000+00:00"
}
```

### bet365_scraper.log
Contains detailed logging information including:
- Navigation attempts and successes
- Data extraction results
- Error messages and debugging information
- AI API call results

### config.json
Auto-generated configuration file containing:
- Browser headers for requests
- Session cookies for maintaining access

## Configuration

You can modify the following in `scrape.py`:

- **Sports Coverage**: Update `key_paths` list to add/remove sports sections
- **AI Usage**: Modify `MAX_AI_CALLS` to control Google Gemini API usage
- **Runtime**: Change `max_runtime` variable for longer/shorter execution
- **Base URL**: Update `BASE_URL` for different Bet365 regions
- **User Agents**: Modify `user_agents` list for variety
- **Refresh Interval**: Change `REFRESH_INTERVAL` for periodic data updates

## Sport Codes

The scraper covers these sports with their Bet365 codes:
- **B1**: Soccer
- **B2**: Basketball  
- **B3**: Cricket
- **B4**: Tennis
- **B5**: Golf
- **B6**: Ice Hockey
- **B7**: Snooker
- **B8**: American Football
- **B9**: Baseball
- **B13**: NFL
- **#HO**: Home page
- **#IP**: In-Play (live matches)
- **#AS**: All Sports (pre-match)

## Important Notes

- **Legal Compliance**: Ensure you comply with Bet365's terms of service and local laws regarding web scraping
- **Rate Limiting**: The script includes delays and rotation to avoid overwhelming servers
- **API Costs**: Google Gemini API calls are limited to avoid excessive costs
- **Data Accuracy**: Betting odds change rapidly; this is for informational purposes only
- **Browser Profile**: Uses persistent browser profile stored in `pw_profile/` directory

## Troubleshooting

- **JavaScript Errors**: Check `bet365_scraper.log` for page.evaluate syntax errors
- **No data collected**: Verify internet connection and Bet365 accessibility
- **AI API Errors**: Check your Google Gemini API key in `api key.txt`
- **Browser issues**: Delete `pw_profile/` directory to reset browser state
- **Config errors**: Delete `config.json` to regenerate browser configuration
- **Permission errors**: Ensure write permissions for output files

## Dependencies

- `playwright`: Browser automation framework
- `google-genai`: Google Gemini AI API client for advanced data extraction
- `asyncio`: Built-in asynchronous programming support
- `json`: Built-in JSON handling
- `datetime`: Built-in datetime handling
- `logging`: Built-in logging functionality
- `os`: Built-in OS operations
- `random`: Built-in randomization
- `time`: Built-in timing controls
- `re`: Built-in regular expressions

## Files Structure

```
bet365_site_data_collection_test-main/
├── scrape.py                 # Main scraper script
├── api key.txt              # Google Gemini API key
├── config.json              # Auto-generated browser config
├── bet365_data.json         # Output data file
├── bet365_scraper.log       # Detailed logs
├── README.md                # This file
└── pw_profile/              # Persistent browser profile directory
```

## License

This project is for educational purposes only. Please respect website terms of service and applicable laws.