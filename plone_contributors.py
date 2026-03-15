#!/usr/bin/env python3
"""
Plone GitHub Statistics Extractor

Extracts commit and pull request statistics from the Plone GitHub organization.
Aggregates data per contributor including:
- Number of commits per person on the default branch (main/master) - filtered by commit date
- Number of merged pull requests per person (filtered by merge date, excludes open or closed/rejected PRs)
- Repository contributions

Important: Only commits that made it to the default branch are counted. This includes:
- Direct commits to the default branch
- Commits merged via pull requests

Commits on feature branches that were never merged are NOT counted.

Note: This script uses the direct GitHub commits API (/repos/{org}/{repo}/commits)
with the 'sha' parameter set to the default branch, rather than the statistics API,
to ensure accurate and up-to-date commit counts without caching issues.
"""

import os
import time
import json
import requests
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any
import pandas as pd
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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
        self.session = self._create_session_with_retries()
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

    def _create_session_with_retries(self):
        """Create a requests session with automatic retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,  # Total number of retries
            backoff_factor=2,  # Wait 1, 2, 4, 8, 16 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only retry safe methods
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _safe_request(self, method, url, params=None, max_retries=3):
        """Make a safe HTTP request with error handling and retries."""
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, params=params, timeout=30)
                return response
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError) as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                if attempt < max_retries - 1:
                    print(f"  Connection error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}")
                    print(f"  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"  Failed after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                print(f"  Unexpected error: {e}")
                return None
        return None
        
    def get_organization_repos(self) -> List[Dict[str, Any]]:
        """Fetch all repositories from the Plone organization."""
        print(f"Fetching repositories from {self.org} organization...")
        repos = []
        page = 1

        while True:
            url = f'https://api.github.com/orgs/{self.org}/repos'
            params = {'page': page, 'per_page': 100, 'sort': 'updated'}

            response = self._safe_request('GET', url, params=params)
            if response is None:
                print(f"Failed to fetch repositories page {page}")
                break
            
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
    
    def get_repository_contributors_list(self, repo_name: str) -> List[str]:
        """Get list of contributor usernames for a specific repository."""
        print(f"Fetching contributors list for {repo_name}...")

        contributors = []
        page = 1

        while True:
            url = f'https://api.github.com/repos/{self.org}/{repo_name}/contributors'
            params = {'page': page, 'per_page': 100}

            response = self._safe_request('GET', url, params=params)

            if response is None:
                print(f"Failed to fetch contributors for {repo_name} after retries")
                break

            if response.status_code != 200:
                print(f"Error fetching contributors for {repo_name}: {response.status_code}")
                break

            data = response.json()
            if not data:
                break

            # Exclude bots and extract usernames
            for contributor in data:
                if contributor.get('type') == 'User':
                    contributors.append(contributor['login'])

            if len(data) < 100:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        print(f"Found {len(contributors)} contributors for {repo_name}")
        return contributors

    def get_repository_default_branch(self, repo_name: str) -> str:
        """Get the default branch for a repository."""
        url = f'https://api.github.com/repos/{self.org}/{repo_name}'

        try:
            response = self.session.get(url)
            if response.status_code == 200:
                repo_data = response.json()
                return repo_data.get('default_branch', 'main')
        except Exception as e:
            print(f"Error getting default branch for {repo_name}: {e}")

        return 'main'  # Default fallback

    def get_commits_for_user(self, repo_name: str, username: str, default_branch: str) -> int:
        """Get number of commits for a user in the specified date range on the default branch only."""
        url = f'https://api.github.com/repos/{self.org}/{repo_name}/commits'

        params = {
            'author': username,
            'sha': default_branch,  # Only count commits on default branch (main/master)
            'since': self.start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'until': self.end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'per_page': 100
        }

        total_commits = 0
        page = 1
        first_commit_date = None
        last_commit_date = None

        try:
            while True:
                params['page'] = page
                response = self._safe_request('GET', url, params=params)

                if response is None:
                    print(f"  Failed to fetch commits for {username} after retries")
                    break

                if response.status_code != 200:
                    break

                commits = response.json()
                if not commits:
                    break

                total_commits += len(commits)

                # Track first and last commit dates
                for commit in commits:
                    if commit.get('commit', {}).get('author', {}).get('date'):
                        commit_date = datetime.fromisoformat(
                            commit['commit']['author']['date'].replace('Z', '+00:00')
                        ).replace(tzinfo=None)

                        if first_commit_date is None or commit_date < first_commit_date:
                            first_commit_date = commit_date
                        if last_commit_date is None or commit_date > last_commit_date:
                            last_commit_date = commit_date

                # Check if there are more pages
                if 'Link' not in response.headers or 'rel="next"' not in response.headers['Link']:
                    break

                page += 1
                time.sleep(0.5)  # Rate limiting

            # Update contributor data if commits found
            if total_commits > 0:
                if first_commit_date:
                    if (self.contributors_data[username]['first_contribution'] is None or
                        first_commit_date < self.contributors_data[username]['first_contribution']):
                        self.contributors_data[username]['first_contribution'] = first_commit_date

                if last_commit_date:
                    if (self.contributors_data[username]['last_contribution'] is None or
                        last_commit_date > self.contributors_data[username]['last_contribution']):
                        self.contributors_data[username]['last_contribution'] = last_commit_date

            return total_commits
        except Exception as e:
            print(f"Error fetching commits for {username} in {repo_name}: {e}")
            return 0
    
    def get_repository_pull_requests(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get merged pull requests for a repository."""
        print(f"Fetching merged pull requests for {repo_name}...")

        prs = []
        page = 1

        while True:
            url = f'https://api.github.com/repos/{self.org}/{repo_name}/pulls'
            params = {
                'state': 'closed',  # Fetch closed PRs (includes both merged and rejected)
                'page': page,
                'per_page': 100,
                'sort': 'updated',
                'direction': 'desc'
            }

            response = self._safe_request('GET', url, params=params)

            if response is None:
                print(f"Failed to fetch PRs for {repo_name} after retries")
                break

            if response.status_code != 200:
                print(f"Error fetching PRs for {repo_name}: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
            
            # Filter PRs by date range (using merged_at date for consistency with commit counting)
            filtered_prs = []
            for pr in data:
                # Only consider merged PRs and filter by merge date
                if pr.get('merged_at'):
                    merged_date = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')).replace(tzinfo=None)
                    if self.start_date <= merged_date <= self.end_date:
                        filtered_prs.append(pr)
            
            prs.extend(filtered_prs)
            page += 1

            # If we're getting PRs with merge dates older than our date range, we can stop
            # Check merged PRs only
            merged_prs_in_page = [pr for pr in data if pr.get('merged_at')]
            if merged_prs_in_page and all(
                datetime.fromisoformat(pr.get('merged_at', '1970-01-01T00:00:00Z').replace('Z', '+00:00')).replace(tzinfo=None) < self.start_date
                for pr in merged_prs_in_page
            ):
                break
                
        print(f"Fetched {len(prs)} pull requests for {repo_name}")
        return prs
    
    def process_commits(self, repo_name: str, contributors: List[str], default_branch: str):
        """Process commit statistics for contributors in a repository."""
        print(f"Processing commits for {len(contributors)} contributors in {repo_name} (branch: {default_branch})...")

        processed = 0
        for i, username in enumerate(contributors, 1):
            commit_count = self.get_commits_for_user(repo_name, username, default_branch)

            if commit_count > 0:
                self.contributors_data[username]['commits'] += commit_count
                self.contributors_data[username]['repositories'].add(repo_name)
                processed += 1
                if processed % 5 == 0 or commit_count > 10:
                    print(f"  [{i}/{len(contributors)}] {username}: {commit_count} commits")

            # Show progress every 10 contributors
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(contributors)} contributors checked")

            time.sleep(0.3)  # Rate limiting

        print(f"  Completed: {processed} contributors with commits on {default_branch} branch in date range")
    
    def process_pull_requests(self, repo_name: str, prs: List[Dict[str, Any]]):
        """Process merged pull request statistics for a repository."""
        try:
            merged_count = 0
            for pr in prs:
                # Only count merged PRs (filter out closed but not merged PRs)
                if pr.get('merged_at') is None:
                    continue

                if pr['user'] and pr['user']['type'] != 'Bot':
                    username = pr['user']['login']
                    self.contributors_data[username]['pull_requests'] += 1
                    self.contributors_data[username]['repositories'].add(repo_name)
                    merged_count += 1

            print(f"Processed {merged_count} merged PRs for {repo_name}")
        except Exception as e:
            print(f"Error processing PRs for {repo_name}: {e}")
    
    def save_progress(self, filename: str):
        """Save current progress to a checkpoint file."""
        df = self.generate_report()
        checkpoint_file = f"{filename}_checkpoint.csv"
        df.to_csv(checkpoint_file, index=False)
        print(f"Progress saved to {checkpoint_file}")

    def extract_all_stats(self, max_repos: int = None, save_every: int = 50):
        """Extract statistics from all repositories in the organization."""
        print("Starting statistics extraction...")

        repos = self.get_organization_repos()

        if max_repos:
            repos = repos[:max_repos]
            print(f"Processing first {max_repos} repositories")

        for i, repo in enumerate(repos, 1):
            repo_name = repo['name']
            print(f"\n{'='*60}")
            print(f"Processing repository {i}/{len(repos)}: {repo_name}")
            print(f"{'='*60}")

            try:
                # Skip archived repositories
                if repo.get('archived', False):
                    print(f"Skipping archived repository: {repo_name}")
                    continue

                # Get default branch for this repository
                default_branch = repo.get('default_branch', 'main')
                print(f"Default branch: {default_branch}")

                # Get list of contributors
                contributors = self.get_repository_contributors_list(repo_name)
                if contributors:
                    self.process_commits(repo_name, contributors, default_branch)

                # Get pull requests
                prs = self.get_repository_pull_requests(repo_name)
                if prs:
                    self.process_pull_requests(repo_name, prs)

            except Exception as e:
                print(f"ERROR: Failed to process repository {repo_name}: {e}")
                print(f"Continuing with next repository...")

            # Save progress checkpoint every N repositories
            if save_every and i % save_every == 0:
                print(f"\n*** Saving checkpoint at repository {i}/{len(repos)} ***")
                self.save_progress(f"data/{self.start_date.year}-plone-contributors")

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
        """Save the report to CSV file."""
        if filename is None:
            filename = 'plone-contributors'
        
        # Save to CSV
        csv_file = f'data/{filename}.csv'
        df.to_csv(csv_file, index=False)
        print(f"Report saved to {csv_file}")
        
        return csv_file

