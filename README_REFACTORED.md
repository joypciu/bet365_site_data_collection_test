# Bet365 Odds Scraper - Refactored

A modular, maintainable web scraper for bet365 odds data with AI-powered extraction capabilities.

## Features

- **Modular Architecture**: Clean separation of concerns across config, models, parsers, AI, and utilities
- **Multi-Sport Support**: Covers 22+ sports including NFL, NBA, MLB, Soccer, Tennis, etc.
- **Dual Market Coverage**: Both pre-match and in-play odds
- **AI-Powered Extraction**: Google Gemini integration for complex odds parsing
- **Robust Error Handling**: Comprehensive logging and retry mechanisms
- **Persistent Browser Context**: Maintains login state across sessions
- **API Discovery**: Intercepts and processes bet365 API responses
- **Rate Limiting**: Configurable AI usage limits and request delays

## Project Structure

```
src/
├── config/
│   ├── settings.py          # Configuration management
│   └── browser_config.py    # Browser settings and user agents
├── models/
│   ├── match.py            # Match data model
│   └── odds.py             # Odds data model with conversion utilities
├── parsers/
│   ├── odds_parser.py      # Regex-based odds extraction
│   └── html_parser.py      # HTML content parsing
├── ai/
│   ├── client.py           # Google AI client wrapper
│   └── extractor.py        # AI-powered odds extraction
├── utils/
│   ├── logger.py           # Enhanced logging utilities
│   ├── helpers.py          # Common helper functions
│   └── constants.py        # Sport codes, selectors, and configurations
└── scraper/
    └── bet365_scraper.py   # Main scraper orchestration
```

## Installation

1. **Clone/Download** the project
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Setup API key**: Create `api key.txt` with your Google AI API key:
   ```
   API_KEY=your_google_ai_api_key_here
   ```

## Usage

### Basic Usage
```bash
# Run continuous scraping (default sports)
python main.py

# Single run with specific sports
python main.py --sports B1,B8,B13 --single-run

# Custom refresh interval
python main.py --interval 60

# Skip in-play markets
python main.py --no-inplay
```

### Command Line Options
- `--sports`: Sport codes (e.g., B1,B2,B8) - see `--list-sports` for available codes
- `--interval`: Refresh interval in seconds (default: 30)
- `--single-run`: Run once instead of continuous loop
- `--no-inplay`: Skip in-play markets, only scrape pre-match
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--list-sports`: Show available sport codes

### Available Sports
| Code | Sport |
|------|-------|
| B1 | Soccer |
| B2 | Basketball |
| B8 | American Football |
| B9 | Baseball |
| B13 | NFL |
| ... | (22 total sports) |

## Configuration

### Settings (`src/config/settings.py`)
- Browser configuration and cookie management
- Output file paths and data persistence
- AI API integration settings

### Constants (`src/utils/constants.py`)
- Sport codes and league mappings
- CSS selectors for scraping
- Default configuration values

## Features Breakdown

### 1. Data Models
- **Match**: Structured match representation with teams, league, sport, timestamps
- **Odds**: Comprehensive odds model supporting spread, total, moneyline markets
- **Type Safety**: Dataclass-based models with validation

### 2. Parsing Engine
- **Multi-Strategy**: DOM parsing → Regex extraction → AI fallback
- **Odds Normalization**: American/Decimal odds conversion utilities
- **League Detection**: Intelligent league inference from team names

### 3. AI Integration
- **Rate Limited**: Configurable API call limits
- **Robust Parsing**: JSON sanitization and error recovery
- **Fallback Extraction**: Regex-based fallback when AI parsing fails

### 4. Browser Automation
- **Persistent Context**: Maintains cookies and session state
- **Request Interception**: Captures API responses for data extraction
- **Anti-Detection**: Random user agents and delays

### 5. Error Handling & Logging
- **Structured Logging**: Contextual logging with prefixes and timestamps
- **Retry Logic**: Exponential backoff for failed operations
- **Graceful Degradation**: Continues operation when individual components fail

## Output

Data is saved to `bet365_data.json` with structure:
```json
{
  "match_id": {
    "home_team": "Team A",
    "away_team": "Team B", 
    "league": "NFL",
    "sport": "American Football",
    "odds": {
      "spread_home": "-7.5",
      "spread_home_odds": "-110",
      "total_over": "47.5",
      "total_over_odds": "-105"
    },
    "timestamp": "2025-09-21T10:30:00Z"
  }
}
```

## Monitoring & Statistics

The scraper provides real-time statistics:
- Total matches scraped
- API URLs discovered
- AI calls used/remaining
- Runtime and performance metrics

## Error Recovery

- **Configuration Issues**: Auto-regenerates browser config if corrupted
- **Navigation Failures**: Retry logic with exponential backoff
- **AI Service Outages**: Falls back to regex-based parsing
- **Rate Limiting**: Respects API limits and continues with available methods

## Development

### Testing
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Adding New Sports
1. Add sport code to `SPORT_CODES` in `constants.py`
2. Add team patterns to `LEAGUE_PATTERNS` if needed
3. Test with `--sports NEW_CODE --single-run`

## Improvements Over Original

1. **Modularity**: Single 400+ line file → 9 focused modules
2. **Testability**: Separated concerns enable unit testing
3. **Maintainability**: Clear interfaces and documentation
4. **Extensibility**: Easy to add new sports, parsers, or AI providers
5. **Error Handling**: Comprehensive error recovery and logging
6. **Performance**: Concurrent operations and intelligent caching
7. **Configuration**: Externalized settings and environment support

## Troubleshooting

### Common Issues
1. **Browser Launch Fails**: Ensure Chrome/Chromium is installed
2. **AI Extraction Fails**: Check API key in `api key.txt`
3. **No Data Found**: Verify sport codes with `--list-sports`
4. **Rate Limiting**: Increase `--interval` or reduce `max_ai_calls`

### Debug Mode
```bash
python main.py --log-level DEBUG --single-run
```

This provides detailed logging for troubleshooting parsing and extraction issues.

## License

This project is for educational and research purposes. Please respect bet365's terms of service and robots.txt when using this scraper.