"""
Dynamic team and sport detection utilities
"""

import re
import logging
from typing import Dict, Set, List, Optional, Tuple
from datetime import datetime, timedelta
from .constants import SPORT_CODES

class DynamicSportDetector:
    """Dynamically detect sports and teams from scraped data"""
    
    def __init__(self):
        self.discovered_teams: Dict[str, Set[str]] = {}  # sport -> set of teams
        self.team_patterns: Dict[str, List[str]] = {}    # sport -> regex patterns
        self.sport_keywords: Dict[str, List[str]] = {
            'American Football': ['nfl', 'football', 'touchdown', 'yard', 'quarterback', 'patriots', 'cowboys', 'chiefs', 'lions', 'ravens'],
            'Basketball': ['nba', 'basketball', 'points', 'lakers', 'warriors', 'celtics', 'heat', 'bucks', 'bulls', 'grizzlies', 'cavaliers', 'knicks', 'nets', 'raptors', 'jazz', 'thunder', 'clippers', 'kings', 'suns', 'mavericks', 'spurs', 'rockets', 'pelicans', 'timberwolves', 'pistons', 'hornets', 'wizards', 'hawks', 'magic', 'pacers', 'sixers'],
            'Baseball': ['mlb', 'baseball', 'inning', 'yankees', 'dodgers', 'red sox', 'astros', 'braves', 'brewers', 'padres', 'cardinals', 'giants', 'mets', 'phillies', 'lotte marines', 'nippon', 'hanshin', 'yomiuri', 'yakult'],
            'Soccer': ['premier league', 'fifa', 'goal', 'arsenal', 'chelsea', 'liverpool', 'barcelona', 'manchester', 'tottenham', 'bayern', 'real madrid', 'juventus', 'ac milan', 'inter milan', 'napoli', 'roma', 'psg', 'lyon', 'marseille', 'monaco', 'dortmund', 'leverkusen', 'rb leipzig', 'champions league', 'europa league', 'conference league', 'ucl', 'uel', 'uecl', 'aston villa', 'wolverhampton'],
            'Hockey': ['nhl', 'hockey', 'puck', 'rangers', 'bruins', 'blackhawks', 'penguins', 'kings'],
            'Ice Hockey': ['nhl', 'hockey', 'ice hockey', 'puck', 'goal', 'assist', 'rangers', 'bruins', 'blackhawks', 'penguins', 'kings', 'capitals', 'devils', 'islanders', 'flyers', 'avalanche', 'blues', 'predators', 'lightning', 'panthers', 'hurricanes', 'maple leafs', 'senators', 'sabres', 'red wings', 'blue jackets'],
            'Golf': ['golf', 'pga', 'tour', 'major', 'masters', 'open', 'championship', 'birdie', 'eagle', 'par', 'hole', 'round', 'course', 'driver', 'iron', 'putter', 'woods', 'mcilroy', 'rahm', 'schauffele', 'koepka', 'dechambeau', 'cantlay', 'morikawa', 'thomas', 'spieth', 'johnson', 'fowler', 'mickelson'],
            'Snooker': ['snooker', 'frame', 'century', 'break', 'pot', 'cue', 'table', 'world championship', 'masters', 'uk championship', 'ranking', 'trump', 'selby', 'robertson', 'higgins', 'williams', 'murphy', 'wilson', 'lisowski', 'allen', 'ding', 'zhao', 'yan', 'brecel', 'gilbert', 'milkins', 'carter', 'bingham', 'hawkins'],
            'Tennis': ['atp', 'wta', 'tennis', 'set', 'match', 'djokovic', 'nadal', 'federer', 'bublik', 'wu', 'alcaraz', 'sinner', 'medvedev', 'rublev', 'tsitsipas', 'berrettini', 'zverev', 'humbert', 'ruud', 'musetti', 'bellucci', 'uchiyama', 'kovacevic', 'vukic', 'cerundolo', 'noguchi', 'sakamoto', 'walton', 'jacquemot', 'aiava', 'shimabukuro', 'navone', 'timofeeva', 'minnen', 'gracheva', 'tararudee', 'bucsa', 'ngounoue', 'sakkari', 'sabalenka', 'swiatek', 'jabeur', 'pegula', 'gaud', 'murray', 'djokovic', 'nadal', 'federer', 'wawrinka', 'del potro', 'cilic', 'thiem', 'zverev', 'berrettini', 'sinner', 'alcaraz', 'medvedev', 'rublev', 'tsitsipas', 'ruud', 'humbert', 'musetti', 'fognini', 'seppi', 'lorenzi', 'travaglia', 'caruso', 'sonego', 'mager', 'cecchinato', 'giustino', 'marcora', 'bellucci', 'gaio', 'giannessi', 'brugnoli', 'napolitano', 'passaro', 'taberner', 'munar', 'davidovich', 'alcaraz', 'bautista', 'carreno', 'diaz', 'etcheverry', 'galan', 'londero', 'mayer', 'molinero', 'navone', 'pella', 'schwartzman', 'tirante', 'varillas', 'zeballos'],
        }
        self.confidence_scores: Dict[str, float] = {}
        
        # Comprehensive team databases for accurate sport detection
        self.soccer_teams = {
            'manchester united', 'manchester city', 'chelsea', 'arsenal', 'liverpool',
            'tottenham', 'aston villa', 'wolverhampton wanderers', 'wolverhampton', 'everton',
            'newcastle', 'west ham', 'brighton', 'crystal palace', 'fulham',
            'bournemouth', 'nottingham forest', 'brentford', 'luton', 'burnley',
            'barcelona', 'real madrid', 'atletico madrid', 'valencia', 'sevilla',
            'bayern munich', 'dortmund', 'leverkusen', 'rb leipzig', 'juventus',
            'ac milan', 'inter milan', 'napoli', 'roma', 'lazio', 'psg', 'lyon',
            'marseille', 'monaco'
        }
        
        self.baseball_teams = {
            'lotte marines', 'nippon', 'hanshin tigers', 'yomiuri giants',
            'yakult swallows', 'chunichi dragons', 'hiroshima toyo carp',
            'yokohama dena baystars', 'hokkaido nippon-ham fighters',
            'chiba lotte marines', 'saitama seibu lions', 'tohoku rakuten eagles',
            'orix buffaloes', 'fukuoka softbank hawks', 'yankees', 'dodgers',
            'red sox', 'astros', 'braves', 'brewers', 'padres', 'cardinals',
            'giants', 'mets', 'phillies', 'nationals', 'cubs', 'reds',
            'pirates', 'marlins', 'rockies', 'diamondbacks', 'rangers',
            'athletics', 'mariners', 'angels', 'orioles', 'rays', 'blue jays',
            'white sox', 'guardians', 'tigers', 'twins', 'royals'
        }
        
        self.basketball_teams = {
            'lakers', 'warriors', 'celtics', 'heat', 'bulls', 'knicks', 
            'grizzlies', 'cavaliers', 'nets', 'raptors', 'jazz', 'thunder',
            'clippers', 'kings', 'suns', 'mavericks', 'spurs', 'rockets',
            'pelicans', 'timberwolves', 'pistons', 'hornets', 'wizards',
            'hawks', 'magic', 'pacers', 'sixers', 'nuggets', 'trail blazers',
            'bucks',
            # WNBA teams
            'mercury', 'lynx', 'storm', 'aces', 'sun', 'wings', 'fever', 
            'sparks', 'sky', 'mystics', 'liberty', 'dream'
        }
        
        self.ice_hockey_teams = {
            'rangers', 'bruins', 'blackhawks', 'penguins', 'kings', 'capitals',
            'devils', 'islanders', 'flyers', 'avalanche', 'blues', 'predators',
            'lightning', 'panthers', 'hurricanes', 'maple leafs', 'senators',
            'sabres', 'red wings', 'blue jackets', 'wild', 'stars', 'flames',
            'oilers', 'canucks', 'kraken', 'golden knights', 'ducks', 'sharks',
            'jets', 'canadiens', 'coyotes'
        }
        
        self.golf_players = {
            'woods', 'mcilroy', 'rahm', 'schauffele', 'koepka', 'dechambeau',
            'cantlay', 'morikawa', 'thomas', 'spieth', 'johnson', 'fowler',
            'mickelson', 'watson', 'garcia', 'rose', 'casey', 'poulter',
            'westwood', 'fleetwood', 'fitzpatrick', 'hovland', 'matsuyama',
            'na', 'kim', 'lee', 'park', 'choi', 'im', 'finau', 'reed',
            'simpson', 'kuchar', 'berger', 'english', 'horschel', 'mitchell',
            'zalatoris', 'young', 'palmer', 'nicklaus', 'player', 'trevino',
            'norman', 'faldo', 'ballesteros', 'langer', 'montgomerie'
        }
        
        self.snooker_players = {
            'trump', 'selby', 'robertson', 'higgins', 'williams', 'murphy',
            'wilson', 'lisowski', 'allen', 'ding', 'zhao', 'yan', 'brecel',
            'gilbert', 'milkins', 'carter', 'bingham', 'hawkins', 'perry',
            'maguire', 'stevens', 'ford', 'mcgill', 'grace', 'burns',
            'hossein', 'jones', 'white', 'wakelin', 'brown', 'joyce',
            'clarke', 'dunham', 'lines', 'day', 'selt', 'donaldson',
            'craig', 'mann', 'dunn', 'davis', 'hendry', 'parrott',
            'white', 'thorne', 'virgo', 'foulds'
        }
        
        self.american_football_teams = {
            'lions', 'ravens', 'cowboys', 'patriots', 'chiefs', 'bills',
            'browns', 'steelers', 'bengals', 'titans', 'colts', 'jaguars',
            'texans', 'broncos', 'chargers', 'raiders', 'rams', 'seahawks',
            '49ers', 'cardinals', 'bears', 'packers', 'vikings', 'eagles',
            'commanders', 'giants', 'falcons', 'panthers', 'saints', 'bucs',
            'dolphins', 'jets'
        }
        
        # Tennis gender detection
        self.womens_tennis_players = {
            'maria', 'timofeeva', 'greet', 'minnen', 'varvara', 'gracheva', 
            'lanlana', 'tararudee', 'cristina', 'bucsa', 'clervie', 'ngounoue',
            'leolia', 'jeanjean', 'lepchenko', 'storm', 'hunter', 'katarzyna', 
            'kawa', 'viktoriya', 'tomova', 'whitney', 'osuigwe', 'yufei', 'ren',
            'lourdes', 'carle', 'sabalenka', 'swiatek', 'jabeur', 'pegula',
            'sakkari', 'azarenka', 'collins', 'garcia', 'halep', 'raducanu',
            'pliskova', 'kvitova', 'muguruza', 'osaka', 'kenin', 'andreescu',
            'keys', 'mertens', 'vekic', 'putintseva', 'kontaveit', 'krejcikova',
            'muchova', 'ostapenko', 'rybakina', 'badosa', 'fernandez', 'gauff'
        }
        
        self.mens_tennis_players = {
            'aleksandar', 'kovacevic', 'vukic', 'rei', 'sakamoto', 'adam', 
            'walton', 'sho', 'shimabukuro', 'mariano', 'navone', 'brandon',
            'nakashima', 'alejandro', 'valentin', 'royer', 'corentin',
            'lorenzo', 'musetti', 'alexander', 'bublik', 'yibing',
            'djokovic', 'nadal', 'federer', 'medvedev', 'alcaraz', 'sinner',
            'rublev', 'tsitsipas', 'berrettini', 'zverev', 'humbert', 'ruud',
            'fognini', 'seppi', 'lorenzi', 'travaglia', 'caruso', 'sonego',
            'mager', 'cecchinato', 'giustino', 'marcora', 'bellucci', 'gaio',
            'giannessi', 'brugnoli', 'napolitano', 'passaro'
        }
        
    def detect_sport_from_context(self, text: str, url: str = "", teams: Optional[List[str]] = None) -> str:
        """Detect sport from context with confidence scoring"""
        text_lower = text.lower()
        scores = {}
        
        # Priority-based team detection with better matching
        if teams:
            team_matches = {}
            
            # Collect all potential matches with sport confidence
            for team_name in teams:
                team_lower = team_name.lower()
                
                # Check each sport database
                for sport, team_list in [
                    ('Soccer', self.soccer_teams),
                    ('American Football', self.american_football_teams),  # Check NFL before baseball
                    ('Basketball', self.basketball_teams),
                    ('Baseball', self.baseball_teams),
                    ('Ice Hockey', self.ice_hockey_teams),
                    ('Golf', self.golf_players),
                    ('Snooker', self.snooker_players)
                ]:
                    for db_team in team_list:
                        # More specific matching - check if team name contains the database team
                        # or if database team is a significant part of team name
                        if (db_team.lower() in team_lower and len(db_team) >= 3) or \
                           (team_lower in db_team.lower() and len(team_lower) >= 3):
                            # Score based on match specificity and team database priority
                            score = len(db_team) * (4 if sport == 'Soccer' else 3 if sport == 'American Football' else 2)
                            if sport not in team_matches or team_matches[sport] < score:
                                team_matches[sport] = score
            
            # Return the highest scoring sport
            if team_matches:
                best_sport = max(team_matches.items(), key=lambda x: x[1])[0]
                return best_sport
        
        # Special case: Detect tennis by player name patterns
        # Tennis players typically have first name + last name format
        if teams:
            tennis_indicators = 0
            college_indicators = 0
            
            for team in teams:
                words = team.strip().split()
                
                # Check for college indicators
                college_terms = ['state', 'university', 'college', 'tech', 'dame', 'texas', 'florida', 'georgia', 'virginia', 'north', 'south', 'west', 'east']
                if any(term.lower() in team.lower() for term in college_terms):
                    college_indicators += 3
                
                # Check for typical tennis player names (first + last name, usually shorter)
                if len(words) == 2 and all(word and word[0].isupper() and 3 <= len(word) <= 12 for word in words):
                    # Two words, both capitalized, reasonable name length
                    tennis_indicators += 2
                elif len(words) >= 2 and all(word and word[0].isupper() for word in words):
                    # Multiple words, all starting with capital letters
                    # Less likely to be tennis if more than 2 words
                    tennis_indicators += 1 if len(words) == 2 else 0
            
            # Prefer college sports over tennis for college-sounding names
            if college_indicators > 0:
                return 'American Football'  # Most common college sport in betting
            
            # Only classify as tennis if it looks like individual names and doesn't match team sports
            if tennis_indicators >= 3:
                teams_text = ' '.join(teams).lower()
                team_sport_indicators = ['united', 'city', 'wanderers', 'villa', 'fc', 'ac', 'madrid', 'barcelona']
                if not any(indicator in teams_text for indicator in team_sport_indicators):
                    return 'Tennis'
        
        # Score based on keywords if no direct team match
        for sport, keywords in self.sport_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            # Boost score if teams match known patterns
            if teams:
                for team in teams:
                    team_lower = team.lower()
                    for keyword in keywords:
                        if keyword in team_lower:
                            score += 2
            
            if score > 0:
                scores[sport] = score
        
        # Return sport with highest score
        if scores:
            best_sport = max(scores.keys(), key=lambda x: scores[x])
            self.confidence_scores[best_sport] = scores[best_sport] / max(1, len(self.sport_keywords[best_sport]))
            return best_sport
            
        # Fallback to URL-based detection if no content matches
        if url:
            # Find all occurrences like B1, B13 etc.
            found_codes = re.findall(r'B\d+', url)
            # Iterate from the end to get the most relevant (usually the active view)
            for code in reversed(found_codes):
                if code in SPORT_CODES:
                    return SPORT_CODES[code]
        
        return 'Unknown'
    
    def is_womens_tennis(self, home_team: str, away_team: str) -> bool:
        """Determine if a tennis match is women's tennis based on player names"""
        home_words = set(word.lower() for word in home_team.split())
        away_words = set(word.lower() for word in away_team.split())
        all_words = home_words | away_words
        
        # Check for known women's players
        women_matches = len(all_words & self.womens_tennis_players)
        men_matches = len(all_words & self.mens_tennis_players)
        
        # If we have clear evidence
        if women_matches > 0 and men_matches == 0:
            return True
        if men_matches > 0 and women_matches == 0:
            return False
            
        # Heuristic: Look for feminine names (rough approximation)
        feminine_endings = {'a', 'ia', 'ova', 'eva', 'ina', 'ana'}
        feminine_count = 0
        masculine_count = 0
        
        for word in all_words:
            if len(word) > 3:
                if any(word.endswith(ending) for ending in feminine_endings):
                    feminine_count += 1
                elif word.endswith('ic') or word.endswith('ov') or word.endswith('ez'):
                    masculine_count += 1
        
        return feminine_count > masculine_count
    
    def learn_team_pattern(self, sport: str, team_name: str):
        """Learn and store team patterns for future detection"""
        if sport not in self.discovered_teams:
            self.discovered_teams[sport] = set()
        
        self.discovered_teams[sport].add(team_name.lower())
        
        # Extract pattern elements
        if sport not in self.team_patterns:
            self.team_patterns[sport] = []
        
        # Common team name patterns
        patterns = [
            r'\b\w+\s+(lions|tigers|bears|eagles|ravens|cowboys|giants|jets)\b',  # Animal/Object names
            r'\b(red|blue|green|white|black|golden)\s+\w+\b',  # Color + noun
            r'\b\w+\s+(city|united|fc|ac)\b',  # City/Club suffixes
        ]
        
        for pattern in patterns:
            if re.search(pattern, team_name.lower()):
                if pattern not in self.team_patterns[sport]:
                    self.team_patterns[sport].append(pattern)
    
    def get_discovered_teams(self, sport: str) -> List[str]:
        """Get all discovered teams for a sport"""
        return list(self.discovered_teams.get(sport, set()))
    
    def get_sport_confidence(self, sport: str) -> float:
        """Get confidence score for sport detection"""
        return self.confidence_scores.get(sport, 0.0)

