#!/usr/bin/env python3
"""
PLIP Report Generator

Generates a markdown report showing PLIP (Plone Improvement Proposal) statistics
for individual contributors and organizations across multiple time periods
(last full year, 3-year, 5-year and 10-year summaries).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def load_plips_data():
    """Load PLIP data from plone-plips-detailed.csv."""
    filepath = Path("plone-plips-detailed.csv")
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return None

    try:
        df = pd.read_csv(filepath)
        df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except Exception as e:
        print(f"Error loading PLIP data: {e}")
        return None


def load_organisation_mapping():
    """Load organisation mapping from organisations.csv."""
    filepath = Path("organisations.csv")
    if not filepath.exists():
        print(f"Warning: {filepath} not found, using 'Independent' for all contributors")
        return {}

    try:
        df = pd.read_csv(filepath)
        # Create mapping from username to organisation
        # Format: Organisation,Team (where Team is semicolon-separated usernames)
        mapping = {}
        for _, row in df.iterrows():
            org = row['Organisation']
            team = row['Team']
            if pd.notna(team) and team.strip():
                usernames = [u.strip() for u in team.split(';')]
                for username in usernames:
                    if username:
                        mapping[username] = org
        return mapping
    except Exception as e:
        print(f"Error loading organisation mapping: {e}")
        return {}


def filter_plips_by_years(df, years):
    """Filter PLIPs by year range."""
    if df is None or df.empty:
        return None

    # Filter by years
    df_filtered = df[df['created_at'].dt.year.isin(years)]
    return df_filtered


def aggregate_contributor_plips(df):
    """Aggregate PLIP statistics by contributor."""
    if df is None or df.empty:
        return None

    # Group by author
    aggregated = df.groupby('author').agg({
        'number': 'count',  # Total PLIPs
        'state': lambda x: (x == 'open').sum(),  # Open PLIPs
        'repository': lambda x: x.nunique()  # Unique repositories
    }).reset_index()

    # Rename columns
    aggregated.columns = ['username', 'total_plips', 'open_plips', 'repositories_count']

    # Calculate closed PLIPs
    closed_counts = df.groupby('author')['state'].apply(lambda x: (x == 'closed').sum())
    aggregated['closed_plips'] = aggregated['username'].map(closed_counts)

    return aggregated


def aggregate_organisation_plips(df, org_mapping):
    """Aggregate PLIP statistics by organisation."""
    if df is None or df.empty:
        return None

    # Add organisation column
    df_with_org = df.copy()
    df_with_org['organisation'] = df_with_org['author'].map(
        lambda x: org_mapping.get(x, 'Independent')
    )

    # Group by organisation
    aggregated = df_with_org.groupby('organisation').agg({
        'number': 'count',  # Total PLIPs
        'state': lambda x: (x == 'open').sum(),  # Open PLIPs
        'author': lambda x: x.nunique(),  # Unique contributors
        'repository': lambda x: x.nunique()  # Unique repositories
    }).reset_index()

    # Rename columns
    aggregated.columns = ['organisation', 'total_plips', 'open_plips', 'contributors_count', 'repositories_count']

    # Calculate closed PLIPs
    closed_counts = df_with_org.groupby('organisation')['state'].apply(lambda x: (x == 'closed').sum())
    aggregated['closed_plips'] = aggregated['organisation'].map(closed_counts)

    return aggregated


def format_number(n):
    """Format number with comma separator."""
    return f"{int(n):,}"


def top_contributors_table(df, n=10):
    """Generate markdown table for top PLIP contributors."""
    if df is None or df.empty:
        return "No data available"

    df_sorted = df.sort_values('total_plips', ascending=False).head(n)
    lines = []
    lines.append("| Rank | Contributor | Total PLIPs | Open | Closed | Repositories |")
    lines.append("|------|-------------|-------------|------|--------|-------------|")
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        lines.append(
            f"| {i} | {row['username']} | {format_number(row['total_plips'])} "
            f"| {int(row['open_plips'])} | {int(row['closed_plips'])} "
            f"| {int(row['repositories_count'])} |"
        )
    return '\n'.join(lines)


def top_organisations_table(df, n=10):
    """Generate markdown table for top organisations by PLIPs."""
    if df is None or df.empty:
        return "No data available"

    df_sorted = df.sort_values('total_plips', ascending=False).head(n)
    lines = []
    lines.append("| Rank | Organization | Total PLIPs | Open | Closed | Contributors | Repositories |")
    lines.append("|------|-------------|-------------|------|--------|--------------|-------------|")
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        lines.append(
            f"| {i} | {row['organisation']} | {format_number(row['total_plips'])} "
            f"| {int(row['open_plips'])} | {int(row['closed_plips'])} "
            f"| {int(row['contributors_count'])} | {int(row['repositories_count'])} |"
        )
    return '\n'.join(lines)


def main():
    print("PLIP Report Generator")
    print("=" * 40)

    # Load data
    print("Loading PLIP data...")
    plips_df = load_plips_data()
    if plips_df is None:
        return

    print("Loading organisation mapping...")
    org_mapping = load_organisation_mapping()

    # Determine available years
    all_years = sorted(plips_df['created_at'].dt.year.unique(), reverse=True)
    print(f"Available years: {', '.join(map(str, all_years))}")

    if not all_years:
        print("No PLIP data found")
        return

    # Define time periods
    # Always use the last FULL year (not the current incomplete year)
    current_year = datetime.now().year
    last_full_year = current_year - 1

    # Filter out incomplete current year from available years
    all_years = [y for y in all_years if y < current_year]

    # Verify the last full year exists in data
    if last_full_year not in all_years:
        if all_years:
            last_full_year = all_years[0]  # Use most recent available year
        else:
            print("No complete year data found")
            return

    # Define time periods (all based on complete years only)
    three_years = [y for y in all_years if y >= last_full_year - 2 and y <= last_full_year]
    five_years = [y for y in all_years if y >= last_full_year - 4 and y <= last_full_year]
    ten_years = [y for y in all_years if y >= last_full_year - 9 and y <= last_full_year]

    periods = [
        (f"Last Full Year: {last_full_year}", [last_full_year]),
        (f"Past 3 Years: {min(three_years)}-{max(three_years)}" if three_years else "Past 3 Years", three_years),
        (f"Past 5 Years: {min(five_years)}-{max(five_years)}" if five_years else "Past 5 Years", five_years),
        (f"Past 10 Years: {min(ten_years)}-{max(ten_years)}" if ten_years else "Past 10 Years", ten_years)
    ]

    # Generate report
    report = []
    report.append("# Plone PLIP Statistics Report")
    report.append("")
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("This report shows the top PLIP (Plone Improvement Proposal) contributors and organizations in the Plone ecosystem across different time periods.")
    report.append("")
    report.append("## Data Overview")
    report.append("")
    report.append(f"- **Available years**: {', '.join(map(str, all_years))}")
    report.append(f"- **Last full year**: {last_full_year}")

    if three_years:
        report.append(f"- **3-year period**: {', '.join(map(str, sorted(three_years)))}")
    if five_years:
        report.append(f"- **5-year period**: {', '.join(map(str, sorted(five_years)))}")
    if ten_years:
        report.append(f"- **10-year period**: {', '.join(map(str, sorted(ten_years)))}")

    report.append("")
    report.append("## About PLIPs")
    report.append("")
    report.append("PLIPs (Plone Improvement Proposals) are feature proposals and enhancement requests that shape the future of Plone. ")
    report.append("They are tracked as GitHub issues with the label '03 type: feature (plip)' in the main Plone repositories:")
    report.append("")
    report.append("- Products.CMFPlone")
    report.append("- plone.restapi")
    report.append("- volto")
    report.append("")
    report.append("---")
    report.append("")

    # Individual Contributors Section
    report.append("## Individual Contributors")
    report.append("")

    for label, years in periods:
        print(f"Processing contributors for {label}...")
        filtered_df = filter_plips_by_years(plips_df, years)
        aggregated = aggregate_contributor_plips(filtered_df)

        report.append(f"### Top 10 Contributors ({label})")
        report.append("")
        report.append(top_contributors_table(aggregated, n=10))
        report.append("")
        report.append("")

    report.append("---")
    report.append("")

    # Organisation Contributors Section
    report.append("## Organisation Contributors")
    report.append("")

    for label, years in periods:
        print(f"Processing organisations for {label}...")
        filtered_df = filter_plips_by_years(plips_df, years)
        aggregated = aggregate_organisation_plips(filtered_df, org_mapping)

        report.append(f"### Top 10 Organisation Contributors ({label})")
        report.append("")
        report.append(top_organisations_table(aggregated, n=10))
        report.append("")
        report.append("")

    # Add organisation mapping note
    report.append("---")
    report.append("")
    report.append("### Organisation Mapping")
    report.append("")
    report.append("The mapping from individual contributors to organisations is maintained in the `organisations.csv` file, ")
    report.append("which is publicly available for all Plone community members to review and update via pull requests.")
    report.append("")

    # Save report
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "plips.md"

    with open(output_file, 'w') as f:
        f.write('\n'.join(report))

    print(f"\nReport saved to: {output_file}")
    print("✅ PLIP report generation completed!")


if __name__ == "__main__":
    main()
