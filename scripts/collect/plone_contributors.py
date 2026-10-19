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
- The history from before the default branch started, which in some
  repositories is only on the old release branches (2.5, 3.0, ...) (#68)

Commits on feature branches that were never merged are NOT counted. Merge
commits are not counted either (#39).

The commits are read from local clones (git_history.py) and linked to
GitHub accounts by their author email, like the GitHub API does. The
closed pull requests come from the API. Both are fetched once for the
whole requested time range, and then assigned to the requested periods
(usually years). One run can therefore produce the files for many years
at once (--from-year/--to-year).
"""

import os
import sys
import time
import csv
import requests
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import pandas as pd
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from scripts.lib import git_history
from scripts.lib import paths
from scripts.lib.github_api import GitHubAPIError, github_get, github_graphql, is_merge_commit
from scripts.lib.model import load_bot_accounts, load_excluded_repositories, load_registry
from scripts.lib.tables import by_count


EXCLUDED_REPOSITORIES_FILE = paths.EXCLUDED_REPOSITORIES
BOT_ACCOUNTS_FILE = paths.BOT_ACCOUNTS
REPORT_COLUMNS = ['username', 'total_commits', 'total_pull_requests', 'repositories_count',
                  'repositories', 'first_contribution', 'last_contribution']

# A period is (label, start, end); the label is the output file name without .csv
Period = Tuple[str, datetime, datetime]


def parse_timestamp(value: str) -> datetime:
    """Parse a GitHub UTC timestamp into a naive datetime, like the date range."""
    return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)


def select_repositories(repos: List[Dict[str, Any]], excluded: Dict[str, str]):
    """Split repositories into the ones to process and the skipped ones.

    Archived repositories are processed: their history belongs to the years
    they were active in. Excluded repositories (e.g. forks with foreign
    upstream history, or duplicate copies) are skipped with their reason.
    """
    selected = []
    skipped = []
    for repo in repos:
        if repo['name'] in excluded:
            skipped.append((repo['name'], excluded[repo['name']]))
        else:
            selected.append(repo)
    return selected, skipped


def year_periods(from_year: int, to_year: int) -> List[Period]:
    """One period per calendar year, labelled like the yearly data files."""
    return [
        (f'{year}-plone-contributors', datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59))
        for year in range(from_year, to_year + 1)
    ]


def _new_stats():
    return {
        'commits': 0,
        'pull_requests': 0,
        'repositories': set(),
        'first_contribution': None,
        'last_contribution': None,
    }


class PloneStatsExtractor:
    def __init__(self, token: str = None, start_date: datetime = None, end_date: datetime = None,
                 periods: List[Period] = None):
        # The token comes from --token, the environment, or the .env file.
        # The environment is better than --token, which shows up in the process list.
        load_dotenv()
        token = token or os.getenv('GITHUB_TOKEN')

        self.token = token
        self.org = 'plone'
        self.session = self._create_session_with_retries()
        if self.token:
            self.session.headers.update({'Authorization': f'token {self.token}'})
            print(f"Using GitHub token (length: {len(self.token)})")
        else:
            print("No GitHub token found!")

        if periods is None:
            # A single period - default to current year if not provided
            current_year = datetime.now().year
            start = start_date or datetime(current_year, 1, 1)
            end = end_date or datetime(current_year, 12, 31, 23, 59, 59)
            if start.year == end.year:
                label = f'{start.year}-plone-contributors'
            else:
                label = f'{start.year}-{end.year}-plone-contributors'
            periods = [(label, start, end)]
        self.periods = periods
        self.start_date = min(start for _, start, _ in periods)
        self.end_date = max(end for _, _, end in periods)

        print(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
              f" ({len(periods)} period{'s' if len(periods) > 1 else ''})")

        self.bots = load_bot_accounts()
        self.registry = load_registry()
        self.cache_dir = git_history.CACHE_DIR
        # Author email (lower case) -> GitHub login, or None if the email is not linked to an account
        self.email_logins = {}
        self.repositories = []
        self.contributors_data = {label: defaultdict(_new_stats) for label, _, _ in periods}

    def _create_session_with_retries(self):
        """Create a requests session with automatic retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,  # Total number of retries
            backoff_factor=2,  # Wait 1, 2, 4, 8, 16 seconds between retries
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors; rate limits are handled by github_get
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only retry safe methods
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get(self, url, params=None):
        """GET from the GitHub API; waits for rate limits and raises GitHubAPIError on errors."""
        return github_get(self.session, url, params=params)

    def _period_for(self, date: datetime):
        """Return the label of the period that contains the date, or None."""
        for label, start, end in self.periods:
            if start <= date <= end:
                return label
        return None

    def _is_person(self, user) -> bool:
        """True for a GitHub user who is a person: not a bot account, not a deleted user."""
        return bool(user) and user.get('type') == 'User' and user.get('login') not in self.bots

    def get_organization_repos(self) -> List[Dict[str, Any]]:
        """Fetch all repositories from the Plone organization."""
        print(f"Fetching repositories from {self.org} organization...")
        repos = []
        page = 1

        while True:
            url = f'https://api.github.com/orgs/{self.org}/repos'
            params = {'page': page, 'per_page': 100, 'sort': 'updated'}

            response = self._get(url, params=params)

            data = response.json()
            if not data:
                break

            repos.extend(data)
            print(f"Fetched {len(data)} repositories (page {page})")
            page += 1

        self.repositories = repos
        print(f"Total repositories found: {len(repos)}")
        return repos

    def get_repository_commits(self, repo_name: str, default_branch: str) -> List[Dict[str, Any]]:
        """Get the commits of the default branch (and its older history) in the whole date range.

        They are read from a local clone (#68) and linked to GitHub accounts.
        """
        url = f'https://github.com/{self.org}/{repo_name}.git'
        path = os.path.join(self.cache_dir, self.org, f'{repo_name}.git')
        commits = [
            commit for commit in git_history.repository_commits(url, path, default_branch, token=self.token)
            if self.start_date <= parse_timestamp(commit['commit']['committer']['date']) <= self.end_date
        ]
        self.link_authors(repo_name, commits)
        return commits

    def link_authors(self, repo_name: str, commits: List[Dict[str, Any]], batch_size: int = 100):
        """Set the GitHub account of each commit, like the commit list of the GitHub API does.

        GitHub links a commit to the account that has its author email. For
        each email not seen before, one of its commits is looked up in a
        GraphQL query, up to batch_size commits per query.
        """
        unknown = {}
        for commit in commits:
            email = commit['commit']['author']['email'].strip().lower()
            if email not in self.email_logins:
                unknown.setdefault(email, commit['sha'])

        lookups = list(unknown.items())
        for start in range(0, len(lookups), batch_size):
            batch = lookups[start:start + batch_size]
            fields = ' '.join(
                f'c{i}: object(oid: "{sha}") {{ ... on Commit {{ author {{ user {{ login }} }} }} }}'
                for i, (_, sha) in enumerate(batch)
            )
            query = f'query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{ {fields} }} }}'
            data = github_graphql(self.session, query, {'owner': self.org, 'name': repo_name})
            for i, (email, _) in enumerate(batch):
                node = data['repository'][f'c{i}']
                # Bots are no User, their user is None
                user = ((node or {}).get('author') or {}).get('user')
                self.email_logins[email] = user['login'] if user else None

        for commit in commits:
            email = commit['commit']['author']['email'].strip().lower()
            # Emails that GitHub does not link, e.g. name@localhost from SVN times (#69)
            login = self.email_logins[email]
            if login:
                login = self.counted_login(login)
            else:
                person = self.registry.person_for(email=email)
                login = self.registry.username_of(person) if person else None
            # GraphQL returns GitHub Apps such as pre-commit-ci[bot] as users; the REST API says Bot
            user_type = 'Bot' if login and login.endswith('[bot]') else 'User'
            commit['author'] = {'login': login, 'type': user_type} if login else None

    def counted_login(self, login):
        """The login a GitHub account counts under: the main login of a second account, else the login itself."""
        person = self.registry.person_for(login=login)
        return person.github if person and person.github else login

    def process_commits(self, repo_name: str, commits: List[Dict[str, Any]]):
        """Count each commit for its author in the period of its commit date."""
        counted = 0
        for commit in commits:
            # Merge commits are not code creation (#39)
            if is_merge_commit(commit):
                continue
            # Skip bots and commits without a linked GitHub account
            author = commit.get('author')
            if not self._is_person(author):
                continue

            label = self._period_for(parse_timestamp(commit['commit']['committer']['date']))
            if label is None:
                continue

            stats = self.contributors_data[label][author['login']]
            stats['commits'] += 1
            stats['repositories'].add(repo_name)
            counted += 1

            authored = parse_timestamp(commit['commit']['author']['date'])
            if stats['first_contribution'] is None or authored < stats['first_contribution']:
                stats['first_contribution'] = authored
            if stats['last_contribution'] is None or authored > stats['last_contribution']:
                stats['last_contribution'] = authored

        print(f"Counted {counted} of {len(commits)} commits for {repo_name}")

    def get_repository_pull_requests(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get the pull requests of a repository merged in the whole date range."""
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

            response = self._get(url, params=params)

            if response.status_code != 200:  # empty repository
                break

            data = response.json()
            if not data:
                break

            # Filter PRs by date range (using merged_at date for consistency with commit counting).
            # PRs to any base branch count, including backports to maintenance branches.
            for pr in data:
                if pr.get('merged_at'):
                    merged_date = parse_timestamp(pr['merged_at'])
                    if self.start_date <= merged_date <= self.end_date:
                        prs.append(pr)

            page += 1

            # A short page is the last one
            if len(data) < 100:
                break
            # PRs are sorted by last update, newest first. A PR merged in the range
            # was updated after its merge, so once a whole page was last updated
            # before the range starts, no later page can match (#42).
            if all(parse_timestamp(pr['updated_at']) < self.start_date for pr in data):
                break

        print(f"Fetched {len(prs)} pull requests for {repo_name}")
        return prs

    def process_pull_requests(self, repo_name: str, prs: List[Dict[str, Any]]):
        """Count each merged pull request for its author in the period of its merge date."""
        merged_count = 0
        for pr in prs:
            # Only count merged PRs (filter out closed but not merged PRs)
            if pr.get('merged_at') is None or not self._is_person(pr.get('user')):
                continue

            label = self._period_for(parse_timestamp(pr['merged_at']))
            if label is None:
                continue

            login = pr['user']['login']
            stats = self.contributors_data[label][self.counted_login(login)]
            stats['pull_requests'] += 1
            stats['repositories'].add(repo_name)
            merged_count += 1

        print(f"Processed {merged_count} merged PRs for {repo_name}")

    def save_progress(self):
        """Save the current progress of every period to a checkpoint file."""
        for label, _, _ in self.periods:
            checkpoint_file = paths.checkpoint_file(label)
            self.generate_report(label).to_csv(checkpoint_file, index=False)
            print(f"Progress saved to {checkpoint_file}")

    def extract_all_stats(self, max_repos: int = None, save_every: int = 50):
        """Extract statistics from all repositories in the organization."""
        print("Starting statistics extraction...")

        repos = self.get_organization_repos()
        repos, skipped = select_repositories(repos, load_excluded_repositories())
        for repo_name, reason in skipped:
            print(f"Skipping excluded repository {repo_name}: {reason}")

        if max_repos:
            repos = repos[:max_repos]
            print(f"Processing first {max_repos} repositories")

        for i, repo in enumerate(repos, 1):
            repo_name = repo['name']
            print(f"\n{'='*60}")
            print(f"Processing repository {i}/{len(repos)}: {repo_name}")
            print(f"{'='*60}")

            # Errors are not skipped: a repository with missing data would make the
            # whole year incomplete. They propagate, and main() keeps only a checkpoint.
            default_branch = repo.get('default_branch', 'main')
            print(f"Default branch: {default_branch}")

            self.process_commits(repo_name, self.get_repository_commits(repo_name, default_branch))
            self.process_pull_requests(repo_name, self.get_repository_pull_requests(repo_name))

            # Save progress checkpoint every N repositories
            if save_every and i % save_every == 0:
                print(f"\n*** Saving checkpoint at repository {i}/{len(repos)} ***")
                self.save_progress()

    def generate_report(self, label: str = None) -> pd.DataFrame:
        """Generate the report for one period (the only period by default)."""
        if label is None:
            label = self.periods[0][0]
        data = []

        for username, stats in self.contributors_data[label].items():
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
            print(f"No data collected for {label}. Creating empty report.")
            return pd.DataFrame(columns=REPORT_COLUMNS)
        return by_count(pd.DataFrame(data), 'total_commits', 'username')

    def save_report(self, df: pd.DataFrame, filename: str = None):
        """Save the report to CSV file."""
        if filename is None:
            filename = 'plone-contributors'

        # Save to CSV
        csv_file = paths.CONTRIBUTORS_DIR / f'{filename}.csv'
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
  python -m scripts.collect.plone_contributors                    # Current year (default)
  python -m scripts.collect.plone_contributors --year 2024        # All of 2024
  python -m scripts.collect.plone_contributors --from-year 2003 --to-year 2025   # One file per year, in one run
  python -m scripts.collect.plone_contributors --start-date 2024-01-01 --end-date 2024-06-30  # First half of 2024
  python -m scripts.collect.plone_contributors --start-date 2023-01-01 --end-date 2024-12-31  # Two year span
        """
    )

    parser.add_argument(
        '--year',
        type=int,
        help='Extract stats for a specific year (e.g., 2024)'
    )

    parser.add_argument(
        '--from-year',
        type=int,
        help='First year of a range; writes one file per year (use with --to-year)'
    )

    parser.add_argument(
        '--to-year',
        type=int,
        help='Last year of a range (use with --from-year)'
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
        help='GitHub token. Better use GITHUB_TOKEN or the .env file: --token shows up in the process list.'
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


def periods_from_arguments(args) -> List[Period]:
    """Return the periods to collect: one per year for --from-year/--to-year, else a single one."""
    if args.from_year or args.to_year:
        if not (args.from_year and args.to_year):
            raise ValueError("Use --from-year and --to-year together")
        if args.from_year > args.to_year:
            raise ValueError("--from-year must not be after --to-year")
        return year_periods(args.from_year, args.to_year)

    start_date, end_date = validate_and_parse_dates(args)
    if start_date.year == end_date.year:
        label = f'{start_date.year}-plone-contributors'
    else:
        label = f'{start_date.year}-{end_date.year}-plone-contributors'
    return [(label, start_date, end_date)]


def main():
    """Main function to run the statistics extraction."""
    print("Plone GitHub Statistics Extractor")
    print("=" * 40)

    # Parse command line arguments
    args = parse_arguments()

    try:
        periods = periods_from_arguments(args)
        extractor = PloneStatsExtractor(token=args.token, periods=periods)

        try:
            # Extract statistics from all repositories
            extractor.extract_all_stats()
        except (KeyboardInterrupt, GitHubAPIError, git_history.GitError, requests.exceptions.RequestException) as e:
            # Never write incomplete data to the regular files, only checkpoints
            reason = 'interrupted by user' if isinstance(e, KeyboardInterrupt) else f'{type(e).__name__}: {e}'
            print(f"\n\nExtraction stopped ({reason}).")
            extractor.save_progress()
            print("The regular data files were not written, because the data is incomplete.")
            return 1

        for label, _, _ in periods:
            df = extractor.generate_report(label)
            extractor.save_report(df, label)
            print(f"{label}: {len(df)} contributors")

        print(f"\nStatistics extraction completed!")
        print(f"Total repositories found: {len(extractor.repositories)}")

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
    sys.exit(main())