class DynamicLeagueDetector:
    """Dynamically detect leagues from team combinations and context"""
    
    def __init__(self):
        self.team_league_map: Dict[str, str] = {}
        self.league_patterns: Dict[str, List[str]] = {}
        self.discovered_leagues: Set[str] = set()
        
        # Initial seed patterns - will be expanded dynamically
        self.seed_patterns = {
            'NFL': ['lions', 'ravens', 'cowboys', 'patriots', 'chiefs', 'bills', 'browns'],
            'NBA': ['lakers', 'warriors', 'celtics', 'heat', 'bulls', 'knicks', 'grizzlies', 'cavaliers', 'nets', 'raptors', 'jazz', 'thunder', 'clippers', 'kings', 'suns', 'mavericks', 'spurs', 'rockets', 'pelicans', 'timberwolves', 'pistons', 'hornets', 'wizards', 'hawks', 'magic', 'pacers', 'sixers'],
            'MLB': ['yankees', 'dodgers', 'red sox', 'astros', 'braves', 'mets', 'brewers', 'padres', 'cardinals', 'giants', 'phillies'],
            'Premier League': ['arsenal', 'chelsea', 'liverpool', 'manchester united', 'manchester city', 'tottenham', 'everton', 'newcastle', 'west ham', 'aston villa', 'wolves', 'southampton', 'brighton', 'crystal palace', 'fulham', 'bournemouth', 'nottingham forest', 'brentford', 'luton', 'burnley'],
            'La Liga': ['barcelona', 'real madrid', 'atletico madrid', 'valencia', 'sevilla', 'villarreal', 'real sociedad', 'athletic bilbao', 'betis', 'celta vigo', 'rayo vallecano', 'osasuna', 'mallorca', 'girona', 'almeria', 'getafe', 'cadiz', 'las palmas', 'alaves', 'granada'],
            'Bundesliga': ['bayern munich', 'dortmund', 'leverkusen', 'rb leipzig', 'union berlin', 'freiburg', 'wolfsburg', 'eintracht frankfurt', 'mainz', 'borussia monchengladbach', 'werder bremen', 'augsburg', 'hoffenheim', 'stuttgart', 'bochum', 'heidelberg', 'darmstadt'],
            'Serie A': ['juventus', 'ac milan', 'inter milan', 'napoli', 'roma', 'lazio', 'atalanta', 'fiorentina', 'torino', 'sassuolo', 'hellas verona', 'bologna', 'empoli', 'udinese', 'monza', 'lecce', 'salernitana', 'frosinone', 'genoa', 'cagliari'],
            'Ligue 1': ['psg', 'lyon', 'marseille', 'monaco', 'lille', 'nice', 'lens', 'rennes', 'strasbourg', 'nantes', 'toulouse', 'reims', 'montpellier', 'brest', 'lorient', 'clermont', 'metz', 'auxerre', 'angers', 'ajaccio'],
            'Champions League': ['champions league', 'ucl', 'bayern', 'psg', 'real madrid', 'barcelona', 'manchester city', 'manchester united', 'chelsea', 'arsenal', 'juventus', 'ac milan', 'inter milan', 'napoli', 'dortmund', 'psv', 'benfica', 'porto'],
            'Europa League': ['europa league', 'uel', 'roma', 'lazio', 'arsenal', 'liverpool', 'leverkusen', 'rennes', 'brighton', 'west ham', 'liverpool', 'villarreal', 'roma', 'slavia prague', 'panathinaikos'],
            'Conference League': ['conference league', 'uecl', 'fiorentina', 'lazio', 'nice', 'aston villa', 'fenerbahce', 'olympiacos', 'slavia prague', 'liverpool', 'roma'],
            'NHL': ['rangers', 'bruins', 'blackhawks', 'penguins', 'kings', 'capitals', 'devils', 'islanders', 'flyers', 'avalanche', 'blues', 'predators', 'lightning', 'panthers', 'hurricanes', 'maple leafs', 'senators', 'sabres', 'red wings', 'blue jackets'],
            'PGA Tour': ['woods', 'mcilroy', 'rahm', 'schauffele', 'koepka', 'dechambeau', 'cantlay', 'morikawa', 'thomas', 'spieth', 'johnson', 'fowler', 'mickelson', 'watson', 'garcia', 'rose', 'casey', 'poulter', 'westwood', 'fleetwood', 'fitzpatrick', 'hovland', 'matsuyama'],
            'World Snooker Tour': ['trump', 'selby', 'robertson', 'higgins', 'williams', 'murphy', 'wilson', 'lisowski', 'allen', 'ding', 'zhao', 'yan', 'brecel', 'gilbert', 'milkins', 'carter', 'bingham', 'hawkins', 'perry', 'maguire', 'stevens', 'ford', 'mcgill'],
            'ATP': ['atp', 'djokovic', 'nadal', 'federer', 'medvedev', 'alcaraz', 'sinner', 'rublev', 'tsitsipas', 'berrettini', 'zverev', 'humbert', 'ruud', 'musetti', 'bublik', 'wu', 'cerundolo', 'noguchi', 'sakamoto', 'walton', 'jacquemot', 'aiava', 'shimabukuro', 'navone', 'timofeeva', 'minnen', 'gracheva', 'tararudee', 'bucsa', 'ngounoue'],
        }
        # Canonical mapping of league -> sport
        self.league_sport_map = {
            'NFL': 'American Football',
            'NBA': 'Basketball',
            'WNBA': 'Basketball',
            'MLB': 'Baseball',
            'NPB': 'Baseball',
            'Premier League': 'Soccer',
            'La Liga': 'Soccer',
            'Bundesliga': 'Soccer',
            'Serie A': 'Soccer',
            'Ligue 1': 'Soccer',
            'Champions League': 'Soccer',
            'Europa League': 'Soccer',
            'Conference League': 'Soccer',
            'NHL': 'Ice Hockey',
            'PGA Tour': 'Golf',
            'World Snooker Tour': 'Snooker',
            'ATP': 'Tennis',
            'WTA': 'Tennis',
        }
    
    def detect_league(self, home_team: str, away_team: str, sport: str = "", context: str = "") -> str:
        """Detect league from team names and context"""
        teams_text = f"{home_team} {away_team}".lower()
        context_text = context.lower()
        
        # Special handling for tennis - detect gender
        if sport == 'Tennis':
            if sport_detector.is_womens_tennis(home_team, away_team):
                return 'WTA'
            else:
                return 'ATP'
        
        # For basketball, detect NBA vs WNBA
        if sport == 'Basketball':
            wnba_teams = ['mercury', 'lynx', 'storm', 'aces', 'sun', 'wings', 'fever', 'sparks', 'sky', 'mystics', 'liberty', 'dream']
            if any(team in teams_text for team in wnba_teams):
                return 'WNBA'
            else:
                return 'NBA'
        
        # For American Football, should always be NFL
        if sport == 'American Football':
            return 'NFL'
        
        # For baseball, check for Japanese teams
        if sport == 'Baseball':
            japanese_teams = ['lotte marines', 'nippon', 'hanshin', 'yomiuri', 'yakult', 'chunichi', 'hiroshima', 'yokohama', 'hokkaido', 'chiba', 'saitama', 'tohoku', 'orix', 'fukuoka']
            if any(team in teams_text for team in japanese_teams):
                return 'NPB'
            else:
                return 'MLB'
        
        # For Ice Hockey, typically NHL
        if sport == 'Ice Hockey':
            return 'NHL'
        
        # For Golf, typically PGA Tour
        if sport == 'Golf':
            return 'PGA Tour'
        
        # For Snooker, typically World Snooker Tour
        if sport == 'Snooker':
            return 'World Snooker Tour'
        
        # For soccer, try to detect specific leagues first
        if sport == 'Soccer':
            # Check for specific leagues based on team names
            if any(team in teams_text for team in ['manchester', 'chelsea', 'arsenal', 'liverpool', 'tottenham']):
                return 'Premier League'
            elif any(team in teams_text for team in ['barcelona', 'real madrid', 'atletico']):
                return 'La Liga'
            elif any(team in teams_text for team in ['bayern', 'dortmund', 'leverkusen']):
                return 'Bundesliga'
            elif any(team in teams_text for team in ['juventus', 'milan', 'napoli', 'roma']):
                return 'Serie A'
            elif any(team in teams_text for team in ['psg', 'lyon', 'marseille']):
                return 'Ligue 1'
            
            # Check for Champions League patterns
            champions_teams = ['bayern', 'psg', 'real madrid', 'barcelona', 'manchester city', 'manchester united', 'chelsea', 'arsenal', 'juventus', 'ac milan', 'inter milan', 'napoli', 'dortmund', 'psv', 'benfica', 'porto', 'shakhtar', 'salzburg', 'lazio', 'roma', 'leverkusen', 'psg', 'real sociedad', 'young boys', 'red star', 'copenhagen', 'galatasaray', 'feyenoord']
            if any(team in teams_text for team in champions_teams):
                # Check if both teams are from different countries (international tournament)
                home_country = self._get_team_country(home_team)
                away_country = self._get_team_country(away_team)
                if home_country and away_country and home_country != away_country:
                    self.learn_league_association('Champions League', home_team, away_team)
                    return 'Champions League'
            
            # Check for Europa League patterns
            europa_teams = ['roma', 'lazio', 'arsenal', 'liverpool', 'leverkusen', 'rennes', 'brighton', 'west ham', 'villarreal', 'slavia prague', 'panathinaikos', 'fenerbahce', 'olympiacos', 'qarabag', 'liverpool', 'west ham', 'brighton', 'maccabi haifa', 'hapoel beer sheva', 'sheriff', 'shakhtar', 'dynamo kyiv']
            if any(team in teams_text for team in europa_teams):
                home_country = self._get_team_country(home_team)
                away_country = self._get_team_country(away_team)
                if home_country and away_country and home_country != away_country:
                    self.learn_league_association('Europa League', home_team, away_team)
                    return 'Europa League'
                    
            # Default to Premier League for soccer
            return 'Premier League'
        
        # Check seed patterns first
        seed_scores = []
        for league, patterns in self.seed_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in teams_text)
            if matches > 0:
                seed_scores.append((matches, league))
        if seed_scores:
            # Prefer league with most matches; break ties by non-conflicting with current sport heuristic
            seed_scores.sort(reverse=True)
            best_league = seed_scores[0][1]
            self.learn_league_association(best_league, home_team, away_team)
            return best_league
        
        # Check learned patterns
        for team in [home_team.lower(), away_team.lower()]:
            if team in self.team_league_map:
                return self.team_league_map[team]
        
        # Context-based detection
        league_keywords = {
            'NFL': ['nfl', 'football', 'american football'],
            'NBA': ['nba', 'basketball'],
            'MLB': ['mlb', 'baseball', 'major league'],
            'Premier League': ['premier league', 'epl', 'english', 'manchester', 'chelsea', 'arsenal', 'liverpool', 'tottenham'],
            'La Liga': ['la liga', 'spanish', 'barcelona', 'real madrid', 'atletico', 'valencia', 'sevilla'],
            'Bundesliga': ['bundesliga', 'german', 'bayern', 'dortmund', 'leverkusen', 'schalke', 'werder'],
            'Serie A': ['serie a', 'italian', 'juventus', 'milan', 'inter', 'napoli', 'roma'],
            'Ligue 1': ['ligue 1', 'french', 'psg', 'lyon', 'marseille', 'monaco'],
            'Champions League': ['champions league', 'ucl', 'champions'],
            'Europa League': ['europa league', 'uel', 'europa'],
            'Conference League': ['conference league', 'uecl', 'conference'],
            'NHL': ['nhl', 'hockey', 'ice hockey'],
        }
        
        for league, keywords in league_keywords.items():
            if any(keyword in context_text or keyword in sport.lower() for keyword in keywords):
                self.learn_league_association(league, home_team, away_team)
                return league
        
        # Cross-check: if sport is American Football but teams match clearly another league (e.g., nba team names)
        if sport == 'American Football':
            disambiguation_patterns = {
                'NBA': self.seed_patterns.get('NBA', []),
                'MLB': self.seed_patterns.get('MLB', []),
                'Premier League': self.seed_patterns.get('Premier League', [])
            }
            for league, patterns in disambiguation_patterns.items():
                matches = sum(1 for pattern in patterns if pattern in teams_text)
                if matches >= 2:  # Strong signal it's a different league entirely
                    self.learn_league_association(league, home_team, away_team)
                    return league

        # Default based on sport
        sport_league_defaults = {
            'American Football': 'NFL',
            'Basketball': 'NBA', 
            'Baseball': 'MLB',
            'Soccer': 'Premier League',
            'Ice Hockey': 'NHL',
            'Tennis': 'ATP',
        }
        
        if sport in sport_league_defaults:
            league = sport_league_defaults[sport]
            self.learn_league_association(league, home_team, away_team)
            return league
        
        return 'Unknown'
    
    def _get_team_country(self, team_name: str) -> Optional[str]:
        """Get country for a team based on known leagues"""
        team_lower = team_name.lower()
        
        # Map leagues to countries
        league_countries = {
            'Premier League': 'England',
            'La Liga': 'Spain', 
            'Bundesliga': 'Germany',
            'Serie A': 'Italy',
            'Ligue 1': 'France',
            'Champions League': None,  # International
            'Europa League': None,     # International
            'Conference League': None, # International
        }
        
        # Check if team belongs to a known league
        for league, patterns in self.seed_patterns.items():
            if league in league_countries and any(pattern in team_lower for pattern in patterns):
                return league_countries[league]
        
        return None
    
    def learn_league_association(self, league: str, home_team: str, away_team: str):
        """Learn team-league associations"""
        self.discovered_leagues.add(league)
        
        for team in [home_team, away_team]:
            team_key = team.lower().strip()
            if team_key and len(team_key) > 2:  # Valid team name
                self.team_league_map[team_key] = league
        
        logging.debug(f"[LEARN] Associated {home_team} vs {away_team} with {league}")
    
    def get_discovered_leagues(self) -> List[str]:
        """Get all discovered leagues"""
        return list(self.discovered_leagues)
    
    def get_team_count_by_league(self) -> Dict[str, int]:
        """Get count of teams per league"""
        league_counts = {}
        for team, league in self.team_league_map.items():
            league_counts[league] = league_counts.get(league, 0) + 1
        return league_counts

    def get_sport_for_league(self, league: str) -> Optional[str]:
        return self.league_sport_map.get(league)

