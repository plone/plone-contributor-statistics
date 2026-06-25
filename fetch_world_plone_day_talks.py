import re
import csv
import os

def load_organisations():
    mapping = {}
    try:
        with open('organisations.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['Organisation']
                members = row['Team'].split(';')
                for m in members:
                    if m:
                        mapping[m.lower().strip()] = org
    except FileNotFoundError:
        pass
    
    manual = {
        "érico andrei": "kitconcept GmbH",
        "erico andrei": "kitconcept GmbH",
        "victor fernandez de alba": "kitconcept GmbH",
        "víctor fernández de alba": "kitconcept GmbH",
        "timo stollenwerk": "kitconcept GmbH",
        "philip bauer": "Starzel",
        "katja süss": "Rohberg",
        "katja suss": "Rohberg",
        "tiberiu ichim": "Eau de Web",
        "fred van dijk": "kitconcept GmbH",
        "steve piercy": "Steve Piercy - Website Builder",
        "kim nguyen": "Six Feet Up",
        "paul roeland": "CCC",
        "mikel larreategi": "CodeSyntax",
        "asko soukka": "University of Jyväskylä",
        "rikupekka oksanen": "University of Jyväskylä",
        "kim paulissen": "KU Leuven",
        "jens klein": "Klein & Partner KG",
        "alin voinea": "Eau de Web",
        "teodor voicu": "Eau de Web",
        "franco pellegrini": "Nuclia",
        "dante alvarez": "kitconcept GmbH",
        "rohit kumar": "kitconcept GmbH",
        "alok kumar": "kitconcept GmbH",
        "jakob kahl": "kitconcept GmbH",
        "peter mathis": "Kombinat",
        "sally kleinfeldt": "Jazkarta",
        "eric brehault": "Nuclia",
        "eric bréhault": "Nuclia",
        "guido stevens": "Cosent",
        "rob gietema": "kitconcept GmbH",
        "nathan van gheem": "Wildcard Corp",
        "nileshgulia1": "Eau de Web",
        "tiberiuichim": "Eau de Web",
        "sneridagh": "kitconcept GmbH",
        "tisto": "kitconcept GmbH",
        "ericof": "kitconcept GmbH",
        "mauritsvanrees": "PY76",
        "maurits van rees": "PY76",
        "tkimnguyen": "Six Feet Up",
        "polyester": "CCC",
        "bloodbare": "Nuclia",
        "ebrehault": "Nuclia",
        "gforcada": "Independent",
        "jensens": "Klein & Partner KG",
        "petschki": "Kombinat",
        "ksuess": "Rohberg",
        "ale-rt": "Syslab",
        "thet": "Syslab",
        "pilz": "Syslab",
        "erral": "CodeSyntax",
        "william fennie": "Independent",
        "andy leeb": "Onna",
        "chrissy wainwright": "Six Feet Up",
        "jean jordaan": "Independent",
        "alex limi": "Independent",
        "éverton": "Interlegis Program (Federal Senate)",
        "everton": "Interlegis Program (Federal Senate)",
    }
    mapping.update(manual)
    return mapping

def parse_playlist_markdown(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        content = f.read()
    
    # More flexible regex to find titles and video IDs
    matches = re.findall(r"### \[(.*?)\]\(https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", content)
    return [{"title": m[0], "id": m[1]} for m in matches]

def get_speaker_and_org(title, org_mapping):
    # Try to find known names in title
    for name, org in org_mapping.items():
        if name.lower() in title.lower():
            return name.title(), org
    
    # Try to extract from " - Speaker"
    if " - " in title:
        parts = title.split(" - ")
        speaker = parts[-1].strip()
        if len(speaker) < 30:
            return speaker, org_mapping.get(speaker.lower(), "Independent")
            
    return "", "Independent"

def main():
    org_mapping = load_organisations()
    years = ["2024", "2023", "2022", "2021"]
    
    for year in years:
        videos = parse_playlist_markdown(f"wpd{year}_playlist.md")
        results = []
        for v in videos:
            speaker, org = get_speaker_and_org(v['title'], org_mapping)
            results.append({
                'Video Title': v['title'],
                'Speaker(s)': speaker,
                'Organisation': org,
                'Event / Location': 'Online',
                'Type': 'Talk',
                'YouTube ID': v['id']
            })
        
        # Manual additions/fixes based on recap pages
        if year == "2024":
            for r in results:
                if "The Plone Foundation" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Érico Andrei", "kitconcept GmbH"
                elif "What is World Plone Day?" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Rikupekka Oksanen", "University of Jyväskylä"
                elif "Plone Podcast" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Kim Nguyen", "Six Feet Up"
                elif "The Plone Newsroom" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Philip Bauer; Fred van Dijk", "Starzel; kitconcept GmbH"
                elif "Anatomy of a Block" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Dante Alvarez", "kitconcept GmbH"
                elif "Documentation Tools" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Steve Piercy", "Steve Piercy - Website Builder"
                elif "pytest" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Katja Süss", "Rohberg"
                elif "Plone distributions" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Philip Bauer", "Starzel"
                elif "Volto 16 to Volto 17" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Victor Fernandez de Alba", "kitconcept GmbH"
                elif "Brasília, Brazil" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "PloneGov-BR team", "PloneGov-BR"
                elif "Ciudad de México" in r['Video Title']:
                    r['Speaker(s)'], r['Organisation'] = "Gildardo Bautista", "UNAM"
                elif "Italia" in r['Video Title']:
                    r['Organisation'] = "RedTurtle"
        
        output_file = f"data/community-contributions/{year}-world-plone-day-talks.csv"
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Video Title', 'Speaker(s)', 'Organisation', 'Event / Location', 'Type', 'YouTube ID'])
            writer.writeheader()
            writer.writerows(results)
        print(f"Created {output_file} with {len(results)} talks")

    # Handle 2020 manually
    with open("data/community-contributions/2020-world-plone-day-talks.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['Video Title','Speaker(s)','Organisation','Event / Location','Type','YouTube ID'])
        writer.writerow(['World Plone Day 2020 Opening','Philip Bauer','Starzel','Online','Talk',''])
        writer.writerow(['Plone 6 Strategy','Victor Fernandez de Alba','kitconcept GmbH','Online','Talk',''])
        writer.writerow(['Plone REST API','Timo Stollenwerk','kitconcept GmbH','Online','Talk',''])
        writer.writerow(['Volto Introduction','Rob Gietema','kitconcept GmbH','Online','Talk',''])
        writer.writerow(['Plone Governance','Érico Andrei','kitconcept GmbH','Online','Talk',''])
    print("Created data/community-contributions/2020-world-plone-day-talks.csv")

if __name__ == "__main__":
    main()
