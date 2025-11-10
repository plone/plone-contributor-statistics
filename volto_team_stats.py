#!/usr/bin/env python3
"""
Generate contributor statistics for Volto team members.
Fetches data from GitHub API for plone/volto repository.
"""

import requests
import csv
import time
import argparse
from datetime import datetime
from collections import defaultdict
import os
from dotenv import load_dotenv

# Force reload environment
if 'GITHUB_TOKEN' in os.environ:
    del os.environ['GITHUB_TOKEN']
load_dotenv(override=True)

# GitHub API configuration
REPO_OWNER = 'plone'
REPO_NAME = 'volto'

# API endpoints
BASE_URL = 'https://api.github.com'

def read_team_members(filename='team-volto.md'):
    """Read team member GitHub usernames from file."""
    with open(filename, 'r') as f:
        usernames = [line.strip() for line in f if line.strip()]
    return usernames

def get_pull_requests(session, username, start_date, end_date):
    """Get number of PRs for a user in the specified date range."""
    url = f'{BASE_URL}/search/issues'
    query = f'repo:{REPO_OWNER}/{REPO_NAME} author:{username} type:pr created:{start_date}..{end_date}'

    params = {
        'q': query,
        'per_page': 1  # We only need the count
    }

    try:
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('total_count', 0)
    except Exception as e:
        print(f"Error fetching PRs for {username}: {e}")
        return 0

def get_commits(session, username, start_date, end_date):
    """Get number of commits for a user in the specified date range."""
    url = f'{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/commits'

    params = {
        'author': username,
        'since': f'{start_date}T00:00:00Z',
        'until': f'{end_date}T23:59:59Z',
        'per_page': 100
    }

    total_commits = 0
    page = 1

    try:
        while True:
            params['page'] = page
            response = session.get(url, params=params)
            response.raise_for_status()

            commits = response.json()
            if not commits:
                break

            total_commits += len(commits)

            # Check if there are more pages
            if 'Link' not in response.headers or 'rel="next"' not in response.headers['Link']:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        return total_commits
    except Exception as e:
        print(f"Error fetching commits for {username}: {e}")
        return 0

def generate_statistics(session, start_date, end_date):
    """Generate statistics for all team members."""
    team_members = read_team_members()
    statistics = []

    print(f"Fetching statistics for {len(team_members)} team members...")
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"Date range: {start_date} to {end_date}\n")

    for i, username in enumerate(team_members, 1):
        print(f"[{i}/{len(team_members)}] Processing {username}...")

        pr_count = get_pull_requests(session, username, start_date, end_date)
        time.sleep(1)  # Rate limiting

        commit_count = get_commits(session, username, start_date, end_date)
        time.sleep(1)  # Rate limiting

        statistics.append({
            'github_username': username,
            'pull_requests': pr_count,
            'commits': commit_count
        })

        print(f"  PRs: {pr_count}, Commits: {commit_count}\n")

    return statistics

def save_to_csv(statistics, filename):
    """Save statistics to CSV file."""
    fieldnames = ['github_username', 'pull_requests', 'commits']

    # Sort by pull_requests in descending order
    sorted_statistics = sorted(statistics, key=lambda x: x['pull_requests'], reverse=True)

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_statistics)

    print(f"\nStatistics saved to {filename}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Extract Volto team member statistics from GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python volto_team_stats.py                    # Current year (default)
  python volto_team_stats.py --year 2024       # All of 2024
  python volto_team_stats.py --start-date 2024-01-01 --end-date 2024-06-30  # First half of 2024
  python volto_team_stats.py --start-date 2023-01-01 --end-date 2024-12-31  # Two year span
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

    args = parser.parse_args()

    # Determine date range
    if args.year:
        start_date = f'{args.year}-01-01'
        end_date = f'{args.year}-12-31'
        year_label = str(args.year)
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
        year_label = f'{start_date}_to_{end_date}'
    else:
        # Default to current year
        current_year = datetime.now().year
        start_date = f'{current_year}-01-01'
        end_date = f'{current_year}-12-31'
        year_label = str(current_year)

    # Create data directory if it doesn't exist
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)

    filename = os.path.join(data_dir, f'{year_label}-volto-team-stats.csv')

    print("Volto Team Statistics Extractor")
    print("=" * 60)

    # Get token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("No GITHUB_TOKEN found in .env file!")
        return

    print(f"Token loaded: {len(token)} characters")

    # Setup session
    session = requests.Session()
    session.headers.update({
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    })

    # Test access
    print("Testing API access...")
    test_response = session.get('https://api.github.com/user')
    if test_response.status_code == 200:
        user_data = test_response.json()
        print(f"✓ Authenticated as: {user_data['login']}\n")
    else:
        print(f"✗ Authentication failed: {test_response.status_code}")
        return

    statistics = generate_statistics(session, start_date, end_date)
    save_to_csv(statistics, filename)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_prs = sum(s['pull_requests'] for s in statistics)
    total_commits = sum(s['commits'] for s in statistics)
    print(f"Total PRs: {total_prs}")
    print(f"Total Commits: {total_commits}")
    print(f"Active contributors (with PRs or commits): {sum(1 for s in statistics if s['pull_requests'] > 0 or s['commits'] > 0)}")

if __name__ == '__main__':
    main()
