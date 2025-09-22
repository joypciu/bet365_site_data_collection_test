from dataclasses import dataclass
from typing import Dict, Optional, Any

@dataclass
class Odds:
    """Represents betting odds for a match"""
    # Basic markets
    home_odds: Optional[str] = None
    away_odds: Optional[str] = None
    moneyline_home: Optional[str] = None
    moneyline_away: Optional[str] = None
    moneyline_draw: Optional[str] = None
    
    # Spread/Handicap markets
    spread_home: Optional[str] = None
    spread_home_odds: Optional[str] = None
    spread_away: Optional[str] = None
    spread_away_odds: Optional[str] = None
    asian_handicap_home: Optional[str] = None
    asian_handicap_home_odds: Optional[str] = None
    asian_handicap_away: Optional[str] = None
    asian_handicap_away_odds: Optional[str] = None
    
    # Totals markets
    total_over: Optional[str] = None
    total_over_odds: Optional[str] = None
    total_under: Optional[str] = None
    total_under_odds: Optional[str] = None
    
    # Soccer-specific markets
    btts_yes: Optional[str] = None
    btts_no: Optional[str] = None
    double_chance_1x: Optional[str] = None
    double_chance_x2: Optional[str] = None
    double_chance_12: Optional[str] = None
    draw_no_bet_home: Optional[str] = None
    draw_no_bet_away: Optional[str] = None
    
    # Special markets
    correct_score_options: Optional[list] = None
    player_props: Optional[list] = None
    
    # Live betting data
    is_live: Optional[bool] = None
    current_score: Optional[str] = None
    time_remaining: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert odds to dictionary"""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Odds':
        """Create Odds instance from dictionary"""
        # Handle field name mapping from AI extraction
        mapped_data = {}
        for key, value in data.items():
            if key == 'moneyline_home':
                mapped_data['moneyline_home'] = value
            elif key == 'moneyline_away':
                mapped_data['moneyline_away'] = value
            elif key == 'moneyline_draw':
                mapped_data['moneyline_draw'] = value
            elif key == 'home_odds':
                mapped_data['home_odds'] = value
            elif key == 'away_odds':
                mapped_data['away_odds'] = value
            elif key == 'money_home':
                mapped_data['money_home'] = value
            elif key == 'money_away':
                mapped_data['money_away'] = value
            else:
                mapped_data[key] = value
        
        return cls(**{k: v for k, v in mapped_data.items() if k in cls.__dataclass_fields__})
    
    def merge(self, other: 'Odds') -> 'Odds':
        """Merge with another Odds instance, keeping non-None values"""
        merged_data = self.to_dict()
        for key, value in other.to_dict().items():
            if value is not None:
                merged_data[key] = value
        return Odds.from_dict(merged_data)
    
    def is_empty(self) -> bool:
        """Check if odds object contains any data"""
        return all(v is None for v in self.__dict__.values())
    
    @staticmethod
    def american_to_decimal(american_odds: str) -> Optional[float]:
        """Convert American odds to decimal format"""
        try:
            odds = float(american_odds)
            if odds > 0:
                return (odds / 100) + 1
            else:
                return (100 / abs(odds)) + 1
        except (ValueError, ZeroDivisionError):
            return None
    
    @staticmethod
    def decimal_to_american(decimal_odds: float) -> Optional[str]:
        """Convert decimal odds to American format"""
        try:
            if decimal_odds >= 2:
                return f"+{int((decimal_odds - 1) * 100)}"
            else:
                return f"{int(-100 / (decimal_odds - 1))}"
        except (ValueError, ZeroDivisionError):
            return None