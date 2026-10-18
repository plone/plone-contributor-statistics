#!/usr/bin/env python3
"""
Plone Pull Request Interactions Extractor

Extracts pull request comments, reviews, and interactions from Plone GitHub repositories
to analyze community engagement and collaboration patterns.

Each repository is read once for the whole date range: the PRs with their
comments and reviews come from the GraphQL API (one request per 50 PRs), the
code review comments from one repository-wide REST listing. A PR belongs to
the year it was created in. Bots are left out: their PRs, comments and reviews.
"""

import os
import re
import sys
import time
import requests
from datetime import datetime
import csv
import logging
from collections import defaultdict
from dotenv import load_dotenv

import paths
from github_api import GitHubAPIError, github_get, github_graphql
from mappings import load_bot_accounts, load_excluded_repositories
from plone_contributors import parse_timestamp, select_repositories

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGE_SIZE = 50
# GitHub shows deleted accounts as "ghost"
GHOST = 'ghost'

PULL_REQUESTS_QUERY = """
query($owner: String!, $name: String!, $pageSize: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: $pageSize, after: $after, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title createdAt updatedAt mergedAt closedAt state
        author { login __typename }
        comments(first: 100) {
          totalCount
          nodes { author { login __typename } createdAt reactionGroups { reactors { totalCount } } }
        }
        reviews(first: 100) {
          totalCount
          nodes { author { login __typename } state submittedAt }
        }
      }
    }
  }
}
"""


def graphql_login(actor):
    """Login of a GraphQL actor, with the [bot] suffix that the REST API uses for bots."""
    if not actor:
        return GHOST
    if actor.get('__typename') == 'Bot':
        return f"{actor['login']}[bot]"
    return actor['login']


def rest_login(user):
    """Login of a REST API user; bots already have the [bot] suffix."""
    return user['login'] if user else GHOST


def graphql_comment(node):
    return {
        'login': graphql_login(node['author']),
        'created_at': node['createdAt'],
        'reactions': sum(group['reactors']['totalCount'] for group in node.get('reactionGroups') or []),
    }


def rest_comment(comment):
    return {
        'login': rest_login(comment['user']),
        'created_at': comment['created_at'],
        'reactions': (comment.get('reactions') or {}).get('total_count', 0),
    }


def graphql_review(node):
    return {'login': graphql_login(node['author']), 'state': node['state'], 'submitted_at': node['submittedAt']}


def rest_review(review):
    return {'login': rest_login(review['user']), 'state': review['state'], 'submitted_at': review.get('submitted_at')}


def graphql_pull_request(node):
    """A PR from the GraphQL API in the form used here."""
    return {
        'number': node['number'],
        'title': node['title'],
        'author': graphql_login(node['author']),
        'created_at': node['createdAt'],
        'updated_at': node['updatedAt'],
        'merged_at': node['mergedAt'],
        'closed_at': node['closedAt'],
        # Like the REST API: MERGED and CLOSED are both "closed"
        'state': 'open' if node['state'] == 'OPEN' else 'closed',
        'merged': node['mergedAt'] is not None,
        'comments': [graphql_comment(c) for c in node['comments']['nodes']],
        'comments_total': node['comments']['totalCount'],
        'reviews': [graphql_review(r) for r in node['reviews']['nodes']],
        'reviews_total': node['reviews']['totalCount'],
    }


