import pytest

from src.utils.dynamic_detection import detect_sport_dynamically
from src.utils.dynamic_detection import detect_league_dynamically
from src.parsers.html_parser import HTMLParser


def test_detect_american_football_from_b13_url():
    url = "https://www.co.bet365.com/#/HO/IP/B1/B13"  # Contains Soccer then American Football
    sport = detect_sport_dynamically(text="DET Lions @ BAL Ravens", url=url, teams=["DET Lions", "BAL Ravens"])
    assert sport == 'American Football', f"Expected American Football, got {sport}"


def test_detect_soccer_when_only_b1():
    url = "https://www.co.bet365.com/#/HO/AS/B1"  # Only soccer code
    sport = detect_sport_dynamically(text="Arsenal v Chelsea", url=url, teams=["Arsenal", "Chelsea"])
    assert sport == 'Soccer', f"Expected Soccer, got {sport}"


def test_league_disambiguation_nba_inside_b13():
    # Even if sport code is B13 (American Football), NBA teams should identify NBA league
    url = "https://www.co.bet365.com/#/HO/AS/B13"
    sport = detect_sport_dynamically(text="PHX Suns v CLE Cavaliers", url=url, teams=["PHX Suns", "CLE Cavaliers"])
    league = detect_league_dynamically("PHX Suns", "CLE Cavaliers", sport=sport, context="PHX Suns v CLE Cavaliers")
    assert league == 'NBA', f"Expected NBA, got {league}"


def test_league_implies_sport_override():
    # Simulate that league detection returns NBA and sport fallback was American Football
    url = "https://www.co.bet365.com/#/HO/AS/B13"
    initial_sport = detect_sport_dynamically(text="PHX Suns v CLE Cavaliers", url=url, teams=["PHX Suns", "CLE Cavaliers"])
    league = detect_league_dynamically("PHX Suns", "CLE Cavaliers", sport=initial_sport, context="PHX Suns v CLE Cavaliers")
    from src.utils.dynamic_detection import league_detector
    implied = league_detector.get_sport_for_league(league)
    assert implied == 'Basketball', f"Expected Basketball, got {implied}"


def test_team_cleaning_removes_parentheses_and_short_codes():
    parser = HTMLParser()
    cleaned = parser._clean_team_name("MIL Brewers (F Peralta)")
    assert cleaned == 'MIL Brewers', f"Unexpected cleaned team {cleaned}"
    short = parser._clean_team_name("CLE")
    assert short == 'Unknown', f"Short abbreviation should be Unknown, got {short}"
