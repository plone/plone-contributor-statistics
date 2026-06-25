import requests
import csv
import os
import re
from collections import defaultdict

def load_known_organisations():
    """Load known organisations and their members."""
    org_mapping = {}
    try:
        with open('organisations.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['Organisation']
                members = row['Team'].split(';')
                for member in members:
                    if member:
                        org_mapping[member.lower()] = org
    except FileNotFoundError:
        pass
    
    # Manual mappings for known trainers not in organisations.csv
    manual_mappings = {
        'katja süss': 'Rohberg',
        'katja suss': 'Rohberg',
        'philip bauer': 'Starzel',
        'fred van dijk': 'kitconcept GmbH',
        'víctor fernández de alba': 'kitconcept GmbH',
        'victor fernandez de alba': 'kitconcept GmbH',
        'timo stollenwerk': 'kitconcept GmbH',
        'érico andrei': 'kitconcept GmbH',
        'erico andrei': 'kitconcept GmbH',
        'alok kumar': 'kitconcept GmbH',
        'jakob kahl': 'kitconcept GmbH',
        'tiberiu ichim': 'Eau de Web',
        'david ichim': 'kitconcept GmbH',
        'nilesh gulia': 'Eau de Web',
        'claudia ifrim': 'Eau de Web',
        'paul roeland': 'CCC',
        'kim nguyen': 'Six Feet Up',
        't. kim nguyen': 'Six Feet Up',
        'maik derstappen': 'Derico',
        'stefan antonelli': 'Kombinat',
        'jens klein': 'Klein & Partner KG',
        'johannes raggam': 'Independent',
        'sko soukka': 'University of Jyväskylä',
        'asko soukka': 'University of Jyväskylä',
        'kim paulissen': 'KU Leuven',
        'morganna giovanelli': 'Independent',
        'leon sólon da silva': 'Independent',
        'luciano ramalho': 'Thoughtworks',
        'alexandre b a villares': 'Independent',
        'renan de assis': 'Independent',
        'ana dulce': 'Independent',
        'dante alvarez': 'kitconcept GmbH',
        'rohit kumar': 'kitconcept GmbH',
        'andre da silva mesquita': 'Independent',
        'talita rossari': 'Independent'
    }
    return org_mapping, manual_mappings

def get_org_for_trainer(name, org_mapping, manual_mappings):
    name_lower = name.lower().strip()
    if name_lower in manual_mappings:
        return manual_mappings[name_lower]
    
    # Try to find if any part of the name is in manual_mappings
    for key, org in manual_mappings.items():
        if key in name_lower or name_lower in key:
            return org
            
    return "Independent"

def fetch_2024_trainings(org_mapping, manual_mappings):
    print("Fetching 2024 trainings...")
    url = "https://2024.ploneconf.org/++api++/en/schedule/training"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        items = resp.json().get('items', [])
        trainings = []
        for item in items:
            title = item.get('title')
            presenters = [p.get('title') for p in item.get('presenters', [])]
            # Map presenters to orgs
            orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in presenters])))
            trainings.append({
                'Title': title,
                'Trainer(s)': "; ".join(presenters),
                'GitHub Handle(s)': "", # API doesn't give them easily here
                'Organisation': "; ".join(orgs)
            })
        return trainings
    except Exception as e:
        print(f"Error fetching 2024: {e}")
        return []

def fetch_2023_trainings(org_mapping, manual_mappings):
    print("Fetching 2023 trainings...")
    url = "https://2023.ploneconf.org/++api++/training"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        data = resp.json()
        items = data.get('items', [])
        trainings = []
        
        # Also try to parse the slate table which has more accurate groupings
        blocks = data.get('blocks', {})
        for block in blocks.values():
            if block.get('@type') == 'slateTable':
                rows = block.get('table', {}).get('rows', [])
                for row in rows:
                    cells = row.get('cells', [])
                    # Skip header rows
                    if any("Monday" in str(c) or "Tuesday" in str(c) for c in cells): continue
                    # Typically: Time, Room 1, Room 2, Room 3, Room 4
                    for cell in cells[1:]:
                        val = cell.get('value', [])
                        text = ""
                        # This is getting messy, let's stick to items if possible or basic slate parsing
        
        for item in items:
            title = item.get('title')
            desc = item.get('description', '')
            # Heuristic for trainers in 2023: they are at the end of the description
            match = re.search(r"Trainer[s]?\s+([\w\s,]+)$", desc, re.IGNORECASE)
            presenters = []
            if match:
                presenters = [p.strip() for p in re.split(r",|and", match.group(1))]
            
            orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in presenters])))
            trainings.append({
                'Title': title,
                'Trainer(s)': "; ".join(presenters),
                'GitHub Handle(s)': "",
                'Organisation': "; ".join(orgs)
            })
        return trainings
    except Exception as e:
        print(f"Error fetching 2023: {e}")
        return []

