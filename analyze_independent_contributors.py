#!/usr/bin/env python3
"""
Independent Contributors Analysis Script

Analyzes Independent contributors across all organisation CSV files to identify
patterns and potential mappings based on their contributions and commit patterns.
"""

import pandas as pd
import glob
from collections import defaultdict, Counter
import os
import re

def load_organisation_files():
    """Load all organisation CSV files"""
    files = glob.glob('*-plone-organisation-contributors.csv')
    files.sort()
    
    data = {}
    for file in files:
        year = file.split('-')[0]
        df = pd.read_csv(file)
        data[year] = df
        print(f"Loaded {file}: {len(df)} organisations")
    
    return data

def extract_independent_contributors(data):
    """Extract all Independent contributors from all years"""
    all_independents = set()
    contributor_years = defaultdict(set)
    contributor_stats = defaultdict(lambda: {'total_commits': 0, 'total_prs': 0, 'years': set(), 'repos': set()})
    
    for year, df in data.items():
        # Find the Independent row
        independent_rows = df[df['organisation'] == 'Independent']
        
        if len(independent_rows) > 0:
            independent_row = independent_rows.iloc[0]
            contributors_str = independent_row['contributors']
            
            if pd.notna(contributors_str):
                # Parse contributors (comma-separated)
                contributors = [c.strip() for c in contributors_str.split(',')]
                all_independents.update(contributors)
                
                for contributor in contributors:
                    contributor_years[contributor].add(year)
                    contributor_stats[contributor]['years'].add(year)
                    contributor_stats[contributor]['total_commits'] += int(independent_row['total_commits']) // len(contributors)
                    contributor_stats[contributor]['total_prs'] += int(independent_row['total_pull_requests']) // len(contributors)
                    
                    # Add repositories (if available)
                    if pd.notna(independent_row['repositories']):
                        repos = [r.strip() for r in independent_row['repositories'].split(',')]
                        contributor_stats[contributor]['repos'].update(repos)
                
                print(f"{year}: {len(contributors)} Independent contributors")
    
    return all_independents, contributor_years, contributor_stats

def analyze_contribution_patterns(contributor_stats):
    """Analyze contribution patterns to identify potential organisation mappings"""
    
    # Patterns to look for potential company associations
    patterns = {
        'High Activity': [],  # Contributors with many commits/PRs
        'Multi-Year': [],     # Contributors active across multiple years
        'Domain-Based': [],   # Contributors with domain-like usernames
        'Similar Names': []   # Contributors with similar naming patterns
    }
    
    # High activity contributors (>50 commits total or >20 PRs)
    for contributor, stats in contributor_stats.items():
        if stats['total_commits'] > 50 or stats['total_prs'] > 20:
            patterns['High Activity'].append({
                'name': contributor,
                'commits': stats['total_commits'],
                'prs': stats['total_prs'],
                'years': len(stats['years']),
                'repos': len(stats['repos'])
            })
    
    # Multi-year contributors (active in 3+ years)
    for contributor, stats in contributor_stats.items():
        if len(stats['years']) >= 3:
            patterns['Multi-Year'].append({
                'name': contributor,
                'years': sorted(list(stats['years'])),
                'commits': stats['total_commits'],
                'prs': stats['total_prs']
            })
    
    # Domain-based usernames (contain company-like patterns)
    domain_indicators = [
        'redhat', 'ibm', 'google', 'microsoft', 'oracle', 'canonical',
        'mozilla', 'github', 'gitlab', 'bitbucket', 'atlassian',
        'consulting', 'solutions', 'dev', 'tech', 'systems', 'corp'
    ]
    
    for contributor in contributor_stats.keys():
        contributor_lower = contributor.lower()
        for indicator in domain_indicators:
            if indicator in contributor_lower:
                patterns['Domain-Based'].append({
                    'name': contributor,
                    'indicator': indicator,
                    'commits': contributor_stats[contributor]['total_commits'],
                    'prs': contributor_stats[contributor]['total_prs']
                })
                break
    
    # Look for similar naming patterns that might indicate same organisation
    name_groups = defaultdict(list)
    for contributor in contributor_stats.keys():
        # Group by common prefixes/suffixes
        for other in contributor_stats.keys():
            if contributor != other:
                # Check for common substrings (>3 chars)
                for i in range(len(contributor) - 3):
                    substr = contributor[i:i+4].lower()
                    if substr in other.lower() and len(substr) > 3:
                        name_groups[substr].append(contributor)
                        name_groups[substr].append(other)
    
    # Filter groups with multiple unique contributors
    for substr, names in name_groups.items():
        unique_names = list(set(names))
        if len(unique_names) > 1:
            patterns['Similar Names'].append({
                'pattern': substr,
                'contributors': unique_names
            })
    
    return patterns

