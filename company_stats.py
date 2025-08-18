#!/usr/bin/env python3
"""
Company Statistics Aggregator for Plone GitHub Statistics

Reads the output from plone_stats.py and aggregates statistics by company
using the mapping defined in company_mapping.txt
"""

import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import glob
import os
import sys


def load_company_mapping(mapping_file='company_mapping.txt'):
    """Load company mapping from text file."""
    company_mapping = {}
    
    if not os.path.exists(mapping_file):
        print(f"Warning: {mapping_file} not found. All contributors will be marked as 'Independent'")
        return company_mapping
    
    with open(mapping_file, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                company, contributors = line.split(':', 1)
                contributor_list = [c.strip() for c in contributors.split(',')]
                for contributor in contributor_list:
                    company_mapping[contributor] = company
    
    print(f"Loaded mapping for {len(company_mapping)} contributors across {len(set(company_mapping.values()))} companies")
    return company_mapping


def get_latest_stats_file():
    """Find the most recent plone contributors CSV file."""
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


def aggregate_company_stats(stats_df, company_mapping):
    """Aggregate individual contributor stats by company."""
    company_stats = defaultdict(lambda: {
        'total_commits': 0,
        'total_pull_requests': 0,
        'contributors': set(),
        'repositories': set(),
        'first_contribution': None,
        'last_contribution': None
    })
    
    for _, row in stats_df.iterrows():
        username = row['username']
        company = company_mapping.get(username, 'Independent')
        
        # Aggregate stats
        company_stats[company]['total_commits'] += row['total_commits']
        company_stats[company]['total_pull_requests'] += row['total_pull_requests']
        company_stats[company]['contributors'].add(username)
        
        # Add repositories (split comma-separated string)
        if pd.notna(row['repositories']) and row['repositories']:
            repos = [r.strip() for r in row['repositories'].split(',')]
            company_stats[company]['repositories'].update(repos)
        
        # Track date ranges
        if pd.notna(row['first_contribution']):
            first_date = pd.to_datetime(row['first_contribution'])
            if (company_stats[company]['first_contribution'] is None or 
                first_date < company_stats[company]['first_contribution']):
                company_stats[company]['first_contribution'] = first_date
        
        if pd.notna(row['last_contribution']):
            last_date = pd.to_datetime(row['last_contribution'])
            if (company_stats[company]['last_contribution'] is None or 
                last_date > company_stats[company]['last_contribution']):
                company_stats[company]['last_contribution'] = last_date
    
    return company_stats


def create_company_dataframe(company_stats):
    """Convert company stats to DataFrame."""
    data = []
    
    for company, stats in company_stats.items():
        data.append({
            'company': company,
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


def save_company_report(df, filename=None, date_range=None):
    """Save company statistics to CSV file."""
    if filename is None:
        if date_range:
            filename = f'{date_range}-plone-company-contributors'
        else:
            filename = 'plone-company-contributors'
    
    # Save to CSV
    csv_file = f'{filename}.csv'
    df.to_csv(csv_file, index=False)
    print(f"Company report saved to {csv_file}")
    
    return csv_file


def main():
    """Main function to generate company statistics."""
    print("Plone Company Statistics Aggregator")
    print("=" * 40)
    
    # Load company mapping
    company_mapping = load_company_mapping()
    
    # Find and load latest stats file
    stats_file = get_latest_stats_file()
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
    
    # Aggregate by company
    company_stats = aggregate_company_stats(stats_df, company_mapping)
    
    # Create DataFrame
    company_df = create_company_dataframe(company_stats)
    
    # Display top companies
    print("\n" + "=" * 50)
    print("TOP COMPANIES BY COMMITS:")
    print(company_df[['company', 'total_commits', 'total_pull_requests', 'contributors_count', 'repositories_count']])
    
    # Save report with date range in filename
    csv_file = save_company_report(company_df, date_range=date_range)
    
    print(f"\nProcessed {len(company_df)} companies")
    print(f"Total mapped contributors: {sum(len(set(company_mapping[k] for k in company_mapping if company_mapping[k] == company)) for company in set(company_mapping.values()))}")


if __name__ == "__main__":
    main()