def fetch_2022_trainings(org_mapping, manual_mappings):
    print("Fetching 2022 trainings...")
    url = "https://2022.ploneconf.org/schedule/training.html"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        html = resp.text
        # Look for links like training/mastering-plone-6.html
        # and the name inside the <td>
        import html as html_lib
        matches = re.findall(r"<strong><a href=\"(training/.*?\.html)\">(.*?)</a></strong>.*?<br />\s*(.*?)\s*</td>", html, re.DOTALL)
        trainings_dict = {}
        for link, title, presenters_raw in matches:
            title = html_lib.unescape(title.strip())
            presenters_raw = html_lib.unescape(presenters_raw.replace("<br />", " "))
            presenters = [p.strip() for p in re.split(r",|and", presenters_raw)]
            presenters = [p for p in presenters if p and len(p) < 60 and not p.startswith("(")]
            
            if title not in trainings_dict:
                orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in presenters])))
                trainings_dict[title] = {
                    'Title': title,
                    'Trainer(s)': "; ".join(presenters),
                    'GitHub Handle(s)': "",
                    'Organisation': "; ".join(orgs)
                }
        return list(trainings_dict.values())
    except Exception as e:
        print(f"Error fetching 2022: {e}")
        return []

def fetch_2020_trainings(org_mapping, manual_mappings):
    print("Fetching 2020 trainings...")
    url = "https://2020.ploneconf.org/trainings.html"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        html = resp.text
        # <a href="trainings/mastering-plone-6-part-1.html" title="training_class">Mastering Plone 6 (Part 1)</a>
        links = re.findall(r"href=\"(trainings/.*?\.html)\"[^>]*?>(.*?)</a>", html)
        trainings_dict = {}
        for link, title in links:
            t_url = f"https://2020.ploneconf.org/{link}"
            t_resp = requests.get(t_url, timeout=30)
            if t_resp.status_code != 200: continue
            t_html = t_resp.text
            
            # <h4><strong>Instructor:</strong> <a href="../speakers/katja-suss.html">Katja Süss</a>, <a href="../speakers/philip-bauer.html">Philip Bauer</a></h4>
            # Find all speaker links in that line
            instructor_section = re.search(r"Instructor:</strong>(.*?)</h\d>", t_html, re.DOTALL)
            if instructor_section:
                trainers = re.findall(r"speakers/.*?\.html\">(.*?)</a>", instructor_section.group(1))
                # Clean title (remove Part 1/2)
                clean_title = re.sub(r"\s*\(Part \d\)", "", title).strip()
                if clean_title not in trainings_dict:
                    orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in trainers])))
                    trainings_dict[clean_title] = {
                        'Title': clean_title,
                        'Trainer(s)': "; ".join(trainers),
                        'GitHub Handle(s)': "",
                        'Organisation': "; ".join(orgs)
                    }
        return list(trainings_dict.values())
    except Exception as e:
        print(f"Error fetching 2020: {e}")
        return []

def main():
    org_mapping, manual_mappings = load_known_organisations()
    os.makedirs('data/community-contributions', exist_ok=True)
    
    fetchers = {
        2024: fetch_2024_trainings,
        2023: fetch_2023_trainings,
        2022: fetch_2022_trainings,
        2020: fetch_2020_trainings
    }
    
    for year, fetcher in fetchers.items():
        trainings = fetcher(org_mapping, manual_mappings)
        if trainings:
            output_file = f'data/community-contributions/{year}-plone-conference-trainings.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Title', 'Trainer(s)', 'GitHub Handle(s)', 'Organisation'])
                writer.writeheader()
                writer.writerows(trainings)
            print(f"  Created {output_file} ({len(trainings)} trainings)")
        else:
            print(f"  No trainings found for {year}")

if __name__ == "__main__":
    main()
