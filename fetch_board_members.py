import requests
import csv
import json
import os
import re

def load_known_organisations():
    """Load known organisations to help with mapping."""
    org_list = []
    try:
        with open('organisations.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org_list.append(row['Organisation'])
    except FileNotFoundError:
        pass
    # Add common variants and major Plone companies
    org_list.extend(['Affinitic', 'Nuclia', 'Federal Senate', 'Interlegis', 'Cosent', 
                    'CodeSyntax', 'kitconcept', 'Eau de Web', 'RedTurtle', 'Starzel',
                    'Syslab', 'Six Feet Up', 'Abstract', 'Jarn', 'Zest', '4Teamwork', 'University of Jyväskylä',
                    'Simples Consultoria', 'Six Feet Up', 'Wildcard', 'Enfold', 'Kombinat', 'Agitator'])
    return sorted(list(set(org_list)), key=len, reverse=True)

def extract_org_from_bio(bio, known_orgs):
    """Heuristic to extract organisation from bio text."""
    if not bio:
        return "Independent"
        
    # Try to find known organisations first
    for org in known_orgs:
        if org.lower() in bio.lower():
            if "Federal Senate" in org or "Interlegis" in org:
                return "Federal Senate (Interlegis Program)"
            return org
    
    # Try regex patterns
    patterns = [
        r"CEO (?:of|at) ([\w\s&]+)",
        r"worked (?:for|at) ([\w\s&]+)",
        r"leads the Plone team at ([\w\s&]+)",
        r"developer at ([\w\s&]+)",
        r"founder of ([\w\s&]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, bio, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip().split(',')[0].split('.')[0]
            if len(extracted) > 2:
                return extracted
            
    return "Independent"

def fetch_board_year(slug, known_orgs):
    api_url = f"https://plone.org/++api++/foundation/board/{slug}"
    print(f"Fetching {slug}...")
    try:
        response = requests.get(api_url, timeout=30)
        if response.status_code != 200:
            print(f"  Error fetching {slug}: {response.status_code}")
            return []
        
        data = response.json()
    except Exception as e:
        print(f"  Exception fetching {slug}: {e}")
        return []
        
    members = []
    blocks = data.get('blocks', {})
    layout = data.get('blocks_layout', {}).get('items', [])
    
    # Track names to avoid duplicates in the same page
    current_name = None
    current_bio = ""
    
    for block_id in layout:
        block = blocks.get(block_id, {})
        block_type = block.get('@type')
        
        # Heuristic for slate blocks
        if block_type == 'slate':
            value = block.get('value', [])
            for v in value:
                if not isinstance(v, dict): continue
                
                # Extract text from children recursively
                def get_text(node):
                    text = ""
                    if 'text' in node:
                        text += node['text']
                    if 'children' in node:
                        for child in node['children']:
                            text += get_text(child)
                    return text
                
                node_text = get_text(v).strip()
                if not node_text: continue
                
                # h2, h3 or bold text in a paragraph might be a name
                is_header = v.get('type') in ['h2', 'h3']
                is_bold = False
                if v.get('type') == 'p' and 'children' in v:
                    # Check if the first child is strong
                    first_child = v['children'][0]
                    if isinstance(first_child, dict) and first_child.get('type') == 'strong':
                        is_bold = True
                
                # If it's a short text and looks like a name
                bad_titles = ["Email us!", "Loading", "Previous Boards", "Board of Directors", 
                              "Non-Voting Board Members - Treasurer", "Treasurer", "President", 
                              "Vice President", "Secretary", "year on the board", "term on the board",
                              "Chair", "Liaison", "Assistant Secretary"]
                
                is_bad = any(title.lower() in node_text.lower() for title in bad_titles)
                
                if (is_header or is_bold or (len(node_text) < 40 and node_text[0].isupper())) and not is_bad:
                    
                    if current_name and node_text != current_name:
                        org = extract_org_from_bio(current_bio, known_orgs)
                        members.append({'Name': current_name, 'Organisation': org})
                        print(f"    Found name: {current_name}")
                        current_bio = ""
                    current_name = node_text
                else:
                    current_bio += node_text + " "
                    
        elif block_type == 'text7' or block_type == 'teaser':
            name = block.get('title', '').strip()
            if name:
                bad_titles = ["Email us!", "Loading", "Previous Boards", "Board of Directors", 
                              "Non-Voting Board Members - Treasurer", "Treasurer", "President", 
                              "Vice President", "Secretary", "year on the board", "term on the board",
                              "Chair", "Liaison", "Assistant Secretary"]
                is_bad = any(title.lower() in name.lower() for title in bad_titles)
                
                if not is_bad:
                    if current_name:
                        org = extract_org_from_bio(current_bio, known_orgs)
                        members.append({'Name': current_name, 'Organisation': org})
                        print(f"    Found name: {current_name}")
                    current_name = name
                    current_bio = ""
            
            content_blocks = block.get('content', {}).get('blocks', [])
            current_bio += " ".join([b.get('text', '') for b in content_blocks])
            
        elif block.get('plaintext'):
            text = block.get('plaintext', '').strip()
            if not text: continue
            
            bad_titles = ["Email us!", "Loading", "Previous Boards", "Board of Directors", 
                          "Non-Voting Board Members - Treasurer", "Treasurer", "President", 
                          "Vice President", "Secretary", "year on the board", "term on the board",
                          "Chair", "Liaison", "Assistant Secretary"]
            is_bad = any(title.lower() in text.lower() for title in bad_titles)

            if not is_bad and not current_name and 0 < len(text) < 40 and text[0].isupper():
                current_name = text
            elif not is_bad and current_name and 0 < len(text) < 40 and text[0].isupper():
                # New name found
                org = extract_org_from_bio(current_bio, known_orgs)
                members.append({'Name': current_name, 'Organisation': org})
                print(f"    Found name: {current_name}")
                current_name = text
                current_bio = ""
            else:
                current_bio += text + " "

    # Don't forget the last member
    if current_name and current_name != "Non-Voting Board Members - Treasurer":
        org = extract_org_from_bio(current_bio, known_orgs)
        members.append({'Name': current_name, 'Organisation': org})
            
    return members

def main():
    known_orgs = load_known_organisations()
    # Map second year to the slug
    years = {
        2025: "plone-foundation-board-for-2024-2025",
        2024: "plone-foundation-board-for-2023-2024",
        2023: "plone-foundation-board-for-2022-2023",
        2022: "plone-foundation-board-for-2021-2022",
        2021: "plone-foundation-board-for-2020-2021",
        2020: "plone-foundation-board-for-2019-2020"
    }
    
    os.makedirs('data/community-contributions', exist_ok=True)
    
    # Manual overrides for known data where heuristics might fail
    overrides = {
        "Chrissy Wainwright": "Six Feet Up",
        "Erico Andrei": "kitconcept GmbH",
        "Érico Andrei": "kitconcept GmbH",
        "Victor Fernandez de Alba": "kitconcept GmbH",
        "Víctor Fernández de Alba": "kitconcept GmbH",
        "Paul Roeland": "CCC",
        "Jens Klein": "Klein & Partner KG",
        "Andy Leeb": "Onna",
        "William Fennie": "Independent",
        "T. Kim Nguyen": "Six Feet Up",
        "Kim Nguyen": "Six Feet Up",
        "Filip Heplo": "Abstract IT",
        "Mikel Larreategi": "CodeSyntax",
        "Fulvio Casali": "Soliton Consulting",
        "Lucie Lejard": "Independent",
        "Alexander Loechel": "Ludwig Maximilian University",
        "Carol Ganz": "Six Feet Up",
        "Maurizio Delmonte": "Abstract IT"
    }

    for year, slug in years.items():
        members = fetch_board_year(slug, known_orgs)
        if members:
            # Deduplicate members and apply overrides
            seen = set()
            unique_members = []
            for m in members:
                name = m['Name']
                # Skip some generic titles that might be caught
                if name in ["Board of Directors", "Non-Voting Board Members - Treasurer", "Previous Boards"]:
                    continue
                if name not in seen:
                    if name in overrides:
                        m['Organisation'] = overrides[name]
                    unique_members.append(m)
                    seen.add(name)
            
            output_file = f'data/community-contributions/{year}-board-of-directors.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Name', 'Organisation'])
                writer.writeheader()
                writer.writerows(unique_members)
            print(f"  Created {output_file} ({len(unique_members)} members)")

if __name__ == "__main__":
    main()
