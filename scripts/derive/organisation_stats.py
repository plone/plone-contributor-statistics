#!/usr/bin/env python3
"""
Organisation Statistics Aggregator for Plone GitHub Statistics

Reads the output from plone_contributors.py and aggregates statistics by organisation
using the affiliations of the registers (curated/mappings/)

The changelog entries of the year (plone_changelogs.py, #71) are shown in a
column of their own, next to commits and pull requests, and never added to
them. The rows and their order stay those of the code work.
"""

import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import glob
import os
import sys
import argparse

from scripts.lib import paths
from scripts.lib.model import UNMAPPED, load_bot_accounts, load_registry
from scripts.lib.tables import by_count


def get_stats_file(year=None):
    """Find the plone contributors CSV file for a specific year or the latest one."""
    if year:
        # Look for specific year file
        year_file = str(paths.contributors_file(year))
        if os.path.exists(year_file):
            print(f"Using stats file: {year_file}")
            return year_file
        else:
            print(f"File {year_file} not found")
            return None

    # Look for new format (year-first) and legacy format
    csv_files = glob.glob(str(paths.CONTRIBUTORS_DIR / '????-plone-contributors.csv'))  # New format: 2024-plone-contributors.csv
    csv_files.extend(glob.glob(str(paths.CONTRIBUTORS_DIR / '????-????-plone-contributors.csv')))  # New format: 2023-2024-plone-contributors.csv
    csv_files.extend(glob.glob(str(paths.CONTRIBUTORS_DIR / 'plone_contributors_*.csv')))  # Legacy format
    csv_files.extend(glob.glob(str(paths.CONTRIBUTORS_DIR / 'plone-contributors.csv')))
    csv_files.extend(glob.glob(str(paths.CONTRIBUTORS_DIR / 'plone_contributors.csv')))
    
    if not csv_files:
        print("No plone contributors CSV files found. Run 'make run-stats YEAR=<year>' first.")
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


def load_changelog_entries(year):
    """The changelog entries per person of the year, or None if the year has no file."""
    path = paths.changelog_entries_file(year)
    if not os.path.exists(path):
        print(f"No changelog entries for {year} ({path}); the column is 0. Run: make run-changelogs")
        return None
    return pd.read_csv(path, keep_default_na=False)


def changelog_entries_by_organisation(changelog_df, organisation_of, bots=frozenset()):
    """{organisation: changelog entries} of the people of each organisation.

    organisation_of(username) gives the organisation name. Names that no
    identity of the registers maps are no login, so they count as UNMAPPED.
    """
    entries = defaultdict(int)
    if changelog_df is None:
        return entries
    for _, row in changelog_df.iterrows():
        username = row['username']
        if username in bots:
            continue
        unmatched = 'unmatched' in str(row['matched_by']).split(';')
        organisation = UNMAPPED if unmatched else organisation_of(username)
        entries[organisation] += int(row['changelog_entries'])
    return entries


def aggregate_organisation_stats(stats_df, organisation_of, bots=None, changelog_df=None):
    """Aggregate individual contributor stats by organisation.

    organisation_of(username) gives the organisation name of a login or
    'person:<id>'. Bot accounts are left out; unmapped contributors go to
    UNMAPPED. The changelog entries go to the organisations that have code
    work in the year; they don't add rows.
    """
    bots = load_bot_accounts() if bots is None else bots
    organisation_stats = defaultdict(lambda: {
        'total_commits': 0,
        'total_pull_requests': 0,
        'changelog_entries': 0,
        'contributors': set(),
        'repositories': set(),
        'first_contribution': None,
        'last_contribution': None
    })
    
    for _, row in stats_df.iterrows():
        username = row['username']
        if username in bots:
            continue
        organisation = organisation_of(username)
        
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

    for organisation, entries in changelog_entries_by_organisation(changelog_df, organisation_of, bots).items():
        if organisation in organisation_stats:
            organisation_stats[organisation]['changelog_entries'] += entries

    return organisation_stats


def create_organisation_dataframe(organisation_stats):
    """Convert organisation stats to DataFrame."""
    data = []
    
    for organisation, stats in organisation_stats.items():
        data.append({
            'organisation': organisation,
            'total_commits': stats['total_commits'],
            'total_pull_requests': stats['total_pull_requests'],
            'changelog_entries': stats['changelog_entries'],
            'contributors_count': len(stats['contributors']),
            'contributors': ', '.join(sorted(stats['contributors'])),
            'repositories_count': len(stats['repositories']),
            'repositories': ', '.join(sorted(stats['repositories'])),
            'first_contribution': stats['first_contribution'],
            'last_contribution': stats['last_contribution']
        })
    
    df = pd.DataFrame(data)
    df = by_count(df, 'total_commits', 'organisation')
    return df


def save_organisation_report(df, filename=None, date_range=None):
    """Save organisation statistics to CSV file."""
    if filename is None:
        if date_range:
            filename = f'{date_range}-plone-organisation-contributors'
        else:
            filename = 'plone-organisation-contributors'
    
    # Save to CSV
    csv_file = paths.ORGANISATION_CONTRIBUTORS_DIR / f'{filename}.csv'
    df.to_csv(csv_file, index=False)
    print(f"Organisation report saved to {csv_file}")
    
    return csv_file


def parse_arguments(argv=None):
    """Parse command line arguments; the year is required, as the organisation of a login depends on it."""
    parser = argparse.ArgumentParser(description='Generate organisation statistics from individual contributor data')
    parser.add_argument('--year', type=int, required=True,
                        help='Year of the statistics (e.g., 2024); the organisation of a login depends on the year')
    return parser.parse_args(argv)

def main():
    """Main function to generate organisation statistics."""
    print("Plone Organisation Statistics Aggregator")
    print("=" * 42)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load the registers
    registry = load_registry()

    def organisation_of(username):
        return registry.organisation_for_username(username, args.year)
    
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
    changelog_df = load_changelog_entries(date_range) if date_range and '-' not in date_range else None
    organisation_stats = aggregate_organisation_stats(stats_df, organisation_of, changelog_df=changelog_df)
    
    # Create DataFrame
    organisation_df = create_organisation_dataframe(organisation_stats)
    
    # Display top organisations
    print("\n" + "=" * 50)
    print("TOP ORGANISATIONS BY COMMITS:")
    print(organisation_df[['organisation', 'total_commits', 'total_pull_requests', 'contributors_count', 'repositories_count']])
    
    # Save report with date range in filename
    csv_file = save_organisation_report(organisation_df, date_range=date_range)
    
    print(f"\nProcessed {len(organisation_df)} organisations")
    print(f"Logins with an organisation in {args.year}: {len(registry.login_organisations(args.year))}")


if __name__ == "__main__":
    main()