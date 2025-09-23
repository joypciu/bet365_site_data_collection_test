from playwright.sync_api import sync_playwright
import patchright  # Ensure Patchright is installed (e.g., pip install patchright)
import json
import os
from datetime import datetime, timezone
import hashlib
from bs4 import BeautifulSoup
import time
import random

# List of user agents for randomization
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Store unique entries to avoid duplicates
seen_matches = set()
matches = {}

def bet365_patch(route, request):
    # Check if the request is for bet365
    if request.url.startswith("https://www.bet365.com") or request.url.startswith("https://mobile.bet365.com"):
        print(f"Intercepted request: {request.url}")
        # Modify headers (e.g., User-Agent) for stealth
        headers = request.headers
        headers["User-Agent"] = random.choice(user_agents)
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        headers["Accept-Language"] = "en-US,en;q=0.5"
        headers["Accept-Encoding"] = "gzip, deflate, br"
        headers["Cache-Control"] = "no-cache"
        headers["Pragma"] = "no-cache"
        headers["DNT"] = "1"
        # Continue the request with modified headers
        route.continue_(headers=headers)
    else:
        # Continue other requests without modification
        route.continue_()

def save_to_json(data, filename="bet365_data.json"):
    # Append new data to JSON file
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = []
    
    existing_data.append(data)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=4)
    print(f"Saved data to {filename}")

def generate_match_key(match_data):
    # Create a unique key for deduplication based on match details
    key = f"{match_data.get('home_team', '')}_{match_data.get('away_team', '')}_{match_data.get('match_id', '')}"
    return hashlib.md5(key.encode()).hexdigest()

def extract_match_data(item):
    match_id = item.get("id", item.get("event_id", item.get("FI", item.get("ID", item.get("IT", "unknown").split('_')[0] if '_' in item.get("IT", "") else "unknown"))))
    home_team = item.get("home_team", item.get("home", {}).get("name", item.get("team1", item.get("TM", item.get("SS", "").split('-')[0] if item.get("SS") else item.get("NA", "").split(' v ')[0] if ' v ' in item.get("NA", "") else item.get("CB", "unknown")))))
    away_team = item.get("away_team", item.get("away", {}).get("name", item.get("team2", item.get("TV", item.get("SS", "").split('-')[1] if item.get("SS") else item.get("NA", "").split(' v ')[1] if ' v ' in item.get("NA", "") else "unknown"))))
    league = item.get("league", item.get("competition", item.get("CT", item.get("CL", item.get("L3", "unknown")))))
    match_time = item.get("time", item.get("start_time", item.get("TT", item.get("TR", item.get("SM", "unknown")))))

    # Build odds dict
    odds = {}
    for key in ['OD', 'HA', 'HD', 'SU', 'OR', 'XP', 'SS']:
        if key in item:
            if key not in odds:
                odds[key] = []
            odds[key].append(item[key])

    # Convert match_time if it's a timestamp
    if match_time.isdigit():
        match_time = datetime.fromtimestamp(int(match_time)).isoformat()

    # Filter out numeric-only team names (likely scores)
    if home_team and home_team.isdigit():
        home_team = "unknown"
    if away_team and away_team.isdigit():
        away_team = "unknown"

    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "match_time": match_time,
        "odds": odds,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def parse_bet365_format(text):
    # Simple parser for Bet365's pipe-delimited format
    matches = []
    current_match = {}
    segments = text.split('|')
    for segment in segments:
        if not segment:
            continue
        fields = segment.split(';')
        for field in fields:
            if '=' in field:
                key, value = field.split('=', 1)
                if key == 'EV' or key == 'MA':  # Start of match or market
                    if current_match:
                        matches.append(current_match)
                    current_match = {}
                current_match[key] = value
            elif field:  # Possible type like 'MA' or 'PA'
                if current_match:
                    matches.append(current_match)
                current_match = {'type': field}
    if current_match:
        matches.append(current_match)
    return matches

