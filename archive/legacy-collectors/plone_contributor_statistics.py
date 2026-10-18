#!/usr/bin/env python3
"""
Fresh Plone GitHub Statistics Extractor
"""

import os
import time
import json
import requests
from datetime import datetime
from collections import defaultdict
import pandas as pd
from dotenv import load_dotenv

# Force reload environment
if 'GITHUB_TOKEN' in os.environ:
    del os.environ['GITHUB_TOKEN']
load_dotenv(override=True)

def main():
    print("Plone GitHub Statistics Extractor")
    print("=" * 40)
    
    # Get token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("No GITHUB_TOKEN found!")
        return
        
    print(f"Token loaded: {len(token)} characters")
    
    # Setup session
    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}'})
    
    # Test access
    print("Testing API access...")
    test_response = session.get('https://api.github.com/user')
    if test_response.status_code == 200:
        user_data = test_response.json()
        print(f"✓ Authenticated as: {user_data['login']}")
    else:
        print(f"✗ Authentication failed: {test_response.status_code}")
        return
    
    # Get Plone repositories
    print("\nFetching Plone repositories...")
    repos = []
    page = 1
    
    while True:
        url = 'https://api.github.com/orgs/plone/repos'
        params = {'page': page, 'per_page': 100, 'sort': 'updated'}
        
        response = session.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching repos: {response.status_code}")
            break
            
        data = response.json()
        if not data:
            break
            
        repos.extend(data)
        print(f"  Page {page}: {len(data)} repositories")
        page += 1
        
        # Limit for initial run
        if page > 3:  # First 300 repos
            break
            
    print(f"Total repositories found: {len(repos)}")
    
    # Process contributors for top repositories
    contributors_data = defaultdict(lambda: {
        'commits': 0,
        'pull_requests': 0,
        'repositories': set()
    })
    
    # Process first 10 repositories with most activity
    active_repos = sorted(repos, key=lambda x: x['stargazers_count'], reverse=True)[:10]
    
    for i, repo in enumerate(active_repos, 1):
        repo_name = repo['name']
        print(f"\nProcessing {i}/10: {repo_name} ({repo['stargazers_count']} stars)")
        
        # Get contributors
        url = f'https://api.github.com/repos/plone/{repo_name}/stats/contributors'
        
        for attempt in range(3):
            response = session.get(url)
            
            if response.status_code == 200:
                contributors = response.json()
                if contributors:
                    for contrib in contributors:
                        if contrib and 'author' in contrib and contrib['author']:
                            author = contrib['author']
                            if author.get('type') != 'Bot':
                                username = author['login']
                                contributors_data[username]['commits'] += contrib['total']
                                contributors_data[username]['repositories'].add(repo_name)
                    print(f"  ✓ {len(contributors)} contributors processed")
                break
            elif response.status_code == 202:
                print(f"  Statistics computing, waiting...")
                time.sleep(3)
            else:
                print(f"  ✗ Error: {response.status_code}")
                break
        
        # Get pull requests
        url = f'https://api.github.com/repos/plone/{repo_name}/pulls'
        params = {'state': 'all', 'per_page': 100}
        
        response = session.get(url, params=params)
        if response.status_code == 200:
            prs = response.json()
            for pr in prs:
                if pr['user'] and pr['user'].get('type') != 'Bot':
                    username = pr['user']['login']
                    contributors_data[username]['pull_requests'] += 1
                    contributors_data[username]['repositories'].add(repo_name)
            print(f"  ✓ {len(prs)} pull requests processed")
        
        time.sleep(1)  # Rate limiting
    
    # Generate report
    print(f"\nGenerating report...")
    data = []
    for username, stats in contributors_data.items():
        data.append({
            'username': username,
            'total_commits': stats['commits'],
            'total_pull_requests': stats['pull_requests'],
            'repositories_count': len(stats['repositories']),
            'repositories': ', '.join(sorted(stats['repositories']))
        })
    
    if data:
        df = pd.DataFrame(data)
        df = df.sort_values('total_commits', ascending=False)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f'plone_stats_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        
        print("\n" + "=" * 60)
        print("TOP 15 CONTRIBUTORS BY COMMITS:")
        print(df.head(15)[['username', 'total_commits', 'total_pull_requests', 'repositories_count']])
        
        print(f"\nResults saved to: {csv_file}")
        print(f"Total contributors: {len(df)}")
        print(f"Repositories analyzed: {len(active_repos)}")
    else:
        print("No data collected")

if __name__ == "__main__":
    main()