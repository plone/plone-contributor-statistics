#!/usr/bin/env python3
"""
Multi-Year Summary Generator for Plone GitHub Statistics

Combines organisation statistics across multiple years into comprehensive
summary reports showing total activity across the specified period.
Supports any combination of years and generates both CSV and TXT outputs.
"""

import pandas as pd
import argparse
import sys
import subprocess
from pathlib import Path


def load_organisation_file(year):
    """Load organisation statistics file for a specific year."""
    filename = f"{year}-plone-organisation-contributors.csv"
    filepath = Path(filename)
    
    if not filepath.exists():
        print(f"❌ Missing file: {filename}")
        print(f"   Run: make run-organisation-stats-{year}")
        return None
    
    try:
        df = pd.read_csv(filepath)
        df['year'] = year
        return df
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return None


def combine_multi_year_stats(years):
    """Combine organisation statistics across multiple years."""
    year_count = len(years)
    year_label = "Multi-Year" if year_count != 3 else "Three-Year"
    print(f"{year_label} Plone Organisation Summary Generator")
    print("=" * 50)
    
    # Load data for each year
    dataframes = []
    for year in years:
        print(f"Loading {year} organisation statistics...")
        df = load_organisation_file(year)
        if df is None:
            return None
        dataframes.append(df)
        print(f"  ✓ Loaded {len(df)} organisations for {year}")
    
    # Combine all years
    print("\nCombining data across years...")
    all_data = pd.concat(dataframes, ignore_index=True)
    
    # Aggregate by organisation across all years
    print("Aggregating statistics by organisation...")
    
    aggregated = all_data.groupby('organisation').agg({
        'total_commits': 'sum',
        'total_pull_requests': 'sum',
        'contributors_count': lambda x: len(set(str(contributors) for contributors in x if pd.notna(contributors))),
        'repositories_count': lambda x: len(set(str(repos) for repos in x if pd.notna(repos))),
        'year': lambda x: sorted(x.unique())
    }).reset_index()
    
    # Create comprehensive contributor and repository lists
    contributor_lists = []
    repository_lists = []
    years_active = []
    first_contributions = []
    last_contributions = []
    
    for org in aggregated['organisation']:
        org_data = all_data[all_data['organisation'] == org]
        
        # Combine contributors across years
        all_contributors = []
        for contributors_str in org_data['contributors']:
            if pd.notna(contributors_str):
                contributors = [c.strip() for c in str(contributors_str).split(',')]
                all_contributors.extend(contributors)
        unique_contributors = sorted(list(set(all_contributors)))
        contributor_lists.append(', '.join(unique_contributors))
        
        # Combine repositories across years  
        all_repositories = []
        for repos_str in org_data['repositories']:
            if pd.notna(repos_str):
                repositories = [r.strip() for r in str(repos_str).split(',')]
                all_repositories.extend(repositories)
        unique_repositories = sorted(list(set(all_repositories)))
        repository_lists.append(', '.join(unique_repositories))
        
        # Years active
        years_active.append(', '.join(map(str, sorted(org_data['year'].unique()))))
        
        # First and last contribution dates across all years
        first_dates = pd.to_datetime(org_data['first_contribution'], errors='coerce')
        last_dates = pd.to_datetime(org_data['last_contribution'], errors='coerce')
        
        first_contributions.append(first_dates.min().strftime('%Y-%m-%d') if not first_dates.isna().all() else '')
        last_contributions.append(last_dates.max().strftime('%Y-%m-%d') if not last_dates.isna().all() else '')
    
    # Add computed columns
    aggregated['contributors'] = contributor_lists
    aggregated['repositories'] = repository_lists
    aggregated['years_active'] = years_active
    aggregated['first_contribution'] = first_contributions
    aggregated['last_contribution'] = last_contributions
    aggregated['repositories_count'] = [len(repos.split(', ')) if repos else 0 for repos in repository_lists]
    aggregated['contributors_count'] = [len(contribs.split(', ')) if contribs else 0 for contribs in contributor_lists]
    
    # Reorder columns for better readability
    column_order = [
        'organisation',
        'total_commits', 
        'total_pull_requests',
        'contributors_count',
        'contributors',
        'repositories_count', 
        'repositories',
        'years_active',
        'first_contribution',
        'last_contribution'
    ]
    
    result = aggregated[column_order]
    
    # Sort by total pull requests descending
    result = result.sort_values('total_pull_requests', ascending=False).reset_index(drop=True)
    
    return result


