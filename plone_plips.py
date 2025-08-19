#!/usr/bin/env python3
"""
Plone PLIP Statistics Extractor

Extracts PLIPs (Plone Improvement Proposals) from all three main repositories:
- Products.CMFPlone
- volto  
- plone.restapi

Creates CSV statistics similar to plone_stats.py but for PLIPs specifically.
"""

import os
import requests
import time
import pandas as pd
from datetime import datetime
from collections import defaultdict

def get_github_token():
    """Get GitHub token from environment or .env file"""
    # For now, skip token to test without authentication
    return None
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    
    if not token or token == 'your_token_here':
        print("❌ GitHub token not found. Please set GITHUB_TOKEN in .env file")
        return None
    
    return token

def get_plips_from_repo(repo_owner, repo_name, token):
    """Get all PLIPs (both open and closed) from a specific repository"""
    print(f"Fetching PLIPs from {repo_owner}/{repo_name}...")
    
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    
    if token:
        headers['Authorization'] = f'token {token}'
    
    plips = []
    page = 1
    per_page = 100
    
    while True:
        url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues'
        params = {
            'state': 'all',  # Get both open and closed
            'labels': '03 type: feature (plip)',
            'page': page,
            'per_page': per_page,
            'sort': 'created',
            'direction': 'desc'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            issues = response.json()
            
            if not issues:
                break
                
            for issue in issues:
                # Skip pull requests
                if 'pull_request' in issue:
                    continue
                
                plip_data = {
                    'number': issue['number'],
                    'title': issue['title'],
                    'author': issue['user']['login'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'closed_at': issue.get('closed_at'),
                    'repository': f"{repo_owner}/{repo_name}",
                    'html_url': issue['html_url']
                }
                plips.append(plip_data)
            
            print(f"  Fetched page {page}: {len(issues)} issues")
            
            if len(issues) < per_page:
                break
                
            page += 1
            # Rate limiting - longer delay without token
            sleep_time = 0.5 if not token else 0.1
            time.sleep(sleep_time)
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error: {e}")
            break
    
    print(f"  ✅ Found {len(plips)} PLIPs in {repo_owner}/{repo_name}")
    return plips

def get_all_plips():
    """Get all PLIPs from all three main repositories"""
    token = get_github_token()
    
    if token:
        print("Using authenticated requests")
    else:
        print("Using unauthenticated requests (limited rate)")
    
    # Define the three main repositories where PLIPs are created
    repositories = [
        ('plone', 'Products.CMFPlone'),
        ('plone', 'volto'),
        ('plone', 'plone.restapi')
    ]
    
    all_plips = []
    
    for repo_owner, repo_name in repositories:
        plips = get_plips_from_repo(repo_owner, repo_name, token)
        all_plips.extend(plips)
    
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
    plips_filename = "plone-plips.csv"
    
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
    detailed_filename = "plone-plips-detailed.csv"
    
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
    
    # Get all PLIPs from all repositories
    plips = get_all_plips()
    
    if not plips:
        print("No PLIPs found.")
        return
    
    # Analyze statistics
    plips_df, contributor_stats = analyze_plip_statistics(plips)
    
    # Save to CSV files
    save_plip_statistics(plips_df, contributor_stats)
    
    print(f"\n✅ PLIP statistics extraction completed!")
    print(f"Found {len(plips)} PLIPs from {len(set(p['repository'] for p in plips))} repositories")

if __name__ == "__main__":
    main()