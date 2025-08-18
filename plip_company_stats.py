#!/usr/bin/env python3
"""
PLIP Company Statistics Generator

Uses the company mapping from company_mapping.txt to aggregate PLIP statistics
from plone-plips.csv by company, similar to company_stats.py but for PLIPs.
"""

import pandas as pd
from collections import defaultdict
import os

def load_company_mapping():
    """Load company mapping from company_mapping.txt"""
    mapping = {}
    companies = defaultdict(list)
    
    if not os.path.exists('company_mapping.txt'):
        print("❌ company_mapping.txt not found")
        return mapping, companies
    
    with open('company_mapping.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                company, contributors = line.split(':', 1)
                contributor_list = [c.strip() for c in contributors.split(',') if c.strip()]
                companies[company].extend(contributor_list)
                for contributor in contributor_list:
                    mapping[contributor] = company
    
    print(f"Loaded mapping for {len(mapping)} contributors across {len(companies)} companies")
    return mapping, companies

def load_plip_contributors():
    """Load PLIP contributor statistics"""
    if not os.path.exists('plone-plips.csv'):
        print("❌ plone-plips.csv not found. Run 'python plone_plips.py' first.")
        return None
    
    df = pd.read_csv('plone-plips.csv')
    print(f"Loaded {len(df)} PLIP contributor records")
    return df

def aggregate_plip_companies(plip_df, mapping, companies):
    """Aggregate PLIP statistics by company"""
    
    company_stats = []
    unmapped_contributors = []
    
    for company, contributors in companies.items():
        # Find PLIPs for this company's contributors
        company_plips = plip_df[plip_df['username'].isin(contributors)]
        
        if len(company_plips) == 0:
            continue
            
        # Aggregate statistics
        total_plips = company_plips['total_plips'].sum()
        open_plips = company_plips['open_plips'].sum()
        closed_plips = company_plips['closed_plips'].sum()
        contributors_count = len(company_plips)
        
        # Get all repositories this company has PLIPs in
        all_repos = set()
        for repos_str in company_plips['repositories'].dropna():
            repos = [r.strip() for r in repos_str.split(',')]
            all_repos.update(repos)
        repositories_count = len(all_repos)
        repositories = ', '.join(sorted(all_repos))
        
        # Get contributor list
        contributors_list = ', '.join(sorted(company_plips['username'].tolist()))
        
        # Get date ranges
        first_plip = company_plips['first_plip'].min()
        last_plip = company_plips['last_plip'].max()
        
        company_stats.append({
            'company': company,
            'total_plips': total_plips,
            'open_plips': open_plips,
            'closed_plips': closed_plips,
            'contributors_count': contributors_count,
            'contributors': contributors_list,
            'repositories_count': repositories_count,
            'repositories': repositories,
            'first_plip': first_plip,
            'last_plip': last_plip
        })
    
    # Handle unmapped contributors (Independent)
    mapped_contributors = set(mapping.keys())
    unmapped = plip_df[~plip_df['username'].isin(mapped_contributors)]
    
    if len(unmapped) > 0:
        # Aggregate Independent statistics
        total_plips = unmapped['total_plips'].sum()
        open_plips = unmapped['open_plips'].sum()
        closed_plips = unmapped['closed_plips'].sum()
        contributors_count = len(unmapped)
        
        # Get all repositories for Independent contributors
        all_repos = set()
        for repos_str in unmapped['repositories'].dropna():
            repos = [r.strip() for r in repos_str.split(',')]
            all_repos.update(repos)
        repositories_count = len(all_repos)
        repositories = ', '.join(sorted(all_repos))
        
        contributors_list = ', '.join(sorted(unmapped['username'].tolist()))
        first_plip = unmapped['first_plip'].min()
        last_plip = unmapped['last_plip'].max()
        
        company_stats.append({
            'company': 'Independent',
            'total_plips': total_plips,
            'open_plips': open_plips,
            'closed_plips': closed_plips,
            'contributors_count': contributors_count,
            'contributors': contributors_list,
            'repositories_count': repositories_count,
            'repositories': repositories,
            'first_plip': first_plip,
            'last_plip': last_plip
        })
    
    return company_stats

def display_company_statistics(company_stats):
    """Display company statistics"""
    if not company_stats:
        print("No company statistics to display")
        return
    
    # Sort by total PLIPs descending
    company_stats.sort(key=lambda x: x['total_plips'], reverse=True)
    
    print(f"\nPLIP COMPANY STATISTICS")
    print("=" * 50)
    
    total_plips = sum(stat['total_plips'] for stat in company_stats)
    total_companies = len(company_stats)
    total_contributors = sum(stat['contributors_count'] for stat in company_stats)
    
    print(f"Total PLIPs: {total_plips}")
    print(f"Total companies: {total_companies}")
    print(f"Total mapped contributors: {total_contributors}")
    print()
    
    print("TOP COMPANIES BY PLIPS:")
    print("-" * 25)
    print(f"{'Company':<25} {'Total':<6} {'Open':<5} {'Closed':<7} {'Contributors':<12}")
    print("-" * 65)
    
    for stat in company_stats:
        company = stat['company'][:24]  # Truncate long names
        print(f"{company:<25} {stat['total_plips']:<6} {stat['open_plips']:<5} {stat['closed_plips']:<7} {stat['contributors_count']:<12}")

def save_company_statistics(company_stats):
    """Save company statistics to CSV"""
    if not company_stats:
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(company_stats)
    
    # Sort by total PLIPs descending
    df = df.sort_values('total_plips', ascending=False)
    
    # Reorder columns to match company contributor CSV format
    column_order = [
        'company', 'total_plips', 'open_plips', 'closed_plips',
        'contributors_count', 'contributors', 'repositories_count', 
        'repositories', 'first_plip', 'last_plip'
    ]
    df = df[column_order]
    
    # Save to CSV
    filename = 'plone-plip-companies.csv'
    df.to_csv(filename, index=False)
    
    print(f"\nPLIP company statistics saved to: {filename}")
    print(f"Total companies: {len(df)}")

def main():
    """Main function"""
    print("Plone PLIP Company Statistics Generator")
    print("=" * 40)
    
    # Load company mapping
    mapping, companies = load_company_mapping()
    if not mapping:
        return
    
    # Load PLIP contributor data
    plip_df = load_plip_contributors()
    if plip_df is None:
        return
    
    # Aggregate by companies
    company_stats = aggregate_plip_companies(plip_df, mapping, companies)
    
    # Display statistics
    display_company_statistics(company_stats)
    
    # Save to CSV
    save_company_statistics(company_stats)
    
    print(f"\n✅ PLIP company statistics generation completed!")

if __name__ == "__main__":
    main()