def main():
    # Launch Playwright with Patchright for stealthy browser automation
    with sync_playwright() as p:
        # Launch a Chromium-based browser (Patchright only supports Chromium)
        browser = p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ])  # Disable automation flags and add stealth
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},  # Desktop viewport
            user_agent=random.choice(user_agents),
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.bet365.com/",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

        # Create a new page
        page = context.new_page()

        # Set up request interception for modifying headers
        page.route("**/*", bet365_patch)

        # Set up response listener to capture real-time API data
        def handle_response(response):
            # Focus on URLs likely containing real-time data
            if (response.url.startswith("https://www.bet365.com") or response.url.startswith("https://mobile.bet365.com")) and (
                "inplay" in response.url.lower() or 
                "api" in response.url.lower() or 
                "schedule" in response.url.lower() or 
                "data" in response.url.lower() or 
                "event" in response.url.lower() or
                "diary" in response.url.lower()
            ):
                print(f"\n=== Intercepted real-time response: {response.url} ===")
                try:
                    # Parse JSON data
                    raw_data = response.json()
                    print(f"Raw data structure: {json.dumps(raw_data, indent=2)[:500]}...")  # Log first 500 chars for debugging
                    
                    # Save raw response for manual inspection
                    raw_entry = {
                        "url": response.url,
                        "status": response.status,
                        "raw_data": raw_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    save_to_json(raw_entry, filename="bet365_raw_data.json")

                    # Attempt to extract match details

                    if isinstance(raw_data, list):
                        for item in raw_data:
                            match_data = extract_match_data(item)
                            match_id = match_data['match_id']
                            if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                match_key = generate_match_key(match_data)
                                if match_id not in matches:
                                    matches[match_id] = match_data
                                    seen_matches.add(match_key)
                                    print(json.dumps(match_data, indent=4))
                                else:
                                    if match_data['odds']:
                                        for key, value in match_data['odds'].items():
                                            if key in matches[match_id]['odds']:
                                                if isinstance(matches[match_id]['odds'][key], list):
                                                    if isinstance(value, list):
                                                        matches[match_id]['odds'][key].extend(value)
                                                    else:
                                                        matches[match_id]['odds'][key].append(value)
                                                else:
                                                    matches[match_id]['odds'][key] = [matches[match_id]['odds'][key]] + (value if isinstance(value, list) else [value])
                                            else:
                                                matches[match_id]['odds'][key] = value
                                        print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                    
                    elif isinstance(raw_data, dict):
                        # Check for nested data
                        if "events" in raw_data:
                            for item in raw_data["events"]:
                                match_data = extract_match_data(item)
                                match_id = match_data['match_id']
                                if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                    match_key = generate_match_key(match_data)
                                    if match_id not in matches:
                                        matches[match_id] = match_data
                                        seen_matches.add(match_key)
                                        print(json.dumps(match_data, indent=4))
                                    else:
                                        if match_data['odds']:
                                            for key, value in match_data['odds'].items():
                                                if key in matches[match_id]['odds']:
                                                    if isinstance(matches[match_id]['odds'][key], list):
                                                        if isinstance(value, list):
                                                            matches[match_id]['odds'][key].extend(value)
                                                        else:
                                                            matches[match_id]['odds'][key].append(value)
                                                    else:
                                                        matches[match_id]['odds'][key] = [matches[match_id]['odds'][key]] + (value if isinstance(value, list) else [value])
                                                else:
                                                    matches[match_id]['odds'][key] = value
                                            print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                        else:
                            match_data = extract_match_data(raw_data)
                            match_id = match_data['match_id']
                            if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                match_key = generate_match_key(match_data)
                                if match_id not in matches:
                                    matches[match_id] = match_data
                                    seen_matches.add(match_key)
                                    print(json.dumps(match_data, indent=4))
                                else:
                                    if match_data['odds']:
                                        for key, value in match_data['odds'].items():
                                            if key in matches[match_id]['odds']:
                                                if isinstance(matches[match_id]['odds'][key], list):
                                                    if isinstance(value, list):
                                                        matches[match_id]['odds'][key].extend(value)
                                                    else:
                                                        matches[match_id]['odds'][key].append(value)
                                                else:
                                                    matches[match_id]['odds'][key] = [matches[match_id]['odds'][key]] + (value if isinstance(value, list) else [value])
                                            else:
                                                matches[match_id]['odds'][key] = value
                                        print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                    
                except Exception as e:
                    print(f"Could not parse response as JSON: {e}")
                    # Try parsing as Bet365 pipe format
                    try:
                        raw_text = response.text()
                        parsed_matches = parse_bet365_format(raw_text)
                        for match in parsed_matches:
                            if 'FI' in match or 'ID' in match or 'IT' in match:  # Only process if it's a match
                                match_data = extract_match_data(match)
                                match_id = match_data['match_id']
                                if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                    match_key = generate_match_key(match_data)
                                    if match_id not in matches:
                                        matches[match_id] = match_data
                                        seen_matches.add(match_key)
                                        print(json.dumps(match_data, indent=4))
                                    else:
                                        if match_data['odds']:
                                            matches[match_id]['odds'].update(match_data['odds'])
                                            print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                        raw_entry = {
                            "url": response.url,
                            "status": response.status,
                            "raw_text": raw_text[:1000],  # Limit to 1000 chars
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        save_to_json(raw_entry, filename="bet365_raw_data.json")
                    except Exception as e:
                        print(f"Error parsing pipe: {e}")
                        pass

        page.on("response", handle_response)

        # Set up WebSocket listener to capture real-time updates
        def handle_websocket(ws):
            print(f"WebSocket opened: {ws.url}")
            def handle_frame(frame):
                print(f"WebSocket frame: {frame[:500]}...")
                # Try to parse frame as JSON or pipe format
                try:
                    raw_data = json.loads(frame)

                    if isinstance(raw_data, list):
                        for item in raw_data:
                            match_data = extract_match_data(item)
                            match_id = match_data['match_id']
                            if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                match_key = generate_match_key(match_data)
                                if match_id not in matches:
                                    matches[match_id] = match_data
                                    seen_matches.add(match_key)
                                    print(json.dumps(match_data, indent=4))
                                else:
                                    if match_data['odds'] != {}:
                                        matches[match_id]['odds'] = match_data['odds']
                                        print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                    elif isinstance(raw_data, dict):
                        if "events" in raw_data:
                            for item in raw_data["events"]:
                                match_data = extract_match_data(item)
                                match_id = match_data['match_id']
                                if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                    match_key = generate_match_key(match_data)
                                    if match_id not in matches:
                                        matches[match_id] = match_data
                                        seen_matches.add(match_key)
                                        print(json.dumps(match_data, indent=4))
                                    else:
                                        if match_data['odds'] != {}:
                                            matches[match_id]['odds'] = match_data['odds']
                                            print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                        else:
                            match_data = extract_match_data(raw_data)
                            match_id = match_data['match_id']
                            if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                match_key = generate_match_key(match_data)
                                if match_id not in matches:
                                    matches[match_id] = match_data
                                    seen_matches.add(match_key)
                                    print(json.dumps(match_data, indent=4))
                                else:
                                    if match_data['odds'] != {}:
                                        matches[match_id]['odds'] = match_data['odds']
                                        print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                except json.JSONDecodeError:
                    # Try parsing as Bet365 pipe format
                    try:
                        parsed_matches = parse_bet365_format(frame)
                        for match in parsed_matches:
                            if 'FI' in match or 'ID' in match or 'IT' in match:  # Only process if it's a match
                                match_data = extract_match_data(match)
                                match_id = match_data['match_id']
                                if match_id != "unknown" and match_data["home_team"] != "unknown" and match_data["away_team"] != "unknown":
                                    match_key = generate_match_key(match_data)
                                    if match_id not in matches:
                                        matches[match_id] = match_data
                                        seen_matches.add(match_key)
                                        print(json.dumps(match_data, indent=4))
                                    else:
                                        if match_data['odds'] != {}:
                                            matches[match_id]['odds'] = match_data['odds']
                                            print(f"Updated odds for {match_data['home_team']} vs {match_data['away_team']}")
                    except Exception as e:
                        print(f"Error parsing WS pipe: {e}")
                        pass
            ws.on("framereceived", handle_frame)

        page.on("websocket", handle_websocket)

        # Navigate to the Bet365 in-play section (B1 for soccer)
        url = "https://www.bet365.com/#/IP/B1"
        max_retries = 3
        for attempt in range(max_retries):
            time.sleep(random.randint(2, 5))  # Random delay for stealth
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=120000)  # 120-second timeout
                page.wait_for_load_state('networkidle', timeout=60000)
                if response:
                    print(f"Page loaded with status: {response.status}")
                else:
                    print("Page goto returned None")

                # Wait for content to load with retry
                for _ in range(3):
                    try:
                        page.wait_for_selector("div.ovm-Fixture", state="visible", timeout=60000)
                        break
                    except:
                        print(f"Waiting for content... Attempt {attempt + 1}, Retry {_ + 1}")
                        time.sleep(10)  # Wait 10 seconds before retrying
                else:
                    print("Selector not found after retries, continuing to collect data anyway...")

                # Scroll to load more content
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                # Scrape the page content for match data as fallback
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                match_blocks = soup.select("div.ovm-Fixture")
                for block in match_blocks:
                    try:
                        team_elems = block.select("div.ovm-FixtureDetailsTwoWay_TeamName")
                        if len(team_elems) < 2:
                            continue
                        home_elem = team_elems[0]
                        away_elem = team_elems[1]
                        league_elem = block.select_one("div.ovm-ClassificationHeader_ClassName")
                        time_elem = block.select_one("div.ovm-FixtureDetailsTwoWay_Time")
                        odds_elems = block.select("div.ovm-FixtureOddsTwoWay_Odds")

                        home = home_elem.text.strip() if home_elem else "unknown"
                        away = away_elem.text.strip() if away_elem else "unknown"
                        league = league_elem.text.strip() if league_elem else "unknown"
                        match_time = time_elem.text.strip() if time_elem else "unknown"
                        odds = {}
                        if len(odds_elems) >= 3:
                            odds = {
                                "OD": [odds_elems[0].text.strip(), odds_elems[1].text.strip(), odds_elems[2].text.strip()],
                            }
                        match_id = str(hash(home + away + league))  # Placeholder ID
                        match_data = {
                            "match_id": match_id,
                            "home_team": home,
                            "away_team": away,
                            "league": league,
                            "match_time": match_time,
                            "odds": odds,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        if match_id not in matches and home != "unknown" and away != "unknown":
                            matches[match_id] = match_data
                            seen_matches.add(generate_match_key(match_data))
                            print(json.dumps(match_data, indent=4))
                        else:
                            if odds:
                                matches[match_id]['odds'].update(odds)
                                print(f"Updated odds for {home} vs {away}")
                    except Exception as e:
                        print(f"Error parsing block: {e}")
                        pass

                # Keep browser open to collect real-time data
                print("Collecting real-time data for 30 seconds...")
                time.sleep(30)  # Run for 30 seconds

                # Save all collected matches
                for match_data in matches.values():
                    save_to_json(match_data)
                print(f"Saved {len(matches)} matches to JSON")
                break

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)  # Wait before retrying
                else:
                    print("Max retries reached, giving up.")

        # Clean up
        browser.close()

if __name__ == "__main__":
    main()