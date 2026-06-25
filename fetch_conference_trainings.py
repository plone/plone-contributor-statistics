import requests
import csv
import os
import re

def load_known_organisations():
    org_mapping = {}
    try:
        with open('organisations.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['Organisation']
                members = row['Team'].split(';')
                for member in members:
                    if member: org_mapping[member.lower()] = org
    except FileNotFoundError: pass
    
    manual_mappings = {
        'katja süss': 'Rohberg', 'katja suss': 'Rohberg', 'philip bauer': 'Starzel',
        'fred van dijk': 'kitconcept GmbH', 'víctor fernández de alba': 'kitconcept GmbH',
        'victor fernandez de alba': 'kitconcept GmbH', 'timo stollenwerk': 'kitconcept GmbH',
        'érico andrei': 'kitconcept GmbH', 'erico andrei': 'kitconcept GmbH',
        'alok kumar': 'kitconcept GmbH', 'jakob kahl': 'kitconcept GmbH',
        'tiberiu ichim': 'Eau de Web', 'david ichim': 'kitconcept GmbH',
        'nilesh gulia': 'Eau de Web', 'claudia ifrim': 'Eau de Web',
        'paul roeland': 'CCC', 'kim nguyen': 'Six Feet Up', 't. kim nguyen': 'Six Feet Up',
        'maik derstappen': 'Derico', 'stefan antonelli': 'Kombinat',
        'jens klein': 'Klein & Partner KG', 'johannes raggam': 'Independent',
        'asko soukka': 'University of Jyväskylä', 'kim paulissen': 'KU Leuven',
        'morganna giovanelli': 'Independent', 'leon sólon da silva': 'Independent',
        'luciano ramalho': 'Thoughtworks', 'alexandre b a villares': 'Independent',
        'renan de assis': 'Independent', 'ana dulce': 'Independent',
        'dante alvarez': 'kitconcept GmbH', 'rohit kumar': 'kitconcept GmbH',
        'andre da silva mesquita': 'Independent', 'talita rossari': 'Independent',
        'teodor voicu': 'Eau de Web', 'franco pellegrini': 'Nuclia', 'oshane bailey': 'Independent'
    }
    return org_mapping, manual_mappings

def get_org_for_trainer(name, org_mapping, manual_mappings):
    name_lower = name.lower().strip()
    if name_lower in manual_mappings: return manual_mappings[name_lower]
    for key, org in manual_mappings.items():
        if key in name_lower or name_lower in key: return org
    return "Independent"

def fetch_2024_trainings(org_mapping, manual_mappings):
    url = "https://2024.ploneconf.org/++api++/en/schedule/training"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        items = resp.json().get('items', [])
        trainings = []
        for item in items:
            title = item.get('title')
            presenters = [p.get('title') for p in item.get('presenters', [])]
            orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in presenters])))
            trainings.append({'Title': title, 'Trainer(s)': "; ".join(presenters), 'Organisation': "; ".join(orgs)})
        return trainings
    except: return []

def fetch_2023_trainings(org_mapping, manual_mappings):
    url = "https://2023.ploneconf.org/++api++/training"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200: return []
        items = resp.json().get('items', [])
        trainings = []
        for item in items:
            title = item.get('title')
            desc = item.get('description', '')
            match = re.search(r"Trainer[s]?\s+([\w\s,]+)$", desc, re.IGNORECASE)
            presenters = [p.strip() for p in re.split(r",|and", match.group(1))] if match else []
            orgs = sorted(list(set([get_org_for_trainer(p, org_mapping, manual_mappings) for p in presenters])))
            trainings.append({'Title': title, 'Trainer(s)': "; ".join(presenters), 'Organisation': "; ".join(orgs)})
        return trainings
    except: return []

def main():
    org_mapping, manual_mappings = load_known_organisations()
    os.makedirs('data/community-contributions', exist_ok=True)
    # The data for 2020-2022 was manually recovered from archived schedules in the current session
    for year, fetcher in {2024: fetch_2024_trainings, 2023: fetch_2023_trainings}.items():
        trainings = fetcher(org_mapping, manual_mappings)
        if trainings:
            with open(f'data/community-contributions/{year}-plone-conference-trainings.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Title', 'Trainer(s)', 'Organisation'])
                writer.writeheader()
                writer.writerows(trainings)
            print(f"Created {year}-plone-conference-trainings.csv")

if __name__ == "__main__": main()
