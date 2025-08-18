#!/usr/bin/env python3
"""
Plone GitHub Statistics Extractor

Extracts commit and pull request statistics from the Plone GitHub organization.
Aggregates data per contributor including:
- Number of commits per person
- Number of pull requests per person  
- Repository contributions
"""

import os
import time
import json
import requests
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any
import pandas as pd
from dotenv import load_dotenv

class PloneStatsExtractor:
    def __init__(self, token: str = None, start_date: datetime = None, end_date: datetime = None):
        # Force load from .env file directly
        if token is None:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
        
        load_dotenv(override=True)
        
        self.token = token
        self.org = 'plone'
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({'Authorization': f'token {self.token}'})
            print(f"Using GitHub token (length: {len(self.token)})")
        else:
            print("No GitHub token found!")
        
        # Set date range - default to current year if not provided
        current_year = datetime.now().year
        self.start_date = start_date or datetime(current_year, 1, 1)
        self.end_date = end_date or datetime(current_year, 12, 31, 23, 59, 59)
        
        print(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        self.repositories = []
        self.contributors_data = defaultdict(lambda: {
            'commits': 0,
            'pull_requests': 0,
            'repositories': set(),
            'first_contribution': None,
            'last_contribution': None
        })
        
    def get_organization_repos(self) -> List[Dict[str, Any]]:
        """Fetch all repositories from the Plone organization."""
        print(f"Fetching repositories from {self.org} organization...")
        repos = []
        page = 1
        
        while True:
            url = f'https://api.github.com/orgs/{self.org}/repos'
            params = {'page': page, 'per_page': 100, 'sort': 'updated'}
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 401:
                print(f"Authentication failed (401). GitHub token is required for organization data.")
                print(f"Get a token at: https://github.com/settings/tokens")
                print(f"Add it to .env file as: GITHUB_TOKEN=your_token")
                return []
            elif response.status_code == 403:
                print(f"Access forbidden (403). Token may lack 'read:org' scope or org is private.")
                print(f"For public repos only, trying individual repo access...")
                # Try to get some popular Plone repos directly
                popular_repos = ['Plone', 'plone.api', 'Products.CMFPlone', 'plone.app.contenttypes', 'plone.restapi']
                repos = []
                for repo_name in popular_repos:
                    repo_url = f'https://api.github.com/repos/{self.org}/{repo_name}'
                    repo_resp = self.session.get(repo_url)
                    if repo_resp.status_code == 200:
                        repos.append(repo_resp.json())
                        print(f"  Added repository: {repo_name}")
                    else:
                        print(f"  Could not access: {repo_name} ({repo_resp.status_code})")
                return repos
            elif response.status_code != 200:
                print(f"Error fetching repos: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
                
            repos.extend(data)
            print(f"Fetched {len(data)} repositories (page {page})")
            page += 1
            
        self.repositories = repos
        print(f"Total repositories found: {len(repos)}")
        return repos
    
    def get_repository_contributors(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get contributors statistics for a specific repository."""
        print(f"Fetching contributors for {repo_name}...")
        
        url = f'https://api.github.com/repos/{self.org}/{repo_name}/stats/contributors'
        
        # Statistics API may return 202 initially, need to retry
        max_retries = 3
        for attempt in range(max_retries):
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 202:
                print(f"Statistics being computed for {repo_name}, waiting...")
                time.sleep(2)
            else:
                print(f"Error fetching contributors for {repo_name}: {response.status_code}")
                return []
                
        print(f"Failed to get contributors for {repo_name} after {max_retries} attempts")
        return []
    
    def get_repository_pull_requests(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get all pull requests for a repository."""
        print(f"Fetching pull requests for {repo_name}...")
        
        prs = []
        page = 1
        
        while True:
            url = f'https://api.github.com/repos/{self.org}/{repo_name}/pulls'
            params = {
                'state': 'all',
                'page': page,
                'per_page': 100,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching PRs for {repo_name}: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
            
            # Filter PRs by date range
            filtered_prs = []
            for pr in data:
                pr_date = None
                if pr.get('created_at'):
                    pr_date = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)
                elif pr.get('updated_at'):
                    pr_date = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if pr_date and self.start_date <= pr_date <= self.end_date:
                    filtered_prs.append(pr)
            
            prs.extend(filtered_prs)
            page += 1
            
            # If we're getting PRs older than our date range, we can stop
            if data and all(datetime.fromisoformat(pr.get('updated_at', '1970-01-01T00:00:00Z').replace('Z', '+00:00')).replace(tzinfo=None) < self.start_date for pr in data):
                break
                
        print(f"Fetched {len(prs)} pull requests for {repo_name}")
        return prs
    
    def process_contributors(self, repo_name: str, contributors: List[Dict[str, Any]]):
        """Process contributor statistics for a repository."""
        for contrib in contributors:
            if not contrib or 'author' not in contrib:
                continue
                
            author = contrib['author']
            if not author or author['type'] == 'Bot':
                continue
                
            username = author['login']
            
            # Filter commits by date range
            commits_in_range = 0
            weeks = contrib.get('weeks', [])
            first_contribution = None
            last_contribution = None
            
            for week in weeks:
                if week['c'] > 0:  # commits in this week
                    week_date = datetime.fromtimestamp(week['w'])
                    
                    # Only count commits within our date range
                    if self.start_date <= week_date <= self.end_date:
                        commits_in_range += week['c']
                        
                        # Track first and last contributions within date range
                        if first_contribution is None or week_date < first_contribution:
                            first_contribution = week_date
                            
                        if last_contribution is None or week_date > last_contribution:
                            last_contribution = week_date
            
            # Only add contributor data if they have commits in the date range
            if commits_in_range > 0:
                self.contributors_data[username]['commits'] += commits_in_range
                self.contributors_data[username]['repositories'].add(repo_name)
                
                # Update overall first and last contributions
                if (self.contributors_data[username]['first_contribution'] is None or
                    (first_contribution and first_contribution < self.contributors_data[username]['first_contribution'])):
                    self.contributors_data[username]['first_contribution'] = first_contribution
                    
                if (self.contributors_data[username]['last_contribution'] is None or
                    (last_contribution and last_contribution > self.contributors_data[username]['last_contribution'])):
                    self.contributors_data[username]['last_contribution'] = last_contribution
    
    def process_pull_requests(self, repo_name: str, prs: List[Dict[str, Any]]):
        """Process pull request statistics for a repository."""
        for pr in prs:
            if pr['user'] and pr['user']['type'] != 'Bot':
                username = pr['user']['login']
                self.contributors_data[username]['pull_requests'] += 1
                self.contributors_data[username]['repositories'].add(repo_name)
    
    def extract_all_stats(self, max_repos: int = None):
        """Extract statistics from all repositories in the organization."""
        print("Starting statistics extraction...")
        
        repos = self.get_organization_repos()
        
        if max_repos:
            repos = repos[:max_repos]
            print(f"Processing first {max_repos} repositories")
        
        for i, repo in enumerate(repos, 1):
            repo_name = repo['name']
            print(f"\nProcessing repository {i}/{len(repos)}: {repo_name}")
            
            # Skip archived repositories if desired
            if repo.get('archived', False):
                print(f"Skipping archived repository: {repo_name}")
                continue
            
            # Get contributors
            contributors = self.get_repository_contributors(repo_name)
            if contributors:
                self.process_contributors(repo_name, contributors)
            
            # Get pull requests
            prs = self.get_repository_pull_requests(repo_name)
            if prs:
                self.process_pull_requests(repo_name, prs)
            
            # Rate limiting - be nice to GitHub API
            time.sleep(1)
    
    def generate_report(self) -> pd.DataFrame:
        """Generate a comprehensive report of the statistics."""
        data = []
        
        for username, stats in self.contributors_data.items():
            data.append({
                'username': username,
                'total_commits': stats['commits'],
                'total_pull_requests': stats['pull_requests'],
                'repositories_count': len(stats['repositories']),
                'repositories': ', '.join(sorted(stats['repositories'])),
                'first_contribution': stats['first_contribution'].strftime('%Y-%m-%d') if stats['first_contribution'] else None,
                'last_contribution': stats['last_contribution'].strftime('%Y-%m-%d') if stats['last_contribution'] else None
            })
        
        if not data:
            print("No data collected. Creating empty report.")
            df = pd.DataFrame(columns=['username', 'total_commits', 'total_pull_requests', 'repositories_count', 'repositories', 'first_contribution', 'last_contribution'])
        else:
            df = pd.DataFrame(data)
            df = df.sort_values('total_commits', ascending=False)
        return df
    
    def save_report(self, df: pd.DataFrame, filename: str = None):
        """Save the report to CSV and JSON files."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'plone_stats_{timestamp}'
        
        # Save to CSV
        csv_file = f'{filename}.csv'
        df.to_csv(csv_file, index=False)
        print(f"Report saved to {csv_file}")
        
        # Save to JSON
        json_file = f'{filename}.json'
        with open(json_file, 'w') as f:
            json.dump(self.contributors_data, f, indent=2, default=str)
        print(f"Raw data saved to {json_file}")
        
        return csv_file, json_file

def main():
    """Main function to run the statistics extraction."""
    print("Plone GitHub Statistics Extractor")
    print("=" * 40)
    
    # Create extractor with current year as default date range (let it load token from .env)
    extractor = PloneStatsExtractor()
    
    # Extract statistics from all repositories
    extractor.extract_all_stats()
    
    # Generate and save report
    df = extractor.generate_report()
    
    print("\n" + "=" * 50)
    print("TOP 10 CONTRIBUTORS BY COMMITS:")
    print(df.head(10)[['username', 'total_commits', 'total_pull_requests', 'repositories_count']])
    
    csv_file, json_file = extractor.save_report(df)
    
    print(f"\nStatistics extraction completed!")
    print(f"Total repositories found: {len(extractor.repositories)}")
    print(f"Total contributors found: {len(df)}")
    print(f"Total repositories processed: {len(extractor.repositories)}")

if __name__ == "__main__":
    main()