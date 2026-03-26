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

Modes:
  API mode (default): fetches commits from the GitHub API in a single sweep per repo.
    As a side effect, builds a persistent email→GitHub-login cache in
    data/email-to-github-login.json so future local-mode runs are fast.

  Local mode (--local): clones/fetches all repos as bare git clones under repos/
    and uses git log for commit data. Much faster on repeat runs since git log
    is nearly instant. Only cache misses (new contributors) trigger API calls.
    Pull request data still comes from the API as it is not in git history.
"""

import json
import os
import subprocess
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


EMAIL_CACHE_FILE = Path('data/email-to-github-login.json')


class PloneStatsExtractor:
    def __init__(
        self,
        token: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        repos_dir: Path = Path('repos'),
    ):
        # Load token from .env if not provided
        if token is None:
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('GITHUB_TOKEN='):
                            token = line.split('=', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass

        load_dotenv(override=True)

        self.token = token
        self.org = 'plone'
        self.repos_dir = Path(repos_dir)
        self.session = self._create_session_with_retries()
        if self.token:
            self.session.headers.update({'Authorization': f'token {self.token}'})
            print(f"Using GitHub token (length: {len(self.token)})")
        else:
            print("No GitHub token found!")

        current_year = datetime.now().year
        self.start_date = start_date or datetime(current_year, 1, 1)
        self.end_date = end_date or datetime(current_year, 12, 31, 23, 59, 59)
        print(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")

        self.repositories: List[Dict] = []
        self.contributors_data: Dict = defaultdict(lambda: {
            'commits': 0,
            'pull_requests': 0,
            'repositories': set(),
            'first_contribution': None,
            'last_contribution': None,
        })

        # Persistent email → GitHub login cache (None = unlinked/bot, not looked up again)
        self.email_cache: Dict[str, Optional[str]] = self._load_email_cache()
        self._email_cache_dirty = False

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _create_session_with_retries(self):
        """Create a requests session with automatic retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
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
                wait_time = 2 ** attempt
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

    # ------------------------------------------------------------------
    # Email → GitHub login cache
    # ------------------------------------------------------------------

    def _load_email_cache(self) -> Dict[str, Optional[str]]:
        """Load the persistent email→login cache from disk."""
        if EMAIL_CACHE_FILE.exists():
            try:
                with open(EMAIL_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                print(f"Loaded email cache: {len(cache):,} entries from {EMAIL_CACHE_FILE}")
                return cache
            except Exception as e:
                print(f"Warning: could not load email cache ({e}), starting fresh.")
        return {}

    def _save_email_cache(self):
        """Atomically save the email→login cache to disk."""
        if not self._email_cache_dirty:
            return
        EMAIL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = EMAIL_CACHE_FILE.with_suffix('.json.tmp')
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.email_cache, f, indent=2, sort_keys=True)
            tmp.replace(EMAIL_CACHE_FILE)
            self._email_cache_dirty = False
            print(f"  Email cache saved: {len(self.email_cache):,} entries")
        except Exception as e:
            print(f"Warning: could not save email cache: {e}")

    def _resolve_email_to_login(self, email: str, repo_name: str, sha: str) -> Optional[str]:
        """Resolve an unknown email to a GitHub login via a single commit API call.

        Stores the result in the cache (including None for unlinked accounts)
        so the same email is never looked up twice.
        """
        url = f'https://api.github.com/repos/{self.org}/{repo_name}/commits/{sha}'
        response = self._safe_request('GET', url)
        login = None
        if response is not None and response.status_code == 200:
            author = response.json().get('author')
            if author and author.get('type') != 'Bot':
                login = author.get('login')
        self.email_cache[email] = login
        self._email_cache_dirty = True
        return login

    # ------------------------------------------------------------------
    # Shared commit recorder
    # ------------------------------------------------------------------

    def _record_commit(self, username: str, repo_name: str, commit_date: Optional[datetime]):
        """Tally one commit for a contributor."""
        data = self.contributors_data[username]
        data['commits'] += 1
        data['repositories'].add(repo_name)
        if commit_date:
            if data['first_contribution'] is None or commit_date < data['first_contribution']:
                data['first_contribution'] = commit_date
            if data['last_contribution'] is None or commit_date > data['last_contribution']:
                data['last_contribution'] = commit_date

    # ------------------------------------------------------------------
    # Repository list
    # ------------------------------------------------------------------

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
                print("Authentication failed (401). GitHub token is required.")
                return []
            elif response.status_code == 403:
                print("Access forbidden (403). Token may lack 'read:org' scope.")
                popular_repos = ['Plone', 'plone.api', 'Products.CMFPlone', 'plone.app.contenttypes', 'plone.restapi']
                for repo_name in popular_repos:
                    repo_url = f'https://api.github.com/repos/{self.org}/{repo_name}'
                    repo_resp = self.session.get(repo_url)
                    if repo_resp.status_code == 200:
                        repos.append(repo_resp.json())
                        print(f"  Added repository: {repo_name}")
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

    # ------------------------------------------------------------------
    # Commit collection — API mode
    # ------------------------------------------------------------------

    def collect_repo_commits(self, repo_name: str, default_branch: str):
        """Fetch all commits for a repo in one paginated API sweep.

        Tallies authors from the GitHub user object on each commit (no
        email mapping needed). As a side effect, populates the email cache
        so subsequent local-mode runs avoid API calls for known contributors.
        """
        url = f'https://api.github.com/repos/{self.org}/{repo_name}/commits'
        params = {
            'sha': default_branch,
            'since': self.start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'until': self.end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'per_page': 100,
        }

        page = 1
        total_commits = 0
        repo_contributors: set = set()

        while True:
            params['page'] = page
            response = self._safe_request('GET', url, params=params)

            if response is None:
                print(f"  Failed to fetch commits page {page} for {repo_name}")
                break
            if response.status_code == 409:  # empty repo
                break
            if response.status_code != 200:
                print(f"  Error {response.status_code} fetching commits for {repo_name}")
                break

            commits = response.json()
            if not commits:
                break

            for commit in commits:
                author = commit.get('author')  # GitHub user object, may be None
                git_author = commit.get('commit', {}).get('author', {})
                email = git_author.get('email', '').lower()

                # Populate email cache as a free side effect of the API response
                if email and email not in self.email_cache:
                    if author and author.get('type') != 'Bot':
                        self.email_cache[email] = author.get('login')
                    else:
                        self.email_cache[email] = None
                    self._email_cache_dirty = True

                if not author or author.get('type') == 'Bot':
                    continue
                username = author.get('login')
                if not username:
                    continue

                commit_date_str = git_author.get('date')
                commit_date = None
                if commit_date_str:
                    commit_date = datetime.fromisoformat(
                        commit_date_str.replace('Z', '+00:00')
                    ).replace(tzinfo=None)

                self._record_commit(username, repo_name, commit_date)
                repo_contributors.add(username)
                total_commits += 1

            if len(commits) < 100:
                break

            page += 1
            time.sleep(0.1)

        if total_commits:
            print(f"  {total_commits} commits from {len(repo_contributors)} contributors")

    # ------------------------------------------------------------------
    # Commit collection — local git mode
    # ------------------------------------------------------------------

    def clone_or_fetch_repo(self, repo_name: str, clone_url: str) -> Optional[Path]:
        """Ensure a bare clone of the repo exists locally and is up to date.

        Returns the path to the bare repo directory, or None on failure.
        """
        repo_path = self.repos_dir / f'{repo_name}.git'

        if repo_path.exists():
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'fetch', '--quiet', 'origin'],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"  Warning: git fetch failed for {repo_name}: {result.stderr.strip()}")
        else:
            self.repos_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Cloning {repo_name}...")
            result = subprocess.run(
                ['git', 'clone', '--bare', '--quiet', clone_url, str(repo_path)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"  Warning: git clone failed for {repo_name}: {result.stderr.strip()}")
                return None

        return repo_path

    def collect_repo_commits_local(self, repo_name: str, default_branch: str, repo_path: Path):
        """Collect commits from a local bare clone using git log.

        Resolves git author emails to GitHub logins via the email cache.
        Falls back to one API call per unknown email and caches the result,
        so each email is only ever resolved once across all runs.
        """
        after = self.start_date.strftime('%Y-%m-%d')
        # git --before is exclusive of midnight, so add one day buffer via the time component
        before = self.end_date.strftime('%Y-%m-%dT%H:%M:%S')

        # Format: hash TAB author-email TAB ISO-date
        result = subprocess.run(
            [
                'git', '-C', str(repo_path), 'log',
                default_branch,
                f'--after={after}',
                f'--before={before}',
                '--format=%H\t%ae\t%aI',
            ],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"  Warning: git log failed for {repo_name}: {result.stderr.strip()}")
            return

        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        if not lines:
            return

        total_commits = 0
        repo_contributors: set = set()
        api_lookups = 0

        for line in lines:
            parts = line.split('\t', 2)
            if len(parts) != 3:
                continue
            sha, email, date_str = parts
            email = email.lower()

            if email not in self.email_cache:
                login = self._resolve_email_to_login(email, repo_name, sha)
                api_lookups += 1
                time.sleep(0.1)  # gentle rate limit for cache-miss calls only
            else:
                login = self.email_cache[email]

            if not login:  # unlinked account or bot
                continue

            try:
                commit_date = datetime.fromisoformat(date_str).replace(tzinfo=None)
            except ValueError:
                commit_date = None

            self._record_commit(login, repo_name, commit_date)
            repo_contributors.add(login)
            total_commits += 1

        if total_commits:
            lookup_note = f", {api_lookups} API cache-miss lookups" if api_lookups else ""
            print(f"  {total_commits} commits from {len(repo_contributors)} contributors{lookup_note}")

    # ------------------------------------------------------------------
    # Pull requests (always via API — not in git history)
    # ------------------------------------------------------------------

    def get_repository_pull_requests(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get merged pull requests for a repository within the date range."""
        print(f"Fetching merged pull requests for {repo_name}...")

        prs = []
        page = 1

        while True:
            url = f'https://api.github.com/repos/{self.org}/{repo_name}/pulls'
            params = {
                'state': 'closed',
                'page': page,
                'per_page': 100,
                'sort': 'updated',
                'direction': 'desc',
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

            for pr in data:
                if pr.get('merged_at'):
                    merged_date = datetime.fromisoformat(
                        pr['merged_at'].replace('Z', '+00:00')
                    ).replace(tzinfo=None)
                    if self.start_date <= merged_date <= self.end_date:
                        prs.append(pr)

            page += 1

            # Stop paging once all merged PRs in the page predate our window
            merged_in_page = [pr for pr in data if pr.get('merged_at')]
            if merged_in_page and all(
                datetime.fromisoformat(
                    pr['merged_at'].replace('Z', '+00:00')
                ).replace(tzinfo=None) < self.start_date
                for pr in merged_in_page
            ):
                break

        print(f"Fetched {len(prs)} pull requests for {repo_name}")
        return prs

    def process_pull_requests(self, repo_name: str, prs: List[Dict[str, Any]]):
        """Tally merged pull requests per contributor."""
        try:
            merged_count = 0
            for pr in prs:
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

    # ------------------------------------------------------------------
    # Main extraction loop
    # ------------------------------------------------------------------

    def save_progress(self, filename: str):
        """Save current progress to a checkpoint CSV and flush the email cache."""
        df = self.generate_report()
        checkpoint_file = f"{filename}_checkpoint.csv"
        df.to_csv(checkpoint_file, index=False)
        print(f"Progress saved to {checkpoint_file}")
        self._save_email_cache()

    def extract_all_stats(self, max_repos: int = None, save_every: int = 50, local: bool = False):
        """Extract statistics from all repositories in the organization.

        Args:
            local:      Use local bare git clones for commit data.
            save_every: Save a checkpoint CSV every N repositories.
        """
        mode = "local git + email cache" if local else "GitHub API"
        print(f"Starting statistics extraction (mode: {mode})...")

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
                if repo.get('archived', False):
                    print(f"Skipping archived repository: {repo_name}")
                    continue

                default_branch = repo.get('default_branch', 'main')
                print(f"Default branch: {default_branch}")

                if local:
                    clone_url = repo.get('clone_url') or \
                        f'https://github.com/{self.org}/{repo_name}.git'
                    repo_path = self.clone_or_fetch_repo(repo_name, clone_url)
                    if repo_path:
                        self.collect_repo_commits_local(repo_name, default_branch, repo_path)
                    else:
                        print(f"  Falling back to API for {repo_name}")
                        self.collect_repo_commits(repo_name, default_branch)
                else:
                    self.collect_repo_commits(repo_name, default_branch)

                prs = self.get_repository_pull_requests(repo_name)
                if prs:
                    self.process_pull_requests(repo_name, prs)

            except Exception as e:
                print(f"ERROR: Failed to process repository {repo_name}: {e}")
                print("Continuing with next repository...")

            if save_every and i % save_every == 0:
                print(f"\n*** Saving checkpoint at repository {i}/{len(repos)} ***")
                self.save_progress(f"data/{self.start_date.year}-plone-contributors")

            time.sleep(0.2)

        self._save_email_cache()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def generate_report(self) -> pd.DataFrame:
        """Generate a DataFrame of contributor statistics."""
        data = []
        for username, stats in self.contributors_data.items():
            data.append({
                'username': username,
                'total_commits': stats['commits'],
                'total_pull_requests': stats['pull_requests'],
                'repositories_count': len(stats['repositories']),
                'repositories': ', '.join(sorted(stats['repositories'])),
                'first_contribution': (
                    stats['first_contribution'].strftime('%Y-%m-%d')
                    if stats['first_contribution'] else None
                ),
                'last_contribution': (
                    stats['last_contribution'].strftime('%Y-%m-%d')
                    if stats['last_contribution'] else None
                ),
            })

        if not data:
            print("No data collected. Creating empty report.")
            return pd.DataFrame(columns=[
                'username', 'total_commits', 'total_pull_requests',
                'repositories_count', 'repositories',
                'first_contribution', 'last_contribution',
            ])

        df = pd.DataFrame(data)
        return df.sort_values('total_commits', ascending=False)

    def save_report(self, df: pd.DataFrame, filename: str = None):
        """Save the report to a CSV file under data/."""
        if filename is None:
            filename = 'plone-contributors'
        csv_file = f'data/{filename}.csv'
        df.to_csv(csv_file, index=False)
        print(f"Report saved to {csv_file}")
        return csv_file


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract GitHub statistics from the Plone organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plone_contributors.py                          # current year, API mode
  python plone_contributors.py --year 2024             # all of 2024, API mode
  python plone_contributors.py --year 2024 --local     # all of 2024, local git mode
  python plone_contributors.py --start-date 2024-01-01 --end-date 2024-06-30
        """,
    )
    parser.add_argument('--year', type=int, help='Extract stats for a specific year (e.g., 2024)')
    parser.add_argument('--start-date', type=str, help='Start date YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='End date YYYY-MM-DD')
    parser.add_argument('--token', type=str, help='GitHub token (overrides .env)')
    parser.add_argument(
        '--local',
        action='store_true',
        help='Use local bare git clones instead of the GitHub commits API',
    )
    parser.add_argument(
        '--repos-dir',
        type=str,
        default='repos',
        help='Directory for bare git clones used in --local mode (default: repos/)',
    )
    return parser.parse_args()


def validate_and_parse_dates(args):
    start_date = None
    end_date = None

    if args.year:
        start_date = datetime(args.year, 1, 1)
        end_date = datetime(args.year, 12, 31, 23, 59, 59)
        print(f"Using year: {args.year}")
    elif args.start_date or args.end_date:
        if args.start_date:
            try:
                start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid start date: {args.start_date}. Use YYYY-MM-DD")
        if args.end_date:
            try:
                end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise ValueError(f"Invalid end date: {args.end_date}. Use YYYY-MM-DD")
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date must be before end date")
    else:
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1)
        end_date = datetime(current_year, 12, 31, 23, 59, 59)
        print(f"Using default year: {current_year}")

    return start_date, end_date


def main():
    print("Plone GitHub Statistics Extractor")
    print("=" * 40)

    args = parse_arguments()

    try:
        start_date, end_date = validate_and_parse_dates(args)

        extractor = PloneStatsExtractor(
            token=args.token,
            start_date=start_date,
            end_date=end_date,
            repos_dir=Path(args.repos_dir),
        )

        if start_date.year == end_date.year:
            filename = f'{start_date.year}-plone-contributors'
        else:
            filename = f'{start_date.year}-{end_date.year}-plone-contributors'

        try:
            extractor.extract_all_stats(local=args.local)
        except KeyboardInterrupt:
            print("\n\nExtraction interrupted by user. Saving progress...")
        except Exception as e:
            print(f"\n\nUnexpected error during extraction: {e}")
            print("Saving current progress...")

        df = extractor.generate_report()

        print("\n" + "=" * 50)
        print("TOP 10 CONTRIBUTORS BY PRs:")
        print(df.sort_values('total_pull_requests', ascending=False).head(10)[
            ['username', 'total_commits', 'total_pull_requests', 'repositories_count']
        ])

        extractor.save_report(df, filename)

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
