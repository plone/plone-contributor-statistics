#!/usr/bin/env python3
"""
Plone Companies/Organizations Extractor

Identifies companies and organizations that have contributed to Plone repositories
by analyzing:
1. GitHub profile company information
2. Email domains from commit data
3. Known organizational patterns
"""

import os
import time
import json
import re
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any
import requests
import pandas as pd
from dotenv import load_dotenv

# Force reload environment
if 'GITHUB_TOKEN' in os.environ:
    del os.environ['GITHUB_TOKEN']
load_dotenv(override=True)

class PloneCompanyExtractor:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            print("ERROR: No GITHUB_TOKEN found in .env file")
            exit(1)
            
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'token {self.token}'})
        
        # Track data
        self.contributors = {}  # username -> profile data
        self.email_domains = Counter()
        self.companies = defaultdict(lambda: {
            'contributors': set(),
            'total_commits': 0,
            'repositories': set(),
            'source': 'unknown'
        })
        
        # Known organizational email domains
        self.known_domains = {
            'plone.org': 'Plone Foundation',
            'plone.com': 'Plone Solutions AG', 
            'kitconcept.com': 'kitconcept GmbH',
            'gocept.com': 'gocept gmbh & co. kg',
            'groundwire.org': 'Groundwire',
            'enfold.com': 'Enfold Systems',
            'jarn.com': 'Jarn',
            'zestsoftware.nl': 'Zest Software',
            '六域.com': 'Six Feet Up',
            'sixfeetup.com': 'Six Feet Up',
            'pretaweb.com': 'Pretaweb',
            'redturtle.it': 'RedTurtle Technology',
            'abstract.it': 'Abstract srl',
            'redomino.com': 'Redomino srl',
            'inquant.es': 'InQuant',
            'wildcardcorp.com': 'Wildcard Corp',
            'jazkarta.com': 'Jazkarta',
            'alteroo.com': 'Alteroo',
            'netsight.co.uk': 'Netsight Internet Solutions',
            'gmail.com': None,  # Individual contributors
            'yahoo.com': None,
            'hotmail.com': None,
            'outlook.com': None,
            'me.com': None,
            'icloud.com': None
        }
        
    def get_plone_repositories(self, max_repos=50) -> List[Dict]:
        """Get Plone repositories, focusing on most active ones."""
        print("Fetching Plone repositories...")
        repos = []
        page = 1
        
        while len(repos) < max_repos:
            url = 'https://api.github.com/orgs/plone/repos'
            params = {
                'page': page, 
                'per_page': 100, 
                'sort': 'updated',
                'direction': 'desc'
            }
            
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                print(f"Error fetching repos: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
                
            # Filter for repositories with some activity
            active_repos = [r for r in data if r['stargazers_count'] > 0 or r['forks_count'] > 0]
            repos.extend(active_repos)
            
            print(f"  Found {len(active_repos)} active repos on page {page}")
            page += 1
            
            if len(data) < 100:  # Last page
                break
                
        # Sort by activity and take top repos
        repos.sort(key=lambda x: x['stargazers_count'] + x['forks_count'] * 2, reverse=True)
        selected_repos = repos[:max_repos]
        
        print(f"Selected top {len(selected_repos)} repositories for analysis")
        return selected_repos
    
    def get_contributor_profile(self, username: str) -> Dict:
        """Get detailed profile information for a contributor."""
        if username in self.contributors:
            return self.contributors[username]
            
        url = f'https://api.github.com/users/{username}'
        response = self.session.get(url)
        
        if response.status_code == 200:
            profile = response.json()
            self.contributors[username] = profile
            return profile
        else:
            print(f"  Warning: Could not fetch profile for {username} ({response.status_code})")
            return {}
    
    def extract_email_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if not email or '@' not in email:
            return None
        return email.split('@')[-1].lower()
    
    def normalize_company_name(self, company: str) -> str:
        """Normalize company names for matching."""
        if not company:
            return ""
        
        # Convert to lowercase for comparison
        normalized = company.lower().strip()
        
        # Remove common suffixes/prefixes
        normalized = re.sub(r'\b(gmbh|ag|llc|inc|ltd|corp|corporation|company|co\.)\b', '', normalized)
        normalized = re.sub(r'[,\s]+', ' ', normalized).strip()
        
        return normalized
    
    def get_commit_authors(self, repo_name: str) -> Dict[str, Dict]:
        """Get commit author information including emails."""
        print(f"  Analyzing commits in {repo_name}...")
        
        # Get recent commits with author details
        url = f'https://api.github.com/repos/plone/{repo_name}/commits'
        params = {'per_page': 100}  # Recent commits
        
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            print(f"    Error fetching commits: {response.status_code}")
            return {}
        
        commits = response.json()
        authors = {}
        
        for commit in commits:
            # GitHub author (account)
            if commit.get('author') and commit['author']:
                username = commit['author']['login']
                if username not in authors:
                    authors[username] = {'commits': 0, 'emails': set()}
                authors[username]['commits'] += 1
            
            # Git author (email from commit)
            if commit.get('commit', {}).get('author', {}).get('email'):
                email = commit['commit']['author']['email']
                domain = self.extract_email_domain(email)
                if domain:
                    self.email_domains[domain] += 1
                    
                # Try to match email to GitHub user
                if commit.get('author') and commit['author']:
                    username = commit['author']['login']
                    if username in authors:
                        authors[username]['emails'].add(email)
        
        print(f"    Found {len(authors)} unique commit authors")
        return authors
    
    def analyze_contributors_for_companies(self, repo_name: str, contributors_data: Dict):
        """Analyze contributors to identify their companies."""
        print(f"  Analyzing companies for {repo_name}...")
        
        for username, data in contributors_data.items():
            # Get profile data
            profile = self.get_contributor_profile(username)
            time.sleep(0.1)  # Rate limiting
            
            company = None
            source = 'unknown'
            
            # Check profile company field
            if profile.get('company'):
                company = profile['company'].strip()
                # Clean company name
                company = re.sub(r'^@', '', company)  # Remove @ prefix
                company = re.sub(r'\s+', ' ', company)  # Normalize whitespace
                source = 'profile'
            
            # Check email domains
            if not company and 'emails' in data:
                for email in data['emails']:
                    domain = self.extract_email_domain(email)
                    if domain and domain in self.known_domains and self.known_domains[domain]:
                        company = self.known_domains[domain]
                        source = 'email_domain'
                        break
            
            # If we found a company, record it
            if company:
                # Normalize company name
                company = company.strip()
                if company.lower() in ['none', 'n/a', '-', '']:
                    continue
                    
                self.companies[company]['contributors'].add(username)
                self.companies[company]['total_commits'] += data.get('commits', 0)
                self.companies[company]['repositories'].add(repo_name)
                self.companies[company]['source'] = source
    
    def process_repository(self, repo: Dict):
        """Process a single repository for company data."""
        repo_name = repo['name']
        print(f"\nProcessing: {repo_name} ({repo['stargazers_count']} stars)")
        
        # Get contributors with commit stats
        url = f'https://api.github.com/repos/plone/{repo_name}/stats/contributors'
        
        contributors_stats = {}
        for attempt in range(3):
            response = self.session.get(url)
            
            if response.status_code == 200:
                stats = response.json()
                if stats:
                    for contrib in stats:
                        if contrib and contrib.get('author'):
                            username = contrib['author']['login']
                            contributors_stats[username] = {
                                'commits': contrib['total'],
                                'emails': set()
                            }
                    break
            elif response.status_code == 202:
                print(f"  Statistics computing, waiting...")
                time.sleep(3)
            else:
                print(f"  Error getting stats: {response.status_code}")
                break
        
        # Get additional email data from recent commits
        commit_authors = self.get_commit_authors(repo_name)
        
        # Merge commit email data with contributor stats
        for username, commit_data in commit_authors.items():
            if username in contributors_stats:
                contributors_stats[username]['emails'].update(commit_data['emails'])
            elif commit_data['commits'] > 0:
                contributors_stats[username] = commit_data
        
        # Analyze for companies
        if contributors_stats:
            self.analyze_contributors_for_companies(repo_name, contributors_stats)
            print(f"  Processed {len(contributors_stats)} contributors")
        
        time.sleep(1)  # Rate limiting
    
    def generate_company_report(self) -> pd.DataFrame:
        """Generate comprehensive company report."""
        print("\nGenerating company report...")
        
        data = []
        for company, info in self.companies.items():
            data.append({
                'company': company,
                'contributors_count': len(info['contributors']),
                'total_commits': info['total_commits'],
                'repositories_count': len(info['repositories']),
                'repositories': ', '.join(sorted(info['repositories'])),
                'contributors': ', '.join(sorted(info['contributors'])[:10]),  # First 10
                'data_source': info['source']
            })
        
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values('total_commits', ascending=False)
            return df
        else:
            return pd.DataFrame()
    
    def analyze_email_domains(self) -> pd.DataFrame:
        """Analyze email domains to identify additional organizations."""
        print("\nAnalyzing email domains...")
        
        domain_data = []
        for domain, count in self.email_domains.most_common():
            # Skip personal email providers
            if domain in self.known_domains and not self.known_domains[domain]:
                continue
                
            # Try to identify organization
            organization = self.known_domains.get(domain, 'Unknown')
            
            domain_data.append({
                'domain': domain,
                'commit_count': count,
                'organization': organization,
                'type': 'known' if domain in self.known_domains else 'unknown'
            })
        
        return pd.DataFrame(domain_data)
    
    def merge_companies(self, companies_df: pd.DataFrame) -> pd.DataFrame:
        """Merge companies with similar names."""
        print("Merging duplicate company entries...")
        
        # Define merge rules
        merge_rules = {
            'kitconcept': ['kitconcept', 'kitconcept gmbh', 'kitconcept, gmbh'],
            'redturtle technology': ['redturtle', 'redturtle technology'],
            'makina corpus': ['makina corpus', 'makina corpus makinacorpus'],
            'plone foundation': ['plone foundation', 'plone'],
            'syslab.com': ['syslab.com, bluedynamics alliance', 'syslabcom'],
            'six feet up': ['six feet up', 'sixfeetup', '六域.com'],
            'zest software': ['zest software', 'zestsoftware'],
            'gocept': ['gocept', 'gocept gmbh & co. kg'],
            'abstract srl': ['abstract', 'abstract srl'],
            'redomino srl': ['redomino', 'redomino srl'],
            'wildcard corp': ['wildcard', 'wildcard corp']
        }
        
        # Create mapping of original names to canonical names
        name_mapping = {}
        for canonical, variants in merge_rules.items():
            for variant in variants:
                # Find matches in the dataframe
                for company in companies_df['company'].values:
                    if self.normalize_company_name(company) == self.normalize_company_name(variant):
                        name_mapping[company] = canonical
        
        # Group companies by canonical name
        merged_data = defaultdict(lambda: {
            'contributors': set(),
            'total_commits': 0,
            'repositories': set(),
            'sample_contributors': set(),
            'canonical_name': '',
            'data_source': 'unknown'
        })
        
        for _, row in companies_df.iterrows():
            company = row['company']
            canonical = name_mapping.get(company, company)
            
            merged_data[canonical]['canonical_name'] = canonical
            
            # Parse contributors list and add to set
            if pd.notna(row['contributors']):
                contrib_list = [c.strip() for c in str(row['contributors']).split(',')]
                merged_data[canonical]['contributors'].update(contrib_list)
            
            merged_data[canonical]['total_commits'] += row['total_commits']
            merged_data[canonical]['data_source'] = row.get('data_source', 'unknown')
            
            # Parse repositories
            if pd.notna(row['repositories']):
                repos = [r.strip() for r in str(row['repositories']).split(',')]
                merged_data[canonical]['repositories'].update(repos)
            
            # Use first few contributors as samples
            if pd.notna(row['contributors']):
                contrib_list = [c.strip() for c in str(row['contributors']).split(',')]
                merged_data[canonical]['sample_contributors'].update(contrib_list[:10])
        
        # Convert back to DataFrame format
        result_data = []
        for canonical, data in merged_data.items():
            result_data.append({
                'company': data['canonical_name'],
                'contributors_count': len(data['contributors']),
                'total_commits': data['total_commits'],
                'repositories_count': len(data['repositories']),
                'repositories': ', '.join(sorted(data['repositories'])),
                'contributors': ', '.join(list(data['sample_contributors'])[:10]),  # First 10
                'data_source': data['data_source']
            })
        
        result_df = pd.DataFrame(result_data)
        result_df = result_df.sort_values('total_commits', ascending=False)
        
        print(f"Merged {len(companies_df)} companies into {len(result_df)} (removed {len(companies_df) - len(result_df)} duplicates)")
        
        return result_df
    
    def save_results(self, companies_df: pd.DataFrame, domains_df: pd.DataFrame, merged_df: pd.DataFrame = None):
        """Save results to files."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save company report
        companies_file = f'plone_companies_{timestamp}.csv'
        companies_df.to_csv(companies_file, index=False)
        print(f"Company report saved to: {companies_file}")
        
        # Save merged companies if provided
        if merged_df is not None:
            merged_file = f'plone_companies_merged_{timestamp}.csv'
            merged_df.to_csv(merged_file, index=False)
            print(f"Merged companies report saved to: {merged_file}")
        
        # Save domains report
        domains_file = f'plone_domains_{timestamp}.csv'
        domains_df.to_csv(domains_file, index=False)
        print(f"Email domains report saved to: {domains_file}")
        
        # Save raw data
        raw_file = f'plone_companies_raw_{timestamp}.json'
        raw_data = {
            'companies': {k: {
                'contributors': list(v['contributors']),
                'total_commits': v['total_commits'],
                'repositories': list(v['repositories']),
                'source': v['source']
            } for k, v in self.companies.items()},
            'email_domains': dict(self.email_domains.most_common()),
            'contributors_profiles': self.contributors
        }
        
        with open(raw_file, 'w') as f:
            json.dump(raw_data, f, indent=2)
        print(f"Raw data saved to: {raw_file}")

def main():
    print("Plone Companies/Organizations Extractor")
    print("=" * 50)
    
    extractor = PloneCompanyExtractor()
    
    # Test authentication
    response = extractor.session.get('https://api.github.com/user')
    if response.status_code == 200:
        user = response.json()
        print(f"✓ Authenticated as: {user['login']}")
    else:
        print("✗ Authentication failed")
        return
    
    # Get repositories to analyze
    repos = extractor.get_plone_repositories(max_repos=25)  # Top 25 repos
    print(f"\nAnalyzing {len(repos)} repositories for company information...")
    
    # Process each repository
    for i, repo in enumerate(repos, 1):
        print(f"\n[{i}/{len(repos)}]", end=" ")
        extractor.process_repository(repo)
    
    # Generate reports
    companies_df = extractor.generate_company_report()
    domains_df = extractor.analyze_email_domains()
    
    # Merge duplicate companies
    merged_df = None
    if len(companies_df) > 0:
        merged_df = extractor.merge_companies(companies_df)
    
    # Display results
    print("\n" + "=" * 70)
    print("COMPANIES/ORGANIZATIONS CONTRIBUTING TO PLONE:")
    print("=" * 70)
    
    if len(companies_df) > 0:
        print("ORIGINAL COMPANIES (before merging):")
        print(companies_df[['company', 'contributors_count', 'total_commits', 'repositories_count']])
        print(f"\nOriginal companies identified: {len(companies_df)}")
        
        if merged_df is not None and len(merged_df) > 0:
            print(f"\nMERGED COMPANIES (after deduplication):")
            print(merged_df[['company', 'contributors_count', 'total_commits', 'repositories_count']])
            print(f"Merged companies: {len(merged_df)}")
        
        # Show top email domains
        print("\nTOP EMAIL DOMAINS:")
        print(domains_df.head(15)[['domain', 'commit_count', 'organization']])
        
        # Save results
        extractor.save_results(companies_df, domains_df, merged_df)
    else:
        print("No company data collected")

if __name__ == "__main__":
    main()