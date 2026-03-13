#!/usr/bin/env python3
"""
Fetch all releases from github.com/plone/Products.CMFPlone

This script fetches all releases from the Products.CMFPlone repository
and outputs them to a CSV file with the release name and upload date.
"""

import os
import csv
import requests
import time
from datetime import datetime
from dotenv import load_dotenv


def create_session(token: str = None) -> requests.Session:
    """
    Create a requests session with optional authentication.

    Args:
        token: Optional GitHub token for authentication

    Returns:
        Configured requests session
    """
    session = requests.Session()
    if token and token != 'your_token_here':
        session.headers.update({'Authorization': f'Bearer {token}'})
        print(f"Using GitHub token for authentication")
    else:
        print("No GitHub token provided - using unauthenticated requests")
    return session


def fetch_all_releases(owner: str, repo: str, session: requests.Session) -> list:
    """
    Fetch all releases from a GitHub repository.

    Args:
        owner: Repository owner (e.g., 'plone')
        repo: Repository name (e.g., 'Products.CMFPlone')
        session: Requests session with authentication

    Returns:
        List of dictionaries containing release information
    """
    releases = []
    page = 1

    print(f"Fetching releases from {owner}/{repo}...")

    while True:
        url = f'https://api.github.com/repos/{owner}/{repo}/releases'
        params = {'page': page, 'per_page': 100}

        response = session.get(url, params=params)

        if response.status_code != 200:
            print(f"Error fetching releases: {response.status_code}")
            if response.status_code == 403:
                print("Rate limit may be exceeded. Try using a GitHub token.")
            break

        data = response.json()
        if not data:
            break

        releases.extend(data)
        print(f"Fetched {len(data)} releases (page {page})")
        page += 1

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    print(f"Total releases found: {len(releases)}")
    return releases


def parse_release_data(releases: list) -> list:
    """
    Parse release data to extract tag name and published date.

    Args:
        releases: List of release dictionaries from GitHub API

    Returns:
        List of tuples (tag_name, published_date)
    """
    parsed_releases = []

    for release in releases:
        tag_name = release.get('tag_name', '')
        published_at = release.get('published_at', '')

        # Parse the date and format it as YYYY-MM-DD
        if published_at:
            try:
                date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                formatted_date = published_at
        else:
            formatted_date = ''

        parsed_releases.append((tag_name, formatted_date))

    return parsed_releases


def save_to_csv(releases: list, filename: str = 'cmfplone-releases.csv'):
    """
    Save releases to a CSV file.

    Args:
        releases: List of tuples (release_name, release_date)
        filename: Output filename
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['release', 'date'])
        writer.writerows(releases)

    print(f"Releases saved to {filename}")


def main():
    """Main function to fetch and save releases."""
    print("Products.CMFPlone Release Fetcher")
    print("=" * 40)

    # Load environment variables
    load_dotenv()

    # Try to get GitHub token from environment
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        # Try reading directly from .env file
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    # Create session
    session = create_session(token)

    # Fetch releases
    releases = fetch_all_releases('plone', 'Products.CMFPlone', session)

    if not releases:
        print("No releases found or error occurred.")
        return 1

    # Parse release data
    parsed_releases = parse_release_data(releases)

    # Save to CSV
    save_to_csv(parsed_releases)

    # Display first 10 releases
    print("\nFirst 10 releases:")
    print("-" * 40)
    print(f"{'Release':<20} {'Date':<15}")
    print("-" * 40)
    for release, date in parsed_releases[:10]:
        print(f"{release:<20} {date:<15}")

    print(f"\nTotal releases exported: {len(parsed_releases)}")

    return 0


if __name__ == "__main__":
    exit(main())