def parse_arguments():
    """Parse command line arguments for date range configuration."""
    parser = argparse.ArgumentParser(
        description="Extract GitHub statistics from the Plone organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plone_stats.py                    # Current year (default)
  python plone_stats.py --year 2024       # All of 2024
  python plone_stats.py --start-date 2024-01-01 --end-date 2024-06-30  # First half of 2024
  python plone_stats.py --start-date 2023-01-01 --end-date 2024-12-31  # Two year span
        """
    )
    
    parser.add_argument(
        '--year', 
        type=int, 
        help='Extract stats for a specific year (e.g., 2024)'
    )
    
    parser.add_argument(
        '--start-date', 
        type=str, 
        help='Start date in YYYY-MM-DD format (e.g., 2024-01-01)'
    )
    
    parser.add_argument(
        '--end-date', 
        type=str, 
        help='End date in YYYY-MM-DD format (e.g., 2024-12-31)'
    )
    
    parser.add_argument(
        '--token',
        type=str,
        help='GitHub token (if not using .env file)'
    )
    
    return parser.parse_args()


def validate_and_parse_dates(args):
    """Validate and parse date arguments."""
    start_date = None
    end_date = None
    
    if args.year:
        # Use specified year
        start_date = datetime(args.year, 1, 1)
        end_date = datetime(args.year, 12, 31, 23, 59, 59)
        print(f"Using year: {args.year}")
    elif args.start_date or args.end_date:
        # Use custom date range
        if args.start_date:
            try:
                start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD")
        
        if args.end_date:
            try:
                end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)  # End of day
            except ValueError:
                raise ValueError(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD")
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")
    else:
        # Default to current year
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1)
        end_date = datetime(current_year, 12, 31, 23, 59, 59)
        print(f"Using default year: {current_year}")
    
    return start_date, end_date


def main():
    """Main function to run the statistics extraction."""
    print("Plone GitHub Statistics Extractor")
    print("=" * 40)
    
    # Parse command line arguments
    args = parse_arguments()
    
    try:
        # Parse and validate dates
        start_date, end_date = validate_and_parse_dates(args)
        
        # Create extractor with specified date range
        extractor = PloneStatsExtractor(
            token=args.token,
            start_date=start_date,
            end_date=end_date
        )

        # Generate filename with date range
        if start_date and end_date:
            if start_date.year == end_date.year:
                filename = f'{start_date.year}-plone-contributors'
            else:
                filename = f'{start_date.year}-{end_date.year}-plone-contributors'
        else:
            filename = None  # Use default filename

        try:
            # Extract statistics from all repositories
            extractor.extract_all_stats()

        except KeyboardInterrupt:
            print("\n\nExtraction interrupted by user. Saving progress...")
        except Exception as e:
            print(f"\n\nUnexpected error during extraction: {e}")
            print("Saving current progress...")

        # Always generate and save report (even if extraction was interrupted)
        df = extractor.generate_report()

        print("\n" + "=" * 50)
        print("TOP 10 CONTRIBUTORS BY PRs:")
        print(df.sort_values('total_pull_requests', ascending=False).head(10)[['username', 'total_commits', 'total_pull_requests', 'repositories_count']])

        csv_file = extractor.save_report(df, filename)

        print(f"\nStatistics extraction completed!")
        print(f"Total repositories found: {len(extractor.repositories)}")
        print(f"Total contributors found: {len(df)}")

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    main()