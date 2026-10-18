#!/usr/bin/env python3
"""
Plone PLIP Statistics Extractor

Extracts PLIPs (Plone Improvement Proposals) from the repositories where they are made:
- Products.CMFPlone
- volto
- plone.restapi
- aurora

Writes the PLIPs per author and per PLIP. Uses GITHUB_TOKEN from the environment or the .env file,
and stops without writing anything if a request fails.
"""

import argparse
import os
import sys

import pandas as pd
import requests
from dotenv import load_dotenv

from scripts.lib import paths
from scripts.lib.github_api import GitHubAPIError, github_get

# The repositories where a PLIP can live. Aurora, the new UI after Volto, started
# as an idea in Volto; its first PLIPs were transferred there from Volto. Other
# repositories use the PLIP label for issues related to a PLIP, which are not PLIPs.
REPOSITORIES = [
    ('plone', 'Products.CMFPlone'),
    ('plone', 'volto'),
    ('plone', 'plone.restapi'),
    ('plone', 'aurora'),
]
PLIP_LABEL = '03 type: feature (plip)'
PER_PAGE = 100


def create_session():
    """A session with the GitHub token from the environment or the .env file, if there is one."""
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')
    session = requests.Session()
    session.headers['Accept'] = 'application/vnd.github.v3+json'
    if token and token != 'your_token_here':
        session.headers['Authorization'] = f'token {token}'
        print("Using authenticated requests")
    else:
        print("No GitHub token found, using unauthenticated requests (60 per hour)")
    return session


def get_plips_from_repo(session, repo_owner, repo_name):
    """All PLIPs, open and closed, of a repository; raises GitHubAPIError if a request fails."""
    print(f"Fetching PLIPs from {repo_owner}/{repo_name}...")
    plips = []
    page = 1
    while True:
        params = {
            'state': 'all',
            'labels': PLIP_LABEL,
            'page': page,
            'per_page': PER_PAGE,
            'sort': 'created',
            'direction': 'desc',
        }
        issues = github_get(session, f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues',
                            params=params).json()
        for issue in issues:
            # The issues endpoint also lists pull requests
            if 'pull_request' in issue:
                continue
            plips.append({
                'number': issue['number'],
                'title': issue['title'],
                'author': issue['user']['login'],
                'state': issue['state'],
                'created_at': issue['created_at'],
                'updated_at': issue['updated_at'],
                'closed_at': issue.get('closed_at'),
                'repository': f"{repo_owner}/{repo_name}",
                'html_url': issue['html_url'],
            })
        print(f"  Fetched page {page}: {len(issues)} issues")
        if len(issues) < PER_PAGE:
            break
        page += 1

    print(f"  Found {len(plips)} PLIPs in {repo_owner}/{repo_name}")
    return plips


def get_all_plips(session):
    """All PLIPs of the repositories in REPOSITORIES."""
    all_plips = []
    for repo_owner, repo_name in REPOSITORIES:
        all_plips.extend(get_plips_from_repo(session, repo_owner, repo_name))
    return all_plips


def analyze_plip_statistics(plips):
    """Analyze PLIP statistics and create CSV output"""
    if not plips:
        print("No PLIPs found.")
        return None, None
    
    # Convert to DataFrame
    df = pd.DataFrame(plips)
    
    # Convert dates
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['updated_at'] = pd.to_datetime(df['updated_at'])
    df['closed_at'] = pd.to_datetime(df['closed_at'])
    
    print(f"\nPLIP STATISTICS ANALYSIS")
    print("=" * 50)
    
    # Overall statistics
    total_plips = len(df)
    open_plips = len(df[df['state'] == 'open'])
    closed_plips = len(df[df['state'] == 'closed'])
    unique_authors = df['author'].nunique()
    
    print(f"Total PLIPs: {total_plips}")
    print(f"Open PLIPs: {open_plips}")
    print(f"Closed PLIPs: {closed_plips}")
    print(f"Unique authors: {unique_authors}")
    print()
    
    # PLIPs by repository
    print("PLIPs BY REPOSITORY:")
    print("-" * 25)
    repo_stats = df['repository'].value_counts()
    for repo, count in repo_stats.items():
        open_count = len(df[(df['repository'] == repo) & (df['state'] == 'open')])
        closed_count = len(df[(df['repository'] == repo) & (df['state'] == 'closed')])
        repo_short = repo.split('/')[1]
        print(f"  {repo_short:<25} {count:>3} total ({open_count} open, {closed_count} closed)")
    print()
    
    # Create contributor statistics (similar to plone_stats.py format)
    author_stats = df.groupby('author').agg({
        'number': 'count',  # total PLIPs
        'state': lambda x: (x == 'open').sum(),  # open PLIPs
        'repository': lambda x: list(set(x))  # unique repositories
    }).rename(columns={
        'number': 'total_plips',
        'state': 'open_plips'
    })
    
    author_stats['closed_plips'] = df.groupby('author')['state'].apply(lambda x: (x == 'closed').sum())
    author_stats['repositories_count'] = author_stats['repository'].apply(len)
    author_stats['repositories'] = author_stats['repository'].apply(lambda x: ', '.join(sorted(x)))
    
    # Calculate date ranges for each author
    date_stats = df.groupby('author').agg({
        'created_at': ['min', 'max']
    })
    date_stats.columns = ['first_plip', 'last_plip']
    
    # Combine stats
    final_stats = author_stats.join(date_stats)
    final_stats = final_stats.sort_values('total_plips', ascending=False)
    
    # Display top contributors
    print("TOP PLIP AUTHORS:")
    print("-" * 20)
    print(f"{'Author':<20} {'Total':<6} {'Open':<5} {'Closed':<7} {'Repos':<5}")
    print("-" * 50)
    
    for author, row in final_stats.head(15).iterrows():
        print(f"{author:<20} {row['total_plips']:<6} {row['open_plips']:<5} {row['closed_plips']:<7} {row['repositories_count']:<5}")
    
    return df, final_stats

