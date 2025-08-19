#!/usr/bin/env python3
"""
Organisation Statistics Aggregator for Plone GitHub Statistics

Reads the output from plone_stats.py and aggregates statistics by organisation
using the mapping defined in organisation_mapping.txt
"""

import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import glob
import os
import sys
import argparse


def load_organisation_mapping(mapping_file='organisation_mapping.txt'):
    """Load organisation mapping from text file."""
    organisation_mapping = {}
    
    if not os.path.exists(mapping_file):
        print(f"Warning: {mapping_file} not found. All contributors will be marked as 'Independent'")
        return organisation_mapping
    
    with open(mapping_file, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                organisation, contributors = line.split(':', 1)
                contributor_list = [c.strip() for c in contributors.split(',')]
                for contributor in contributor_list:
                    organisation_mapping[contributor] = organisation
    
    print(f"Loaded mapping for {len(organisation_mapping)} contributors across {len(set(organisation_mapping.values()))} organisations")
    return organisation_mapping


def get_stats_file(year=None):
    """Find the plone contributors CSV file for a specific year or the latest one."""
    if year:
        # Look for specific year file
        year_file = f'{year}-plone-contributors.csv'
        if os.path.exists(year_file):
            print(f"Using stats file: {year_file}")
            return year_file
        else:
            print(f"File {year_file} not found")
            return None
    
    # Look for new format (year-first) and legacy format
    csv_files = glob.glob('????-plone-contributors.csv')  # New format: 2024-plone-contributors.csv
    csv_files.extend(glob.glob('????-????-plone-contributors.csv'))  # New format: 2023-2024-plone-contributors.csv
    csv_files.extend(glob.glob('plone_contributors_*.csv'))  # Legacy format
    if 'plone-contributors.csv' in glob.glob('plone-contributors.csv'):
        csv_files.append('plone-contributors.csv')
    if 'plone_contributors.csv' in glob.glob('plone_contributors.csv'):
        csv_files.append('plone_contributors.csv')
    
    if not csv_files:
        print("No plone contributors CSV files found. Run 'python plone_stats.py' first.")
        return None
    
    # Sort by modification time, most recent first
    csv_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = csv_files[0]
    print(f"Using latest stats file: {latest_file}")
    return latest_file


def extract_date_range_from_filename(filename):
    """Extract year or date range from the input filename for output naming."""
    import re
    
    # Extract just the filename without path
    basename = os.path.basename(filename)
    
    # Check for new format: year pattern (e.g., 2024-plone-contributors.csv)
    year_match = re.search(r'(\d{4})-plone-contributors\.csv', basename)
    if year_match:
        return year_match.group(1)
    
    # Check for new format: year range pattern (e.g., 2023-2024-plone-contributors.csv)
    range_match = re.search(r'(\d{4}-\d{4})-plone-contributors\.csv', basename)
    if range_match:
        return range_match.group(1)
    
    # Check for legacy format: year pattern (e.g., plone_contributors_2024.csv)
    legacy_year_match = re.search(r'plone_contributors_(\d{4})\.csv', basename)
    if legacy_year_match:
        return legacy_year_match.group(1)
    
    # Check for legacy format: year range pattern (e.g., plone_contributors_2023_2024.csv)
    legacy_range_match = re.search(r'plone_contributors_(\d{4}_\d{4})\.csv', basename)
    if legacy_range_match:
        return legacy_range_match.group(1).replace('_', '-')
    
    # Default files - no year suffix
    if basename in ['plone-contributors.csv', 'plone_contributors.csv']:
        return None
    
    return None


def aggregate_organisation_stats(stats_df, organisation_mapping):
    """Aggregate individual contributor stats by organisation."""
    organisation_stats = defaultdict(lambda: {
        'total_commits': 0,
        'total_pull_requests': 0,
        'contributors': set(),
        'repositories': set(),
        'first_contribution': None,
        'last_contribution': None
    })
    
    for _, row in stats_df.iterrows():
        username = row['username']
        organisation = organisation_mapping.get(username, 'Independent')
        
        # Aggregate stats
        organisation_stats[organisation]['total_commits'] += row['total_commits']
        organisation_stats[organisation]['total_pull_requests'] += row['total_pull_requests']
        organisation_stats[organisation]['contributors'].add(username)
        
        # Add repositories (split comma-separated string)
        if pd.notna(row['repositories']) and row['repositories']:
            repos = [r.strip() for r in row['repositories'].split(',')]
            organisation_stats[organisation]['repositories'].update(repos)
        
        # Track date ranges
        if pd.notna(row['first_contribution']):
            first_date = pd.to_datetime(row['first_contribution'])
            if (organisation_stats[organisation]['first_contribution'] is None or 
                first_date < organisation_stats[organisation]['first_contribution']):
                organisation_stats[organisation]['first_contribution'] = first_date
        
        if pd.notna(row['last_contribution']):
            last_date = pd.to_datetime(row['last_contribution'])
            if (organisation_stats[organisation]['last_contribution'] is None or 
                last_date > organisation_stats[organisation]['last_contribution']):
                organisation_stats[organisation]['last_contribution'] = last_date
    
    return organisation_stats


def create_organisation_dataframe(organisation_stats):
    """Convert organisation stats to DataFrame."""
    data = []
    
    for organisation, stats in organisation_stats.items():
        data.append({
            'organisation': organisation,
            'total_commits': stats['total_commits'],
            'total_pull_requests': stats['total_pull_requests'],
            'contributors_count': len(stats['contributors']),
            'contributors': ', '.join(sorted(stats['contributors'])),
            'repositories_count': len(stats['repositories']),
            'repositories': ', '.join(sorted(stats['repositories'])),
            'first_contribution': stats['first_contribution'],
            'last_contribution': stats['last_contribution']
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('total_commits', ascending=False)
    return df


def save_organisation_report(df, filename=None, date_range=None):
    """Save organisation statistics to CSV file."""
    if filename is None:
        if date_range:
            filename = f'{date_range}-plone-organisation-contributors'
        else:
            filename = 'plone-organisation-contributors'
    
    # Save to CSV
    csv_file = f'{filename}.csv'
    df.to_csv(csv_file, index=False)
    print(f"Organisation report saved to {csv_file}")
    
    return csv_file


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate organisation statistics from individual contributor data')
    parser.add_argument('--year', type=int, help='Generate statistics for specific year (e.g., 2024)')
    return parser.parse_args()

def main():
    """Main function to generate organisation statistics."""
    print("Plone Organisation Statistics Aggregator")
    print("=" * 42)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load organisation mapping
    organisation_mapping = load_organisation_mapping()
    
    # Find and load stats file (specific year or latest)
    stats_file = get_stats_file(args.year)
    if not stats_file:
        sys.exit(1)
    
    # Extract date range from filename for output naming
    date_range = extract_date_range_from_filename(stats_file)
    
    # Load individual contributor stats
    try:
        stats_df = pd.read_csv(stats_file)
        print(f"Loaded {len(stats_df)} contributor records")
    except Exception as e:
        print(f"Error loading {stats_file}: {e}")
        sys.exit(1)
    
    # Aggregate by organisation
    organisation_stats = aggregate_organisation_stats(stats_df, organisation_mapping)
    
    # Create DataFrame
    organisation_df = create_organisation_dataframe(organisation_stats)
    
    # Display top organisations
    print("\n" + "=" * 50)
    print("TOP ORGANISATIONS BY COMMITS:")
    print(organisation_df[['organisation', 'total_commits', 'total_pull_requests', 'contributors_count', 'repositories_count']])
    
    # Save report with date range in filename
    csv_file = save_organisation_report(organisation_df, date_range=date_range)
    
    print(f"\nProcessed {len(organisation_df)} organisations")
    print(f"Total mapped contributors: {sum(len(set(organisation_mapping[k] for k in organisation_mapping if organisation_mapping[k] == organisation)) for organisation in set(organisation_mapping.values()))}")


if __name__ == "__main__":
    main()