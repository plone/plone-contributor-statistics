#!/usr/bin/env python3
"""
PLIP (Plone Improvement Proposal) Statistics Tracker

Counts PLIPs created by individual contributors across the three main repositories:
- Products.CMFPlone
- volto  
- plone.restapi

PLIPs are identified by the label "03 type: feature (plip)"
"""

import os
import requests
import pandas as pd
import argparse
from datetime import datetime
from collections import defaultdict
import time

def get_github_token():
    """Get GitHub token from environment or .env file"""
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

def get_plips_for_repo(repo_owner, repo_name, token, start_date=None, end_date=None):
    """
    Get all PLIPs (issues with '03 type: feature (plip)' label) from a repository
    """
    print(f"Fetching PLIPs from {repo_owner}/{repo_name}...")
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Get all issues first, then filter
    plips = []
    page = 1
    per_page = 100
    
    while True:
        # Get issues from repository
        url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues'
        params = {
            'state': 'all',
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
                # Skip pull requests (they also appear in issues endpoint)
                if 'pull_request' in issue:
                    continue
                
                # Date filtering
                issue_created = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                
                if start_date and issue_created < datetime.fromisoformat(f"{start_date}T00:00:00+00:00"):
                    continue
                if end_date and issue_created > datetime.fromisoformat(f"{end_date}T23:59:59+00:00"):
                    continue
                
                plip_data = {
                    'number': issue['number'],
                    'title': issue['title'],
                    'author': issue['user']['login'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'closed_at': issue.get('closed_at'),
                    'html_url': issue['html_url'],
                    'repository': f"{repo_owner}/{repo_name}"
                }
                plips.append(plip_data)
            
            print(f"  Fetched page {page}: {len(issues)} issues")
            
            # Check if we have more pages
            if len(issues) < per_page:
                break
                
            page += 1
            
            # Rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error fetching PLIPs: {e}")
            if hasattr(e, 'response') and e.response.status_code == 401:
                print(f"  ❌ Authentication failed. Please check your GitHub token.")
            break
    
    print(f"  ✅ Found {len(plips)} PLIPs in {repo_owner}/{repo_name}")
    return plips

def analyze_plip_statistics(plips_data, start_date=None, end_date=None):
    """Analyze PLIP statistics and generate reports"""
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(plips_data)
    
    if df.empty:
        print("No PLIPs found")
        return
    
    # Convert dates
    df['created_at'] = pd.to_datetime(df['created_at'])
    if 'closed_at' in df.columns:
        df['closed_at'] = pd.to_datetime(df['closed_at'])
    
    # Filter by date range if specified
    if start_date:
        df = df[df['created_at'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['created_at'] <= pd.to_datetime(end_date)]
    
    date_range_str = ""
    if start_date and end_date:
        date_range_str = f" ({start_date} to {end_date})"
    elif start_date:
        date_range_str = f" (from {start_date})"
    elif end_date:
        date_range_str = f" (until {end_date})"
    
    print(f"\nPLIP STATISTICS ANALYSIS{date_range_str}")
    print("=" * 60)
    
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
        print(f"  {repo:<30} {count:>3} total ({open_count} open, {closed_count} closed)")
    print()
    
    # Top PLIP authors
    print("TOP PLIP AUTHORS:")
    print("-" * 20)
    author_stats = df.groupby('author').agg({
        'number': 'count',
        'state': lambda x: (x == 'open').sum(),
        'repository': lambda x: x.nunique()
    }).rename(columns={
        'number': 'total_plips',
        'state': 'open_plips', 
        'repository': 'repositories'
    })
    
    author_stats['closed_plips'] = df.groupby('author')['state'].apply(lambda x: (x == 'closed').sum())
    author_stats = author_stats.sort_values('total_plips', ascending=False)
    
    print(f"{'Author':<20} {'Total':<6} {'Open':<5} {'Closed':<7} {'Repos':<5}")
    print("-" * 50)
    
    for author, row in author_stats.head(20).iterrows():
        print(f"{author:<20} {row['total_plips']:<6} {row['open_plips']:<5} {row['closed_plips']:<7} {row['repositories']:<5}")
    
    print()
    
    # PLIPs by year
    if not df.empty:
        print("PLIPs BY YEAR:")
        print("-" * 15)
        df['year'] = df['created_at'].dt.year
        yearly_stats = df.groupby('year').agg({
            'number': 'count',
            'state': lambda x: (x == 'open').sum()
        }).rename(columns={'number': 'total', 'state': 'open'})
        yearly_stats['closed'] = df.groupby('year')['state'].apply(lambda x: (x == 'closed').sum())
        
        for year, row in yearly_stats.sort_index().iterrows():
            print(f"  {year}: {row['total']} total ({row['open']} open, {row['closed']} closed)")
        print()
    
    # Recent PLIPs (last 10)
    print("RECENT PLIPs (Last 10):")
    print("-" * 25)
    recent_plips = df.sort_values('created_at', ascending=False).head(10)
    
    for _, plip in recent_plips.iterrows():
        created_date = plip['created_at'].strftime('%Y-%m-%d')
        state_emoji = "🟢" if plip['state'] == 'open' else "🔴"
        repo_short = plip['repository'].split('/')[1]
        print(f"  {state_emoji} #{plip['number']:<4} {created_date} {plip['author']:<15} [{repo_short}] {plip['title'][:50]}...")
    
    return df

def save_plip_statistics(plips_data, start_date=None, end_date=None):
    """Save PLIP statistics to CSV file"""
    
    if not plips_data:
        print("No PLIP data to save")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(plips_data)
    
    # Filter by date range if specified
    if start_date:
        df = df[pd.to_datetime(df['created_at']) >= pd.to_datetime(start_date)]
    if end_date:
        df = df[pd.to_datetime(df['created_at']) <= pd.to_datetime(end_date)]
    
    # Generate filename
    if start_date and end_date:
        filename = f"{start_date}-to-{end_date}-plone-plips.csv"
    elif start_date:
        filename = f"{start_date}-plone-plips.csv"
    elif end_date:
        filename = f"until-{end_date}-plone-plips.csv"
    else:
        current_year = datetime.now().year
        filename = f"{current_year}-plone-plips.csv"
    
    # Sort by creation date (newest first)
    df = df.sort_values('created_at', ascending=False)
    
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"\nPLIP data saved to: {filename}")
    print(f"Total records: {len(df)}")
    
    return filename

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract PLIP statistics from Plone repositories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plip_stats.py                           # All PLIPs
  python plip_stats.py --year 2024               # PLIPs from 2024
  python plip_stats.py --start-date 2023-01-01   # PLIPs from 2023 onwards
  python plip_stats.py --author tisto             # PLIPs by specific author
  python plip_stats.py --repo volto               # PLIPs from specific repo only
        """
    )
    
    parser.add_argument('--year', type=int,
                        help='Extract PLIPs from specific year (e.g., 2024)')
    parser.add_argument('--start-date', type=str,
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str,
                        help='End date in YYYY-MM-DD format')
    parser.add_argument('--author', type=str,
                        help='Filter PLIPs by specific author')
    parser.add_argument('--repo', type=str, choices=['cmfplone', 'volto', 'restapi'],
                        help='Extract PLIPs from specific repository only')
    
    return parser.parse_args()

def validate_and_parse_dates(args):
    """Validate and parse date arguments"""
    start_date = None
    end_date = None
    
    if args.year:
        start_date = f"{args.year}-01-01"
        end_date = f"{args.year}-12-31"
    else:
        if args.start_date:
            try:
                datetime.strptime(args.start_date, '%Y-%m-%d')
                start_date = args.start_date
            except ValueError:
                print("❌ Invalid start date format. Use YYYY-MM-DD")
                return None, None
        
        if args.end_date:
            try:
                datetime.strptime(args.end_date, '%Y-%m-%d')
                end_date = args.end_date
            except ValueError:
                print("❌ Invalid end date format. Use YYYY-MM-DD")
                return None, None
    
    return start_date, end_date

def main():
    """Main function"""
    print("Plone PLIP Statistics Extractor")
    print("=" * 35)
    
    # Parse arguments
    args = parse_arguments()
    
    # Get GitHub token
    token = get_github_token()
    if not token:
        return
    
    # Validate dates
    start_date, end_date = validate_and_parse_dates(args)
    if args.year and (start_date is None or end_date is None):
        return
    
    # Define repositories where PLIPs can be created
    repositories = []
    
    if not args.repo or args.repo == 'cmfplone':
        repositories.append(('plone', 'Products.CMFPlone'))
    if not args.repo or args.repo == 'volto':
        repositories.append(('plone', 'volto'))
    if not args.repo or args.repo == 'restapi':
        repositories.append(('plone', 'plone.restapi'))
    
    # Fetch PLIPs from all repositories
    all_plips = []
    
    for repo_owner, repo_name in repositories:
        plips = get_plips_for_repo(repo_owner, repo_name, token, start_date, end_date)
        all_plips.extend(plips)
    
    if not all_plips:
        print("No PLIPs found")
        return
    
    # Filter by author if specified
    if args.author:
        original_count = len(all_plips)
        all_plips = [plip for plip in all_plips if plip['author'].lower() == args.author.lower()]
        print(f"\nFiltered to author '{args.author}': {len(all_plips)} of {original_count} PLIPs")
    
    # Analyze statistics
    df = analyze_plip_statistics(all_plips, start_date, end_date)
    
    # Save to CSV
    save_plip_statistics(all_plips, start_date, end_date)
    
    print("\n✅ PLIP statistics extraction completed!")

if __name__ == "__main__":
    main()