def suggest_mappings(patterns, existing_mapping_file='organisation_mapping.txt'):
    """Suggest new mappings based on analysis patterns"""
    
    # Load existing mappings to avoid duplicates
    existing_contributors = set()
    if os.path.exists(existing_mapping_file):
        with open(existing_mapping_file, 'r') as f:
            for line in f:
                if ':' in line:
                    _, contributors = line.split(':', 1)
                    contributor_list = [c.strip() for c in contributors.split(',')]
                    existing_contributors.update(contributor_list)
    
    suggestions = []
    
    # High activity contributors that might be worth researching
    high_activity = sorted(patterns['High Activity'], key=lambda x: x['commits'], reverse=True)[:20]
    for contrib in high_activity:
        if contrib['name'] not in existing_contributors:
            suggestions.append({
                'contributor': contrib['name'],
                'reason': f"High activity: {contrib['commits']} commits, {contrib['prs']} PRs across {contrib['years']} years",
                'priority': 'HIGH',
                'suggested_research': 'Check GitHub profile for company affiliation'
            })
    
    # Multi-year contributors (likely serious contributors)
    multi_year = sorted(patterns['Multi-Year'], key=lambda x: len(x['years']), reverse=True)[:15]
    for contrib in multi_year:
        if contrib['name'] not in existing_contributors:
            suggestions.append({
                'contributor': contrib['name'],
                'reason': f"Multi-year activity: {len(contrib['years'])} years ({', '.join(contrib['years'])})",
                'priority': 'MEDIUM',
                'suggested_research': 'Check for consistent employer across years'
            })
    
    # Domain-based contributors
    for contrib in patterns['Domain-Based']:
        if contrib['name'] not in existing_contributors:
            suggestions.append({
                'contributor': contrib['name'],
                'reason': f"Domain indicator: '{contrib['indicator']}' in username",
                'priority': 'MEDIUM',
                'suggested_research': f'Likely affiliated with {contrib["indicator"]} related organisation'
            })
    
    return suggestions

def generate_research_report():
    """Generate a comprehensive research report"""
    print("=" * 80)
    print("INDEPENDENT CONTRIBUTORS ANALYSIS REPORT")
    print("=" * 80)
    
    # Load data
    data = load_organisation_files()
    all_independents, contributor_years, contributor_stats = extract_independent_contributors(data)
    patterns = analyze_contribution_patterns(contributor_stats)
    suggestions = suggest_mappings(patterns)
    
    print(f"\nTOTAL ANALYSIS:")
    print(f"- Total unique Independent contributors across all years: {len(all_independents)}")
    print(f"- Contributors with multi-year activity: {len(patterns['Multi-Year'])}")
    print(f"- High activity contributors: {len(patterns['High Activity'])}")
    print(f"- Domain-based contributors: {len(patterns['Domain-Based'])}")
    
    print(f"\nYEAR-BY-YEAR BREAKDOWN:")
    for year in sorted(data.keys()):
        year_independents = [c for c, years in contributor_years.items() if year in years]
        print(f"- {year}: {len(year_independents)} Independent contributors")
    
    print(f"\nTOP 20 HIGH ACTIVITY INDEPENDENT CONTRIBUTORS:")
    print("-" * 60)
    high_activity = sorted(patterns['High Activity'], key=lambda x: x['commits'], reverse=True)[:20]
    for i, contrib in enumerate(high_activity, 1):
        print(f"{i:2d}. {contrib['name']:<20} | {contrib['commits']:4d} commits | {contrib['prs']:3d} PRs | {contrib['years']} years")
    
    print(f"\nTOP 15 MULTI-YEAR CONTRIBUTORS:")
    print("-" * 50)
    multi_year = sorted(patterns['Multi-Year'], key=lambda x: len(x['years']), reverse=True)[:15]
    for i, contrib in enumerate(multi_year, 1):
        years_str = ", ".join(contrib['years'])
        print(f"{i:2d}. {contrib['name']:<20} | {len(contrib['years'])} years ({years_str})")
    
    if patterns['Domain-Based']:
        print(f"\nDOMAIN-BASED CONTRIBUTORS:")
        print("-" * 40)
        for contrib in patterns['Domain-Based']:
            print(f"- {contrib['name']:<20} | '{contrib['indicator']}' indicator")
    
    print(f"\nPRIORITY RESEARCH SUGGESTIONS:")
    print("-" * 50)
    priority_suggestions = [s for s in suggestions if s['priority'] == 'HIGH'][:10]
    for i, suggestion in enumerate(priority_suggestions, 1):
        print(f"{i:2d}. {suggestion['contributor']}")
        print(f"    Reason: {suggestion['reason']}")
        print(f"    Action: {suggestion['suggested_research']}")
        print()
    
    return {
        'all_independents': all_independents,
        'contributor_stats': contributor_stats,
        'patterns': patterns,
        'suggestions': suggestions
    }

if __name__ == "__main__":
    results = generate_research_report()