def save_summary(df, years):
    """Save the multi-year summary to CSV and TXT."""
    year_range = f"{min(years)}-{max(years)}"
    year_count = len(years)
    
    # Generate filenames based on year count
    if year_count == 3:
        csv_filename = f"summary-past-three-years-{year_range}.csv"
        txt_filename = f"STATISTICS-PAST-THREE-YEARS.txt"
        summary_type = "Three-year"
    elif year_count == 5:
        csv_filename = f"summary-past-five-years-{year_range}.csv"
        txt_filename = f"STATISTICS-PAST-FIVE-YEARS.txt"
        summary_type = "Five-year"
    elif year_count == 10:
        csv_filename = f"summary-past-ten-years-{year_range}.csv"
        txt_filename = f"STATISTICS-PAST-TEN-YEARS.txt"
        summary_type = "Ten-year"
    else:
        csv_filename = f"summary-past-{year_count}-years-{year_range}.csv"
        txt_filename = f"STATISTICS-PAST-{year_count}-YEARS.txt"
        summary_type = f"{year_count}-year"
    
    # Save CSV file
    df.to_csv(csv_filename, index=False)
    
    # Prepare text content for both console output and file
    if year_count == 10:
        period_label = "the decade"
    elif year_count == 5:
        period_label = "the past 5 years"
    else:
        period_label = f"{year_count} years"
    
    txt_content = []
    txt_content.append(f"# {summary_type.title()} Summary Results ({year_range})")
    txt_content.append("")
    txt_content.append(f"- {len(df)} total organisations tracked across {period_label}")
    txt_content.append(f"- {df['total_commits'].sum():,} total commits and {df['total_pull_requests'].sum():,} pull requests")
    txt_content.append(f"- {df['contributors_count'].sum()} unique contributors across all organisations")
    txt_content.append(f"- File generated: {csv_filename}")
    
    # Add top individual contributors dynamically
    top_contributors_lines = get_top_contributors(years, year_range)
    if top_contributors_lines:
        txt_content.append("")
        txt_content.append(f"## Top 10 contributors by pull requests ({year_range})")
        txt_content.append("")
        txt_content.extend(top_contributors_lines)
    
    # Add top organisations
    txt_content.append("")
    txt_content.append(f"## Top 10 organisations by pull requests ({year_range})")
    txt_content.append("")
    top_orgs = df.head(10)
    for i, row in top_orgs.iterrows():
        txt_content.append(f"{i+1}. {row['organisation']}: {row['total_pull_requests']:,} PRs ({row['total_commits']:,} commits)")
    
    # Write to TXT file
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_content))
    
    # Print to console
    print(f"\n✅ {summary_type} summary saved to: {csv_filename}")
    print(f"✅ {summary_type} statistics saved to: {txt_filename}")
    
    for line in txt_content:
        print(line)
    
    return csv_filename, txt_filename


def get_top_contributors(years, year_range):
    """Get top contributors dynamically by running the analysis."""
    try:
        # Try to run the top contributors analysis dynamically
        import tempfile
        import os
        
        # Create a temporary script to run the top contributors analysis
        temp_script = f"""
import sys
import os
sys.path.append('.')

# Suppress the verbose output from analyze_top_contributors
original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

from top_contributors_summary import analyze_top_contributors

years = {list(years)}
result_df = analyze_top_contributors(years, 10, 'total_pull_requests')

# Restore stdout and print only our desired format
sys.stdout.close()
sys.stdout = original_stdout

if result_df is not None:
    for i in range(min(10, len(result_df))):
        row = result_df.iloc[i]
        print(f"{{i+1}}. {{row['username']}} - {{row['total_pull_requests']:,}} PRs ({{row['total_commits']:,}} commits)")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(temp_script)
            temp_file = f.name
        
        try:
            result = subprocess.run([sys.executable, temp_file], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                # Parse the captured output (which contains the formatted list)
                lines = result.stdout.strip().split('\n')
                contributor_lines = []
                printed_count = 0
                for line in lines:
                    if line.strip() and (line.strip().startswith(tuple(f"{i}." for i in range(1, 11)))) and printed_count < 10:
                        contributor_lines.append(line.strip())
                        printed_count += 1
                return contributor_lines
            else:
                return ["Individual contributor analysis not available"]
        finally:
            os.unlink(temp_file)
            
    except Exception:
        return ["Individual contributor analysis not available"]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate multi-year summary of Plone organisation statistics'
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        default=[2022, 2023, 2024],
        help='Years to combine (default: 2022 2023 2024)'
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()
    years = sorted(args.years)
    
    year_count = len(years)
    summary_label = f"{year_count}-year" if year_count != 3 else "three-year"
    print(f"Generating {summary_label} summary for: {', '.join(map(str, years))}")
    print()
    
    # Combine statistics
    summary_df = combine_multi_year_stats(years)
    
    if summary_df is None:
        print("❌ Failed to generate summary. Please ensure all required files exist.")
        return 1
    
    # Save results
    csv_filename, txt_filename = save_summary(summary_df, years)
    
    print(f"\n🎉 {summary_label.title()} summary generation completed!")
    print(f"   Generated: {csv_filename}")
    print(f"   Generated: {txt_filename}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())