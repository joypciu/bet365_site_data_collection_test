# Bet365 Live Data Scraper

This project is a Python-based web scraper that collects real-time betting data from Bet365's in-play section. It uses Playwright for browser automation and Patchright for stealthy browsing to extract live match information, odds, and other betting data.

## Features

- **Real-time Data Collection**: Scrapes live match data from Bet365's in-play betting section
- **Stealth Browsing**: Uses Patchright to avoid detection and blocking
- **Multiple Data Formats**: Handles both JSON and pipe-delimited data formats from Bet365
- **Deduplication**: Prevents duplicate entries using unique match keys
- **WebSocket Support**: Captures real-time updates via WebSocket connections
- **Comprehensive Data**: Extracts match IDs, team names, leagues, times, and betting odds

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser (for Playwright)
- Internet connection

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd bet365-experiment
   ```

2. **Install Python dependencies**:
   ```bash
   pip install playwright patchright beautifulsoup4
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

4. **Install Patchright**:
   ```bash
   pip install patchright
   ```

## Usage

1. **Run the scraper**:
   ```bash
   python using_patchright\ \(works\).py
   ```

2. **Monitor the output**: The script will:
   - Launch a headless Chromium browser
   - Navigate to Bet365's in-play section
   - Start collecting real-time data
   - Save processed data to `bet365_data.json`
   - Save raw responses to `bet365_raw_data.json`

3. **Stop the script**: The script runs for approximately 30 seconds by default. You can modify the `time.sleep(30)` line to change the duration.

## Output Files

### bet365_data.json
Contains processed match data with the following structure:
```json
{
  "match_id": "unique_match_identifier",
  "home_team": "Home Team Name",
  "away_team": "Away Team Name",
  "league": "League/Competition Name",
  "match_time": "2025-09-20T15:00:00",
  "odds": {
    "OD": ["1.50", "2.00", "3.00"],
    "HA": ["1.80", "2.10"]
  },
  "timestamp": "2025-09-20T10:03:28.164968+00:00"
}
```

### bet365_raw_data.json
Contains raw API responses and intercepted data for debugging and analysis.

## Configuration

You can modify the following in the script:

- **User agents**: Update the `user_agents` list for better stealth
- **Target URL**: Change the `url` variable to scrape different sections
- **Data collection duration**: Modify `time.sleep(30)` to run longer/shorter
- **Output filenames**: Change the filenames in `save_to_json()` calls

## Important Notes

- **Legal Compliance**: Ensure you comply with Bet365's terms of service and local laws regarding web scraping
- **Rate Limiting**: The script includes delays to avoid overwhelming the server
- **Detection Avoidance**: Uses various techniques to minimize detection risk
- **Data Accuracy**: Bet365 data may have delays; this is for informational purposes only

## Troubleshooting

- **Browser launch issues**: Ensure Chrome is installed and Playwright is properly set up
- **No data collected**: Check your internet connection and Bet365's availability
- **Permission errors**: Run with appropriate permissions for file writing
- **Detection**: If blocked, try updating user agents or adding more delays

## Dependencies

- `playwright`: Browser automation
- `patchright`: Stealth browser automation
- `beautifulsoup4`: HTML parsing
- `json`: Built-in JSON handling
- `datetime`: Built-in datetime handling
- `hashlib`: Built-in hashing for deduplication
- `os`: Built-in OS operations
- `random`: Built-in randomization
- `time`: Built-in timing controls

## License

This project is for educational purposes only. Please respect website terms of service and applicable laws.