def save_plip_statistics(df, contributor_stats):
    """Save PLIP statistics to CSV files"""
    if df is None or contributor_stats is None:
        return
    
    # Save aggregated PLIP statistics by author (main CSV file)
    plips_filename = paths.PLIPS
    
    # Prepare contributor stats for CSV (this becomes the main plips file)
    contrib_export = contributor_stats.copy()
    contrib_export.reset_index(inplace=True)
    contrib_export['first_plip'] = contrib_export['first_plip'].dt.strftime('%Y-%m-%d')
    contrib_export['last_plip'] = contrib_export['last_plip'].dt.strftime('%Y-%m-%d')
    
    # Rename columns to match the expected format (like plone-contributors.csv)
    contrib_export = contrib_export.rename(columns={
        'author': 'username',
        'total_plips': 'total_plips', 
        'open_plips': 'open_plips',
        'closed_plips': 'closed_plips',
        'repositories_count': 'repositories_count',
        'repositories': 'repositories',
        'first_plip': 'first_plip',
        'last_plip': 'last_plip'
    })
    
    # Reorder columns to match plone-contributors.csv format
    column_order = [
        'username', 'total_plips', 'open_plips', 'closed_plips', 
        'repositories_count', 'repositories', 'first_plip', 'last_plip'
    ]
    contrib_export = contrib_export[column_order]
    
    contrib_export.to_csv(plips_filename, index=False)
    print(f"\nPLIP statistics saved to: {plips_filename}")
    print(f"Total contributors: {len(contrib_export)}")
    
    # Save individual PLIPs for detailed analysis (optional detailed file)
    detailed_filename = paths.PLIPS_DETAILED
    
    # Prepare DataFrame for detailed CSV export
    export_df = df.copy()
    export_df = export_df.sort_values('created_at', ascending=False)
    
    # Format dates for CSV
    export_df['created_at'] = export_df['created_at'].dt.strftime('%Y-%m-%d')
    export_df['updated_at'] = export_df['updated_at'].dt.strftime('%Y-%m-%d')
    export_df['closed_at'] = export_df['closed_at'].dt.strftime('%Y-%m-%d')
    
    # Replace NaT with empty string for open PLIPs
    export_df['closed_at'] = export_df['closed_at'].replace('NaT', '')
    
    export_df.to_csv(detailed_filename, index=False)
    print(f"Detailed PLIP data saved to: {detailed_filename}")
    print(f"Total PLIP records: {len(export_df)}")

def main():
    """Main function"""
    print("Plone PLIP Statistics Extractor")
    print("=" * 35)

    try:
        plips = get_all_plips(create_session())
    except (KeyboardInterrupt, GitHubAPIError, requests.exceptions.RequestException) as e:
        # Never write incomplete data
        reason = 'interrupted by user' if isinstance(e, KeyboardInterrupt) else f'{type(e).__name__}: {e}'
        print(f"\nExtraction stopped ({reason}). The data files were not written.")
        return 1

    if not plips:
        print("No PLIPs found.")
        return 1

    plips_df, contributor_stats = analyze_plip_statistics(plips)
    save_plip_statistics(plips_df, contributor_stats)

    print("\nPLIP statistics extraction completed!")
    print(f"Found {len(plips)} PLIPs from {len(set(p['repository'] for p in plips))} repositories")
    return 0


if __name__ == "__main__":
    # No options; --help says what the script does
    argparse.ArgumentParser(description=__doc__.strip().splitlines()[0]).parse_args()
    sys.exit(main())
