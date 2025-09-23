# Sport codes mapping
SPORT_CODES = {
    'B1': 'Soccer',
    'B2': 'Basketball', 
    'B3': 'Cricket',
    'B4': 'Tennis',
    'B5': 'Golf',
    'B6': 'Ice Hockey',
    'B7': 'Snooker',
    'B8': 'American Football',
    'B9': 'Baseball',
    'B10': 'Handball',
    'B11': 'Volleyball',
    'B12': 'Rugby',
    'B13': 'Tennis',  # Live tennis
    'B14': 'Boxing',
    'B15': 'Darts',   # Live darts
    'B16': 'Baseball',  # Live baseball
    'B17': 'Cycling',
    'B18': 'Basketball',  # Live basketball
    'B19': 'Bowls',
    'B20': 'Badminton',
    'B21': 'Squash',
    'B22': 'Table Tennis',
    'B91': 'Volleyball',  # Live volleyball
    'B92': 'Table Tennis', # Live table tennis
    'B151': 'Esports',     # Live esports
}

# Mapping from prematch sport codes to live sport codes
PREMATCH_TO_LIVE_MAPPING = {
    'B1': 'B1',   # Soccer/Football -> Live Soccer
    'B2': 'B18',  # Basketball -> Live Basketball
    'B3': 'B3',   # Cricket -> Live Cricket
    'B4': 'B13',  # Tennis -> Live Tennis
    'B5': 'B5',   # Golf -> Live Golf (assuming same)
    'B6': 'B6',   # Ice Hockey -> Live Ice Hockey (assuming same)
    'B7': 'B7',   # Snooker -> Live Snooker (assuming same)
    'B8': 'B8',   # American Football -> Live American Football (assuming same)
    'B9': 'B16',  # Baseball -> Live Baseball
    'B13': 'B13', # Tennis -> Live Tennis
    'B15': 'B15', # Darts -> Live Darts
    'B22': 'B92', # Table Tennis -> Live Table Tennis
    'B11': 'B91', # Volleyball -> Live Volleyball
    'B151': 'B151', # Esports -> Live Esports
}

# Special live URLs
LIVE_STREAMING_URL = "https://www.co.bet365.com/#/IP/STREAMING"
LIVE_SCHEDULE_URL = "https://www.co.bet365.com/#/IP/SCHEDULE"

# Default sport codes to scrape - comprehensive list including live-specific sports
DEFAULT_SPORT_CODES = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B13', 'B15', 'B22', 'B11', 'B151']

# Market types
MARKET_TYPES = {
    'AS': 'Pre-match',
    'IP': 'In-play'
}

# Default configuration values
DEFAULT_CONFIG = {
    'refresh_interval': 30,
    'max_ai_calls': 10,
    'base_url': 'https://www.co.bet365.com/#/HO/',
    'config_file': 'config.json',
    'output_file': 'bet365_data.json',
    'log_file': 'bet365_scraper.log',
    'api_key_file': 'api key.txt'
}

# CSS selectors for scraping
SELECTORS = {
    'match_containers': [
        '.gl-MarketGroup',
        '.cpm-ParticipantOdds', 
        '.ovm-ParticipantStackedCentered',
        '[aria-label*="@"]',
        '[aria-label*=" v "]'
    ],
    'odds_elements': [
        '.cpm-ParticipantOdds_Odds',
        '.gl-ParticipantOdds_Odds',
        '.ovm-ParticipantOdds_Odds'
    ],
    'team_elements': [
        '.cpm-ParticipantFixtureDetails_TeamNames',
        '.cpm-ParticipantFixtureDetails_TeamName',
        '.gl-ParticipantFixtureDetails_TeamNames'
    ]
}

# Retry configuration
RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 1.0,
    'backoff_factor': 2.0,
    'max_delay': 30.0
}

# Browser configuration
BROWSER_CONFIG = {
    'user_data_dir': 'pw_profile',
    'timeout': 60000,
    'wait_for': 'networkidle',
    'headless': False
}

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36", 
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# League detection patterns
LEAGUE_PATTERNS = {
    'NFL': [
        'bengals', 'vikings', 'patriots', 'raiders', 'browns', 'jets', 'colts',
        'titans', 'falcons', 'panthers', 'texans', 'jaguars', 'broncos',
        'chargers', 'saints', 'seahawks', 'cowboys', 'bears', 'cardinals',
        '49ers', 'chiefs', 'giants', 'lions', 'ravens', 'steelers', 'eagles',
        'bills', 'dolphins', 'packers', 'rams', 'buccaneers'
    ],
    'MLB': [
        'yankees', 'orioles', 'athletics', 'pirates', 'braves', 'tigers',
        'nationals', 'mets', 'cubs', 'reds', 'blue jays', 'royals',
        'guardians', 'twins', 'padres', 'white sox', 'brewers', 'cardinals',
        'marlins', 'rangers', 'angels', 'rockies', 'dodgers', 'phillies',
        'mariners', 'astros', 'red sox', 'rays'
    ],
    'NBA': [
        'lakers', 'warriors', 'celtics', 'heat', 'bulls', 'knicks', 'nets',
        'sixers', 'raptors', 'bucks', 'cavaliers', 'pistons', 'pacers',
        'hawks', 'hornets', 'magic', 'wizards', 'rockets', 'mavericks',
        'spurs', 'grizzlies', 'pelicans', 'thunder', 'nuggets', 'jazz',
        'suns', 'kings', 'clippers', 'blazers', 'timberwolves'
    ],
    'Premier League': [
        'arsenal', 'chelsea', 'liverpool', 'manchester united', 'manchester city',
        'tottenham', 'leicester', 'west ham', 'everton', 'wolves',
        'crystal palace', 'brighton', 'southampton', 'burnley', 'newcastle',
        'leeds', 'aston villa', 'fulham', 'brentford', 'nottingham forest'
    ]
}

# API endpoints patterns
API_PATTERNS = [
    'config/api',
    'prematch/api',
    'inplay/api',
    'sports/api'
]

# Error messages
ERROR_MESSAGES = {
    'config_load_failed': 'Failed to load configuration',
    'browser_init_failed': 'Failed to initialize browser',
    'navigation_failed': 'Navigation to URL failed',
    'odds_extraction_failed': 'Failed to extract odds data',
    'ai_unavailable': 'AI service is not available',
    'api_limit_reached': 'API call limit reached',
    'invalid_response': 'Invalid response received',
    'timeout_error': 'Operation timed out'
}

# Success messages
SUCCESS_MESSAGES = {
    'config_loaded': 'Configuration loaded successfully',
    'browser_initialized': 'Browser initialized successfully',
    'navigation_success': 'Navigation completed successfully',
    'odds_extracted': 'Odds data extracted successfully',
    'data_saved': 'Data saved successfully',
    'ai_extraction_success': 'AI extraction completed successfully'
}