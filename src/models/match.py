from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timezone
from .odds import Odds

@dataclass
class Match:
    """Represents a sports match with odds"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    sport: str
    match_time: str
    odds: Dict
    match_type: str
    timestamp: str
    source_url: Optional[str] = None
    
    # Live betting fields
    is_live: bool = False
    current_score: Optional[str] = None
    time_remaining: Optional[str] = None
    
    @classmethod
    def create(cls, home_team: str, away_team: str, league: str, sport: str = "Unknown",
               match_time: str = "unknown", odds: Optional[Dict] = None, 
               match_type: str = "prematch", source_url: Optional[str] = None) -> 'Match':
        """Create a new Match instance with generated match_id"""
        # Use sport as base for ID since it's more stable than league (league can be mis-detected)
        base_sport = sport if sport and sport != 'Unknown' else league
        def sanitize(name: str) -> str:
            return name.replace(' ', '_').replace('/', '_').lower()
        match_id = f"{sanitize(base_sport)}_{sanitize(home_team)}_{sanitize(away_team)}_{match_time}".lower()
        return cls(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            sport=sport,
            match_time=match_time,
            odds=odds or {},
            match_type=match_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_url=source_url
        )
    
    def to_dict(self) -> Dict:
        """Convert match to dictionary for JSON serialization"""
        result = {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league": self.league,
            "sport": self.sport,
            "match_time": self.match_time,
            "odds": self.odds,
            "type": self.match_type,
            "timestamp": self.timestamp,
            "source_url": self.source_url
        }
        
        # Add live betting fields if present
        if self.is_live:
            result["is_live"] = self.is_live
        if self.current_score:
            result["current_score"] = self.current_score
        if self.time_remaining:
            result["time_remaining"] = self.time_remaining
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Match':
        """Create Match instance from dictionary"""
        return cls(
            match_id=data["match_id"],
            home_team=data["home_team"],
            away_team=data["away_team"],
            league=data["league"],
            sport=data.get("sport", "Unknown"),
            match_time=data["match_time"],
            odds=data["odds"],
            match_type=data.get("type", "prematch"),
            timestamp=data["timestamp"],
            source_url=data.get("source_url"),
            is_live=data.get("is_live", False),
            current_score=data.get("current_score"),
            time_remaining=data.get("time_remaining")
        )
    
    def update_odds(self, new_odds: Dict):
        """Update match odds with new data"""
        self.odds.update(new_odds)
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def add_odds_from_odds_object(self, odds: Odds):
        """Add odds from an Odds object"""
        self.odds.update(odds.to_dict())
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def is_same_match(self, other: 'Match') -> bool:
        """Check if this is the same match as another"""
        return (self.home_team.lower() == other.home_team.lower() and 
                self.away_team.lower() == other.away_team.lower() and
                self.league.lower() == other.league.lower())
    
    def get_teams_display(self) -> str:
        """Get formatted team display string"""
        return f"{self.home_team} vs {self.away_team}"