# Global instances
sport_detector = DynamicSportDetector()
league_detector = DynamicLeagueDetector()

def detect_sport_dynamically(text: str, url: str = "", teams: Optional[List[str]] = None) -> str:
    """Wrapper function for dynamic sport detection"""
    return sport_detector.detect_sport_from_context(text, url, teams)

def detect_league_dynamically(home_team: str, away_team: str, sport: str = "", context: str = "") -> str:
    """Wrapper function for dynamic league detection"""
    return league_detector.detect_league(home_team, away_team, sport, context)

def learn_team_patterns(sport: str, home_team: str, away_team: str, league: str):
    """Learn patterns from successful matches"""
    sport_detector.learn_team_pattern(sport, home_team)
    sport_detector.learn_team_pattern(sport, away_team)
    league_detector.learn_league_association(league, home_team, away_team)

def get_dynamic_stats() -> Dict:
    """Get statistics about discovered patterns"""
    return {
        'discovered_sports': list(sport_detector.discovered_teams.keys()),
        'discovered_leagues': league_detector.get_discovered_leagues(),
        'team_counts_by_sport': {sport: len(teams) for sport, teams in sport_detector.discovered_teams.items()},
        'team_counts_by_league': league_detector.get_team_count_by_league(),
        'confidence_scores': sport_detector.confidence_scores
    }