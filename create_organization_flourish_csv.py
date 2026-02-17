#!/usr/bin/env python3

import csv
import os
from collections import defaultdict

# Years to analyze
years = range(2015, 2026)  # 2015-2025

# Store all organisation data
all_orgs = defaultdict(dict)

# Read all organisation contributor files
for year in years:
    filename = f"{year}-plone-organisation-contributors.csv"
    if os.path.exists(filename):
        print(f"Reading {filename}")
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['organisation']
                commits = int(row['total_commits'])
                all_orgs[org][year] = commits

# Find organisations with significant activity
top_orgs = {}
for org, yearly_data in all_orgs.items():
    total_commits = sum(yearly_data.values())
    years_active = len(yearly_data)

    if total_commits >= 25 or (total_commits >= 10 and years_active >= 3):
        top_orgs[org] = {
            'total_commits': total_commits,
            'years_active': years_active,
            'yearly_data': yearly_data
        }

# Sort by total commits
sorted_orgs = sorted(top_orgs.items(), key=lambda x: x[1]['total_commits'], reverse=True)

print(f"\nFound {len(sorted_orgs)} organisations")
for org, data in sorted_orgs[:20]:
    print(f"{org}: {data['total_commits']} commits across {data['years_active']} years")

# Categorize organisations by type
def get_org_type(org):
    academic = [
        'Uni. Jyvaskylä', 'TU Dresden', 'Uni. Hospital Dresden',
        'Academy of FA Vienna', 'FHNW', 'TU Munich',
    ]
    individual = ['Independent', 'PY76']
    community = []

    if org in academic:
        return 'Academic'
    if org in individual:
        return 'Individual'
    if org in community:
        return 'Community'
    return 'Corporate'

# Normalise org names for Flourish (lowercase, no spaces)
def normalise_org_name(org):
    name_map = {
        'kitconcept GmbH': 'kitconcept',
        'PY76': 'py76',
        'der Freitag': 'freitag',
        'Klein & Partner': 'kleinundpartner',
        'Uni. Jyvaskylä': 'university-jyvaskylä',
        'Uni. Hospital Dresden': 'university-hospital-dresden',
        'TU Dresden': 'university-tu-dresden',
        'TU Munich': 'university-tu-munich',
        'Academy of FA Vienna': 'academy-of-fine-arts-vienna',
        'Eau de Web': 'eau-de-web',
        'CMS Communications': 'cms-communications',
        'Abstract IT': 'abstract-it',
    }
    if org in name_map:
        return name_map[org]
    return org.lower().replace(' ', '-').replace('.', '-')


# Create Flourish CSV
output_file = 'plone-organizations-bar-chart-race-flourish.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)

    # Header
    header = ['Organization', 'Region', 'Image URL'] + [str(year) for year in years]
    writer.writerow(header)

    # Write data for top organisations
    for org, data in sorted_orgs:
        org_type = get_org_type(org)
        display_name = normalise_org_name(org)
        row = [display_name, org_type, '']

        for year in years:
            if year in data['yearly_data']:
                commits = data['yearly_data'][year]
                row.append(commits if commits > 0 else '')
            else:
                row.append('')

        writer.writerow(row)

print(f"\nCreated {output_file} with {len(sorted_orgs)} organisations")
