#!/usr/bin/env python3
"""
Plone Pull Request Interactions Extractor

Extracts pull request comments, reviews, and interactions from Plone GitHub repositories
to analyze community engagement and collaboration patterns.
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import csv
import logging
from collections import defaultdict
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PlonePRInteractionExtractor:
    def __init__(self, github_token=None):
        """Initialize the PR interaction extractor."""
        # Force load from .env file directly (same as plone_stats.py)
        if github_token is None:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        github_token = line.split('=', 1)[1].strip()
                        break
        
        load_dotenv(override=True)
        
        self.github_token = github_token
        if not self.github_token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Plone-PR-Interaction-Extractor'
        })
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None
        
        # Cache for repository data
        self.repo_cache = {}
        
        # Plone core repositories to analyze
        self.plone_repos = [
            'plone/volto'
        ]
    
    def check_rate_limit(self):
        """Check and handle GitHub API rate limiting."""
        if self.rate_limit_remaining < 100:  # Conservative buffer
            if self.rate_limit_reset:
                sleep_time = self.rate_limit_reset - time.time() + 60  # Add 1 minute buffer
                if sleep_time > 0:
                    logger.info(f"Rate limit low. Sleeping for {sleep_time:.0f} seconds...")
                    time.sleep(sleep_time)
    
    def make_request(self, url, params=None):
        """Make a GitHub API request with rate limiting."""
        self.check_rate_limit()
        
        try:
            response = self.session.get(url, params=params)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.warning("Rate limit exceeded. Sleeping...")
                time.sleep(3600)  # Sleep for 1 hour
                return self.make_request(url, params)
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    def get_pull_requests(self, repo, start_date=None, end_date=None, state='all'):
        """Get pull requests for a repository."""
        params = {
            'state': state,
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100
        }
        
        # GitHub API 'since' parameter only works for issues, not pulls
        # We'll filter by date after fetching
        
        url = f"https://api.github.com/repos/{repo}/pulls"
        pull_requests = []
        page = 1
        
        while True:
            params['page'] = page
            data = self.make_request(url, params)
            
            if not data:
                break
                
            if not data:  # Empty page
                break
                
            # Filter by date range if specified
            filtered_prs = data
            if start_date or end_date:
                filtered_prs = []
                for pr in data:
                    pr_date = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                    
                    # Convert naive datetime to UTC for comparison
                    if start_date and start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=pr_date.tzinfo)
                    if end_date and end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=pr_date.tzinfo)
                    
                    # Check if PR falls within date range
                    within_range = True
                    if start_date and pr_date < start_date:
                        within_range = False
                    if end_date and pr_date > end_date:
                        within_range = False
                    
                    if within_range:
                        filtered_prs.append(pr)
            
            pull_requests.extend(filtered_prs)
            
            # Stop if we've reached the date limit or no more pages
            if len(data) < 100 or ((start_date or end_date) and not filtered_prs):
                break
                
            page += 1
            
        logger.info(f"Found {len(pull_requests)} pull requests in {repo}")
        return pull_requests
    
    def get_pr_comments(self, repo, pr_number):
        """Get all comments for a pull request."""
        comments_data = {
            'issue_comments': [],  # General discussion comments
            'review_comments': [],  # Code review comments
            'reviews': []  # Pull request reviews
        }
        
        # Get issue comments (general discussion)
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        issue_comments = []
        page = 1
        
        while True:
            params = {'page': page, 'per_page': 100}
            data = self.make_request(url, params)
            
            if not data:
                break
                
            issue_comments.extend(data)
            
            if len(data) < 100:
                break
                
            page += 1
        
        comments_data['issue_comments'] = issue_comments
        
        # Get review comments (code-specific)
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
        review_comments = []
        page = 1
        
        while True:
            params = {'page': page, 'per_page': 100}
            data = self.make_request(url, params)
            
            if not data:
                break
                
            review_comments.extend(data)
            
            if len(data) < 100:
                break
                
            page += 1
        
        comments_data['review_comments'] = review_comments
        
        # Get pull request reviews
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
        reviews = self.make_request(url)
        
        if reviews:
            comments_data['reviews'] = reviews
        
        return comments_data
    
    def analyze_pr_interactions(self, repo, pr_data, comments_data):
        """Analyze interactions for a single pull request."""
        analysis = {
            'repo': repo,
            'pr_number': pr_data['number'],
            'title': pr_data['title'],
            'author': pr_data['user']['login'],
            'created_at': pr_data['created_at'],
            'updated_at': pr_data['updated_at'],
            'merged_at': pr_data.get('merged_at'),
            'closed_at': pr_data.get('closed_at'),
            'state': pr_data['state'],
            'merged': pr_data.get('merged', False) or pr_data.get('merged_at') is not None,
            
            # Comment counts
            'issue_comments_count': len(comments_data['issue_comments']),
            'review_comments_count': len(comments_data['review_comments']),
            'reviews_count': len(comments_data['reviews']),
            'total_comments': len(comments_data['issue_comments']) + len(comments_data['review_comments']),
            
            # Participant analysis
            'participants': set(),
            'reviewers': set(),
            'commenters': set(),
            
            # Interaction timeline
            'first_response_time': None,
            'last_activity': pr_data['updated_at'],
            
            # Review analysis
            'approved_reviews': 0,
            'changes_requested_reviews': 0,
            'comment_reviews': 0,
            
            # Engagement metrics
            'reactions_total': 0,
            'conversation_threads': 0
        }
        
        # Collect all participants
        analysis['participants'].add(pr_data['user']['login'])
        
        # Analyze issue comments
        for comment in comments_data['issue_comments']:
            commenter = comment['user']['login']
            analysis['participants'].add(commenter)
            analysis['commenters'].add(commenter)
            
            # Count reactions
            if 'reactions' in comment:
                reactions = comment['reactions']
                analysis['reactions_total'] += (
                    reactions.get('+1', 0) + reactions.get('-1', 0) +
                    reactions.get('laugh', 0) + reactions.get('hooray', 0) +
                    reactions.get('confused', 0) + reactions.get('heart', 0) +
                    reactions.get('rocket', 0) + reactions.get('eyes', 0)
                )
        
        # Analyze review comments
        for comment in comments_data['review_comments']:
            commenter = comment['user']['login']
            analysis['participants'].add(commenter)
            analysis['commenters'].add(commenter)
        
        # Analyze reviews
        for review in comments_data['reviews']:
            reviewer = review['user']['login']
            analysis['participants'].add(reviewer)
            analysis['reviewers'].add(reviewer)
            
            if review['state'] == 'APPROVED':
                analysis['approved_reviews'] += 1
            elif review['state'] == 'CHANGES_REQUESTED':
                analysis['changes_requested_reviews'] += 1
            elif review['state'] == 'COMMENTED':
                analysis['comment_reviews'] += 1
        
        # Calculate response time (first comment/review after PR creation)
        pr_created = datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00'))
        first_response = None
        
        all_responses = []
        for comment in comments_data['issue_comments']:
            if comment['user']['login'] != pr_data['user']['login']:
                all_responses.append(datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')))
        
        for comment in comments_data['review_comments']:
            if comment['user']['login'] != pr_data['user']['login']:
                all_responses.append(datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')))
        
        for review in comments_data['reviews']:
            if review['user']['login'] != pr_data['user']['login']:
                all_responses.append(datetime.fromisoformat(review['submitted_at'].replace('Z', '+00:00')))
        
        if all_responses:
            first_response = min(all_responses)
            analysis['first_response_time'] = (first_response - pr_created).total_seconds() / 3600  # Hours
        
        # Convert sets to lists for JSON serialization
        analysis['participants'] = list(analysis['participants'])
        analysis['reviewers'] = list(analysis['reviewers'])
        analysis['commenters'] = list(analysis['commenters'])
        analysis['participants_count'] = len(analysis['participants'])
        analysis['reviewers_count'] = len(analysis['reviewers'])
        analysis['commenters_count'] = len(analysis['commenters'])
        
        return analysis
    
    def extract_interactions(self, repos=None, start_date=None, end_date=None, output_file=None):
        """Extract PR interactions for specified repositories."""
        repos = repos or self.plone_repos
        
        if start_date and end_date:
            logger.info(f"Extracting PR interactions from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        elif start_date:
            logger.info(f"Extracting PR interactions from {start_date.strftime('%Y-%m-%d')} onwards")
        elif end_date:
            logger.info(f"Extracting PR interactions up to {end_date.strftime('%Y-%m-%d')}")
        else:
            logger.info("Extracting all PR interactions (no date filter)")
        
        all_analyses = []
        
        for repo in repos:
            logger.info(f"Processing repository: {repo}")
            
            try:
                # Get pull requests
                prs = self.get_pull_requests(repo, start_date, end_date)
                
                for pr in prs:
                    logger.info(f"Analyzing PR #{pr['number']}: {pr['title'][:50]}...")
                    
                    # Get comments and interactions
                    comments_data = self.get_pr_comments(repo, pr['number'])
                    
                    # Analyze interactions
                    analysis = self.analyze_pr_interactions(repo, pr, comments_data)
                    all_analyses.append(analysis)
                    
                    # Small delay to be respectful to API
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error processing {repo}: {e}")
                continue
        
        # Save results
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"plone_pr_interactions_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(all_analyses, f, indent=2, default=str)
        
        logger.info(f"Saved {len(all_analyses)} PR interaction analyses to {output_file}")
        
        # Generate summary CSV
        self.generate_summary_csv(all_analyses, output_file.replace('.json', '_summary.csv'))
        
        return all_analyses
    
    def generate_summary_csv(self, analyses, output_file):
        """Generate a summary CSV of PR interactions."""
        fieldnames = [
            'repo', 'pr_number', 'title', 'author', 'created_at', 'merged_at', 'state', 'merged',
            'issue_comments_count', 'review_comments_count', 'reviews_count', 'total_comments',
            'participants_count', 'reviewers_count', 'commenters_count',
            'approved_reviews', 'changes_requested_reviews', 'comment_reviews',
            'reactions_total', 'first_response_time'
        ]
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for analysis in analyses:
                row = {field: analysis.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        logger.info(f"Generated summary CSV: {output_file}")
    
    def generate_engagement_report(self, analyses, output_file=None):
        """Generate an engagement analysis report."""
        if not output_file:
            output_file = "plone_pr_engagement_report.md"
        
        # Calculate statistics
        total_prs = len(analyses)
        merged_prs = len([a for a in analyses if a['merged']])
        
        # Helper function to filter out bots
        def is_bot(username):
            bot_patterns = ['[bot]', '-bot', 'bot-', 'dependabot', 'greenkeeper']
            username_lower = username.lower()
            return any(pattern in username_lower for pattern in bot_patterns)
        
        # Comment statistics
        total_comments = sum(a['total_comments'] for a in analyses)
        avg_comments_per_pr = total_comments / total_prs if total_prs > 0 else 0
        
        # Participation statistics (excluding bots)
        all_participants = set()
        all_reviewers = set()
        all_commenters = set()
        
        for analysis in analyses:
            all_participants.update([p for p in analysis['participants'] if not is_bot(p)])
            all_reviewers.update([r for r in analysis['reviewers'] if not is_bot(r)])
            all_commenters.update([c for c in analysis['commenters'] if not is_bot(c)])
        
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
                if not is_bot(participant):
                    participant_counts[participant] += 1
            for reviewer in analysis['reviewers']:
                if not is_bot(reviewer):
                    reviewer_counts[reviewer] += 1
            for commenter in analysis['commenters']:
                if not is_bot(commenter):
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
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Generated engagement report: {output_file}")
        
        return output_file


def main():
    """Main execution function."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description='Extract Plone PR interactions and engagement data',
        epilog="""
Examples:
  python plone_pr_interactions.py                    # Current year (default)
  python plone_pr_interactions.py --year 2024       # All of 2024
  python plone_pr_interactions.py --year 2025       # All of 2025
  python plone_pr_interactions.py --start-date 2024-01-01 --end-date 2024-06-30  # First half of 2024
  python plone_pr_interactions.py --all             # All PRs (no date filter)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--year', type=int, 
                       help='Extract interactions for a specific year (e.g., 2024)')
    parser.add_argument('--start-date', type=str,
                       help='Start date in YYYY-MM-DD format (e.g., 2024-01-01)')
    parser.add_argument('--end-date', type=str,
                       help='End date in YYYY-MM-DD format (e.g., 2024-12-31)')
    parser.add_argument('--all', action='store_true', 
                       help='Extract all PRs (no date filter)')
    
    args = parser.parse_args()
    
    # Set date range - same logic as plone_stats.py
    start_date = None
    end_date = None
    
    if args.all:
        # No date filtering
        start_date = None
        end_date = None
    elif args.year:
        # Specific year
        start_date = datetime(args.year, 1, 1)
        end_date = datetime(args.year, 12, 31, 23, 59, 59)
    elif args.start_date or args.end_date:
        # Custom date range
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        # Default to current year
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1)
        end_date = datetime(current_year, 12, 31, 23, 59, 59)
    
    extractor = PlonePRInteractionExtractor()
    
    # Extract interactions
    logger.info("Starting Plone PR interaction extraction...")
    
    try:
        analyses = extractor.extract_interactions(start_date=start_date, end_date=end_date)
        
        # Generate engagement report
        extractor.generate_engagement_report(analyses)
        
        logger.info("✅ PR interaction extraction completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())