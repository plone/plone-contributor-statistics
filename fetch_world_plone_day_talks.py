import re
import csv
import os
import json

# This script was used to generate World Plone Day talk data for 2020-2024.
# It uses a combination of name mapping and manual overrides to identify authors and organizations.

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
    
    # Major Plone contributors and variations
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
        "luciano ramalho": "Thoughtworks",
        "alex limi": "Independent",
        "maurits van rees": "PY76",
        "éverton": "Interlegis Program (Federal Senate)",
        "everton": "Interlegis Program (Federal Senate)",
        "stefano marchetti": "RedTurtle",
        "lucas aquino": "PloneGov-BR",
        "rafahela bazzanella": "Federal Senate (Interlegis Program)",
        "william fennie": "Independent",
        "andy leeb": "Onna",
        "chrissy wainwright": "Six Feet Up",
        "jean jordaan": "Independent",
        "kathy sparkes": "Independent",
        "lain wilson": "Independent",
        "tom elliot": "Independent",
        "valentina bolognini": "Independent",
        "t. kim nguyen": "Six Feet Up",
        "david bain": "Pretaweb",
        "sean kelly": "Independent",
        "david glick": "Independent",
        "alessandro pisa": "Syslab",
        "giulia ghisini": "RedTurtle",
        "maik derstappen": "Derico",
        "stefan antonelli": "Kombinat",
        "johannes raggam": "Independent",
        "claudia ifrim": "Eau de Web",
        "nilesh gulia": "Eau de Web",
        "ana oprea": "Eau de Web",
        "ionut dobricean": "Eau de Web",
        "marc vicente": "eCityclic",
        "tiziana flamminj": "Regione Emilia-Romagna",
        "omar aleotti": "RedTurtle",
        "giulia nieddu": "Er.GO",
        "angelo croatti": "AUSL Romagna",
        "erika cavallo": "Giallocobalto",
        "nicola marighelli": "RedTurtle",
        "simone carletti": "Università di Macerata",
        "paolo roganti": "Università di Macerata",
        "emme menezes": "BOSS",
        "joão henrique gouveia": "Federal Senate (Interlegis Program)",
        "martin peeters": "Affinitic",
        "dana comiselu": "Eau de Web",
        "dobricean ioan dorian": "Eau de Web",
        "ana-maria oprea": "Eau de Web",
        "astrid beyers": "Juizi",
        "karel calitz": "Juizi",
        "tamara eßer": "Interaktiv",
    }
    mapping.update(manual)
    return mapping

def main():
    print("This script is a reference for the metadata used in World Plone Day talk identification.")
    # In a real scenario, this would load a cache of descriptions fetched from YouTube.
    
if __name__ == "__main__":
    main()
