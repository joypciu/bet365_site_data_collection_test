import json

# Check the most recent JSON for any remaining issues
with open('bet365_data.json', 'r') as f:
    data = json.load(f)

print(f"Total matches: {len(data)}")

# Check for other potential issues
issues = []
tennis_atp_count = 0
tennis_wta_count = 0
college_in_wrong_sport = 0

for match_id, match in data.items():
    sport = match['sport']
    league = match['league']
    home = match['home_team']
    away = match['away_team']
    
    # Count tennis gender distribution
    if sport == 'Tennis':
        if league == 'ATP':
            tennis_atp_count += 1
        elif league == 'WTA':
            tennis_wta_count += 1
    
    # Check for college teams that might be misclassified
    college_terms = ['State', 'University', 'College', 'Tech', 'Dame']
    if any(term in home or term in away for term in college_terms):
        if sport == 'Tennis':
            college_in_wrong_sport += 1
            issues.append(f"College team in Tennis: {home} vs {away} -> {sport}/{league}")
    
    # Check for obvious sport mismatches
    if 'Patriots' in home or 'Patriots' in away:
        if sport != 'American Football':
            issues.append(f"Patriots not in American Football: {home} vs {away} -> {sport}/{league}")
    
    if 'Lakers' in home or 'Lakers' in away:
        if sport != 'Basketball':
            issues.append(f"Lakers not in Basketball: {home} vs {away} -> {sport}/{league}")

print(f"\nTennis gender distribution:")
print(f"  ATP: {tennis_atp_count}")
print(f"  WTA: {tennis_wta_count}")

print(f"\nPotential issues found:")
print(f"  College teams in wrong sport: {college_in_wrong_sport}")

if issues:
    print(f"\nSpecific issues:")
    for issue in issues[:10]:
        print(f"  ❌ {issue}")
else:
    print(f"  ✅ No obvious misclassifications found!")

# Check a few random matches for line_id and money_line_id
print(f"\nSample matches with ID fields:")
count = 0
for match_id, match in data.items():
    if count >= 3:
        break
    line_id = match.get('line_id', 'None')
    money_line_id = match.get('money_line_id', 'None')
    print(f"  {match['sport']}: {match['home_team']} vs {match['away_team']}")
    print(f"    line_id: {line_id}")
    print(f"    money_line_id: {money_line_id}")
    count += 1