class PlonePRInteractionExtractor:
    def __init__(self, github_token=None):
        """Initialize the PR interaction extractor."""
        load_dotenv()

        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN or use --token.")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Plone-PR-Interaction-Extractor'
        })

        self.bots = load_bot_accounts()

        # Organization to fetch repositories from
        self.org = 'plone'

        # Will be populated by get_organization_repos()
        self.plone_repos = []
        self.repositories = []

    def is_bot(self, login):
        """True for GitHub Apps ([bot]) and the bot accounts in bot_accounts.csv."""
        return login.endswith('[bot]') or login in self.bots

    def get_all_pages(self, url, params=None):
        """GET all pages of a REST API listing."""
        items = []
        page = 1
        while True:
            data = github_get(self.session, url, params={**(params or {}), 'page': page, 'per_page': 100}).json()
            items.extend(data)
            if len(data) < 100:
                return items
            page += 1

    def get_organization_repos(self):
        """Fetch all repositories from the Plone organization."""
        logger.info(f"Fetching repositories from {self.org} organization...")
        repos = self.get_all_pages(f'https://api.github.com/orgs/{self.org}/repos', {'sort': 'updated'})

        # Skip the same repositories as plone_contributors.py
        repos, skipped = select_repositories(repos, load_excluded_repositories())
        for repo_name, reason in skipped:
            logger.info(f"Skipping excluded repository {repo_name}: {reason}")

        self.repositories = repos
        # Convert to repo names for compatibility
        self.plone_repos = [f"{self.org}/{repo['name']}" for repo in repos]
        logger.info(f"Total repositories found: {len(repos)}")
        return repos

    def get_pull_requests(self, repo, start_date=None, end_date=None):
        """Get the PRs created in the date range, with their comments and reviews."""
        owner, name = repo.split('/')
        pull_requests = []
        after = None

        while True:
            data = github_graphql(self.session, PULL_REQUESTS_QUERY,
                                  {'owner': owner, 'name': name, 'pageSize': PAGE_SIZE, 'after': after})
            connection = data['repository']['pullRequests']

            reached_start = False
            for node in connection['nodes']:
                created = parse_timestamp(node['createdAt'])
                if end_date and created > end_date:
                    continue
                # Sorted by creation, newest first: the rest is older
                if start_date and created < start_date:
                    reached_start = True
                    break
                pull_requests.append(graphql_pull_request(node))

            if reached_start or not connection['pageInfo']['hasNextPage']:
                break
            after = connection['pageInfo']['endCursor']

        # The query returns up to 100 comments and reviews; get the rest of the rare longer ones
        base = f'https://api.github.com/repos/{repo}'
        for pr in pull_requests:
            if pr['comments_total'] > len(pr['comments']):
                pr['comments'] = [rest_comment(c) for c in self.get_all_pages(f"{base}/issues/{pr['number']}/comments")]
            if pr['reviews_total'] > len(pr['reviews']):
                pr['reviews'] = [rest_review(r) for r in self.get_all_pages(f"{base}/pulls/{pr['number']}/reviews")]

        logger.info(f"Found {len(pull_requests)} pull requests in {repo}")
        return pull_requests

    def get_review_comments(self, repo, start_date=None):
        """Get the code review comments of a repository, grouped by PR number."""
        params = {'sort': 'created', 'direction': 'asc'}
        if start_date:
            # Comments on PRs created in the range were updated after it started
            params['since'] = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        by_pr = defaultdict(list)
        for comment in self.get_all_pages(f'https://api.github.com/repos/{repo}/pulls/comments', params):
            number = int(re.search(r'/pulls/(\d+)$', comment['pull_request_url']).group(1))
            by_pr[number].append({'login': rest_login(comment['user']), 'created_at': comment['created_at']})
        return by_pr

    def analyze_pr_interactions(self, repo, pr_data, review_comments=()):
        """Analyze interactions for a single pull request. Bot comments and reviews are left out."""
        author = pr_data['author']
        comments = [c for c in pr_data['comments'] if not self.is_bot(c['login'])]
        review_comments = [c for c in review_comments if not self.is_bot(c['login'])]
        # Pending reviews have no submission date
        reviews = [r for r in pr_data['reviews'] if r['submitted_at'] and not self.is_bot(r['login'])]

        commenters = {c['login'] for c in comments} | {c['login'] for c in review_comments}
        reviewers = {r['login'] for r in reviews}
        participants = {author} | commenters | reviewers

        # Response time: first comment or review by someone else than the author
        responses = [parse_timestamp(c['created_at']) for c in comments + review_comments if c['login'] != author]
        responses += [parse_timestamp(r['submitted_at']) for r in reviews if r['login'] != author]
        first_response_time = None
        if responses:
            first_response_time = (min(responses) - parse_timestamp(pr_data['created_at'])).total_seconds() / 3600

        states = [r['state'] for r in reviews]
        return {
            'repo': repo,
            'pr_number': pr_data['number'],
            'title': pr_data['title'],
            'author': author,
            'created_at': pr_data['created_at'],
            'updated_at': pr_data['updated_at'],
            'merged_at': pr_data['merged_at'],
            'closed_at': pr_data['closed_at'],
            'state': pr_data['state'],
            'merged': pr_data['merged'],

            # Comment counts
            'issue_comments_count': len(comments),
            'review_comments_count': len(review_comments),
            'reviews_count': len(reviews),
            'total_comments': len(comments) + len(review_comments),

            # Participant analysis
            'participants': sorted(participants),
            'reviewers': sorted(reviewers),
            'commenters': sorted(commenters),
            'participants_count': len(participants),
            'reviewers_count': len(reviewers),
            'commenters_count': len(commenters),

            # Review analysis
            'approved_reviews': states.count('APPROVED'),
            'changes_requested_reviews': states.count('CHANGES_REQUESTED'),
            'comment_reviews': states.count('COMMENTED'),

            # Engagement metrics
            'reactions_total': sum(c['reactions'] for c in comments),
            'first_response_time': first_response_time,
            'last_activity': pr_data['updated_at'],
        }

    def extract_interactions(self, repos=None, start_date=None, end_date=None):
        """Extract PR interactions for the PRs created in the date range.

        Raises GitHubAPIError when a request fails, so that no incomplete data is written.
        """
        # Fetch all Plone repositories if none specified
        if repos is None:
            self.get_organization_repos()
            repos = self.plone_repos

        logger.info(f"Extracting PR interactions from {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}")

        all_analyses = []
        for index, repo in enumerate(repos, 1):
            logger.info(f"Processing repository {index}/{len(repos)}: {repo}")
            prs = [pr for pr in self.get_pull_requests(repo, start_date, end_date) if not self.is_bot(pr['author'])]
            if not prs:
                continue
            review_comments = self.get_review_comments(repo, start_date)
            for pr in prs:
                all_analyses.append(self.analyze_pr_interactions(repo, pr, review_comments.get(pr['number'], [])))

        return all_analyses

    def save_csv_report(self, analyses, filename: str = None):
        """Save the PR interactions report to CSV file (similar to plone_stats.py)."""
        if filename is None:
            filename = 'plone-pr-interactions'

        # Create data directory if it doesn't exist
        os.makedirs(paths.PR_INTERACTIONS_DIR, exist_ok=True)

        # Save to CSV in data folder
        csv_file = paths.PR_INTERACTIONS_DIR / f'{filename}.csv'

        fieldnames = [
            'repo', 'pr_number', 'title', 'author', 'created_at', 'merged_at', 'state', 'merged',
            'issue_comments_count', 'review_comments_count', 'reviews_count', 'total_comments',
            'participants_count', 'reviewers_count', 'commenters_count',
            'approved_reviews', 'changes_requested_reviews', 'comment_reviews',
            'reactions_total', 'first_response_time'
        ]

        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for analysis in sorted(analyses, key=lambda a: (a['repo'], a['pr_number'])):
                row = {field: analysis.get(field, '') for field in fieldnames}
                writer.writerow(row)

        logger.info(f"Report saved to {csv_file}")
        return csv_file

    def generate_engagement_report(self, analyses, output_file=None, year=None):
        """Generate an engagement analysis report."""
        if not output_file:
            if year:
                # Create report directory if it doesn't exist
                os.makedirs(paths.PR_INTERACTION_REPORTS_DIR, exist_ok=True)
                output_file = paths.pr_interactions_report(year)
            else:
                output_file = "plone_pr_engagement_report.md"
        
        # Calculate statistics
        total_prs = len(analyses)
        merged_prs = len([a for a in analyses if a['merged']])
        
        # Comment statistics
        total_comments = sum(a['total_comments'] for a in analyses)
        avg_comments_per_pr = total_comments / total_prs if total_prs > 0 else 0
        
        # Participation statistics (excluding bots)
        all_participants = set()
        all_reviewers = set()
        all_commenters = set()
        
        for analysis in analyses:
            all_participants.update([p for p in analysis['participants'] if not self.is_bot(p)])
            all_reviewers.update([r for r in analysis['reviewers'] if not self.is_bot(r)])
            all_commenters.update([c for c in analysis['commenters'] if not self.is_bot(c)])
        
        # Response time statistics
        response_times = [a['first_response_time'] for a in analyses if a['first_response_time'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate merge rate safely
        merge_rate = (merged_prs / total_prs * 100) if total_prs > 0 else 0
        
        # Top contributors by engagement
        participant_counts = defaultdict(int)
        reviewer_counts = defaultdict(int)
        commenter_counts = defaultdict(int)
        
        for analysis in analyses:
            for participant in analysis['participants']:
                if not self.is_bot(participant):
                    participant_counts[participant] += 1
            for reviewer in analysis['reviewers']:
                if not self.is_bot(reviewer):
                    reviewer_counts[reviewer] += 1
            for commenter in analysis['commenters']:
                if not self.is_bot(commenter):
                    commenter_counts[commenter] += 1
        
        # Generate report
        report_content = f"""# Plone Pull Request Engagement Report

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

- **Total Pull Requests Analyzed**: {total_prs:,}
- **Merged Pull Requests**: {merged_prs:,} ({merge_rate:.1f}% merge rate)
- **Total Comments**: {total_comments:,}
- **Average Comments per PR**: {avg_comments_per_pr:.1f}
- **Average First Response Time**: {avg_response_time:.1f} hours

## Community Engagement

- **Unique Participants**: {len(all_participants):,}
- **Unique Reviewers**: {len(all_reviewers):,}
- **Unique Commenters**: {len(all_commenters):,}

## Top 10 Most Active Participants

| Rank | Participant | PRs Participated |
|------|-------------|------------------|
"""
        
        top_participants = sorted(participant_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for rank, (participant, count) in enumerate(top_participants, 1):
            report_content += f"| {rank} | {participant} | {count} |\n"
        
        report_content += f"""
## Top 10 Most Active Reviewers

| Rank | Reviewer | PRs Reviewed |
|------|----------|--------------|
"""
        
        top_reviewers = sorted(reviewer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for rank, (reviewer, count) in enumerate(top_reviewers, 1):
            report_content += f"| {rank} | {reviewer} | {count} |\n"
        
        report_content += f"""
## Repository Breakdown

| Repository | PRs | Avg Comments | Avg Participants |
|------------|-----|-------------|------------------|
"""
        
        repo_stats = defaultdict(lambda: {'count': 0, 'comments': 0, 'participants': 0})
        for analysis in analyses:
            repo = analysis['repo']
            repo_stats[repo]['count'] += 1
            repo_stats[repo]['comments'] += analysis['total_comments']
            repo_stats[repo]['participants'] += analysis['participants_count']
        
        for repo, stats in sorted(repo_stats.items()):
            avg_comments = stats['comments'] / stats['count']
            avg_participants = stats['participants'] / stats['count']
            report_content += f"| {repo} | {stats['count']} | {avg_comments:.1f} | {avg_participants:.1f} |\n"
        
        report_content += f"""

## Engagement Insights

### Most Discussed PRs (by comment count)
"""
        
        most_discussed = sorted(analyses, key=lambda x: x['total_comments'], reverse=True)[:5]
        for pr in most_discussed:
            report_content += f"- **[{pr['repo']}#{pr['pr_number']}](https://github.com/{pr['repo']}/pull/{pr['pr_number']})**: {pr['title']} ({pr['total_comments']} comments)\n"
        
        report_content += f"""
### Fastest Response Times (hours)
"""
        
        fastest_responses = sorted([a for a in analyses if a['first_response_time']], 
                                 key=lambda x: x['first_response_time'])[:5]
        for pr in fastest_responses:
            report_content += f"- **[{pr['repo']}#{pr['pr_number']}](https://github.com/{pr['repo']}/pull/{pr['pr_number']})**: {pr['first_response_time']:.1f} hours\n"
        
        # Save report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Generated engagement report: {output_file}")
        
        return output_file



def periods_from_arguments(args):
    """Return the periods to write, as (label, start, end), one per year where possible."""
    if args.from_year or args.to_year:
        if not (args.from_year and args.to_year):
            raise ValueError("Use --from-year and --to-year together")
        if args.from_year > args.to_year:
            raise ValueError("--from-year must not be after --to-year")
        years = range(args.from_year, args.to_year + 1)
    elif args.start_date or args.end_date:
        if not (args.start_date and args.end_date):
            raise ValueError("Use --start-date and --end-date together")
        start = datetime.strptime(args.start_date, '%Y-%m-%d')
        end = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        if start > end:
            raise ValueError("Start date must be before end date")
        label = str(start.year) if start.year == end.year else f'{start.year}-{end.year}'
        return [(label, start, end)]
    else:
        years = [args.year or datetime.now().year]
    return [(str(year), datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)) for year in years]


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract Plone PR interactions and engagement data',
        epilog="""
Examples:
  python plone_pr_interactions.py                    # All Plone repos, current year
  python plone_pr_interactions.py --year 2024       # All Plone repos, all of 2024
  python plone_pr_interactions.py --from-year 2010 --to-year 2025  # One file per year, in one run
  python plone_pr_interactions.py --repos plone/volto --year 2025  # Only Volto, 2025
  python plone_pr_interactions.py --repos plone/volto plone/plone.restapi --year 2024  # Specific repos
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--year', type=int,
                        help='Extract interactions for a specific year (e.g., 2024)')
    parser.add_argument('--from-year', type=int,
                        help='First year of a range; writes one file per year (use with --to-year)')
    parser.add_argument('--to-year', type=int,
                        help='Last year of a range (use with --from-year)')
    parser.add_argument('--start-date', type=str,
                        help='Start date in YYYY-MM-DD format (e.g., 2024-01-01)')
    parser.add_argument('--end-date', type=str,
                        help='End date in YYYY-MM-DD format (e.g., 2024-12-31)')
    parser.add_argument('--repos', nargs='+',
                        help='Specific repositories to analyze (e.g., plone/volto plone/plone.restapi). If not specified, all Plone repos will be fetched.')
    parser.add_argument('--token', type=str,
                        help='GitHub token (if not using GITHUB_TOKEN or the .env file)')

    args = parser.parse_args()

    try:
        periods = periods_from_arguments(args)
        extractor = PlonePRInteractionExtractor(github_token=args.token)
    except ValueError as e:
        logger.error(str(e))
        return 1

    logger.info("Starting Plone PR interaction extraction...")
    start_date = min(start for _, start, _ in periods)
    end_date = max(end for _, _, end in periods)

    try:
        analyses = extractor.extract_interactions(repos=args.repos, start_date=start_date, end_date=end_date)
    except (KeyboardInterrupt, GitHubAPIError, requests.exceptions.RequestException) as e:
        # Never write incomplete data
        reason = 'interrupted by user' if isinstance(e, KeyboardInterrupt) else f'{type(e).__name__}: {e}'
        logger.error(f"❌ Extraction stopped ({reason}). No files were written, because the data is incomplete.")
        return 1

    for label, start, end in periods:
        period_analyses = [a for a in analyses if start <= parse_timestamp(a['created_at']) <= end]
        csv_file = extractor.save_csv_report(period_analyses, f'{label}-plone-pr-interactions')
        report_file = extractor.generate_engagement_report(period_analyses, year=label)
        logger.info(f"{label}: {len(period_analyses)} PRs, saved to {csv_file} and {report_file}")

    logger.info("✅ PR interaction extraction completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
