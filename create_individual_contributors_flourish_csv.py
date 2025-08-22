#!/usr/bin/env python3

import csv
import os
from collections import defaultdict

# Years to analyze
years = range(2015, 2025)  # Focus on 2015-2024 for better visualization

# Store all contributor data
all_contributors = defaultdict(dict)

# Read all individual contributor files
for year in years:
    filename = f"{year}-plone-contributors.csv"
    if os.path.exists(filename):
        print(f"Reading {filename}")
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row['username']
                commits = int(row['total_commits'])
                all_contributors[username][year] = commits

# Find top contributors (those with significant commits across multiple years)
top_contributors = {}
for username, yearly_data in all_contributors.items():
    total_commits = sum(yearly_data.values())
    years_active = len(yearly_data)
    
    # Only include contributors with significant activity
    # Threshold for individual contributors (higher than organizations)
    if total_commits >= 50 or (total_commits >= 25 and years_active >= 3):
        top_contributors[username] = {
            'total_commits': total_commits,
            'years_active': years_active,
            'yearly_data': yearly_data
        }

# Sort by total commits
sorted_contributors = sorted(top_contributors.items(), key=lambda x: x[1]['total_commits'], reverse=True)

print(f"\nFound {len(sorted_contributors)} top contributors")
for username, data in sorted_contributors[:20]:
    print(f"{username}: {data['total_commits']} commits across {data['years_active']} years")

# Categorize contributors by region (based on known information)
def get_contributor_region(username):
    # Known contributor regions (partial list based on community knowledge)
    regions = {
        'mauritsvanrees': 'Netherlands',
        'vangheem': 'USA',
        'stevepiercy': 'USA',
        'gforcada': 'Spain',
        'petschki': 'Austria',
        'sneridagh': 'Spain',
        'tisto': 'Germany',
        'davilima6': 'Brazil',
        'pbauer': 'Austria',
        'jensens': 'Austria',
        'ale-rt': 'Italy',
        'mamico': 'Italy',
        'ksuess': 'Austria',
        'erral': 'Spain',
        'frapell': 'Argentina',
        'ericof': 'Brazil',
        'claytonc': 'USA',
        'esteele': 'USA',
        'djay': 'Australia',
        'taito': 'Finland',
        'datakurre': 'Finland',
        'gomez': 'Spain',
        'thet': 'Austria',
        'avoinea': 'Romania',
        'naro': 'Romania',
        'giacomos': 'Italy',
        'tiberiuichim': 'Romania',
        'pysailor': 'Germany',
        'zupo': 'Slovenia',
        'iham': 'Finland',
        'miohtama': 'Finland',
        'polyester': 'USA',
        'tkimnguyen': 'USA',
        'rohnsha0': 'India',
        'agitator': 'Germany',
        'do3cc': 'Germany',
        'fredvd': 'Belgium',
        'mikejmets': 'Estonia',
    }
    return regions.get(username, 'Other')

# Create Flourish CSV for individual contributors
with open('plone-individual-contributors-flourish.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    
    # Header
    header = ['Contributor', 'Region', 'Image URL'] + [str(year) for year in years]
    writer.writerow(header)
    
    # Write data for top contributors (limit to top 50 for better visualization)
    for username, data in sorted_contributors[:50]:
        region = get_contributor_region(username)
        row = [username, region, '']  # Basic info
        
        # Add yearly commit data
        for year in years:
            if year in data['yearly_data']:
                commits = data['yearly_data'][year]
                row.append(commits if commits > 0 else '')
            else:
                row.append('')  # Empty for years with no data
        
        writer.writerow(row)

print(f"\nCreated plone-individual-contributors-flourish.csv with {len(sorted_contributors[:50])} contributors")
print("Top contributors included:")
for i, (username, data) in enumerate(sorted_contributors[:50], 1):
    print(f"{i:2d}. {username:25s} - {data['total_commits']:4d} commits")