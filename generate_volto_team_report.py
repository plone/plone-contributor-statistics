#!/usr/bin/env python3
"""
Volto Team Report Generator

Generates a markdown report of Volto team contributor statistics
across multiple time periods.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def load_year(year):
    filepath = Path(f"data/{year}-volto-stats.csv")
    if not filepath.exists():
        return None
    try:
        df = pd.read_csv(filepath)
        df['year'] = year
        return df
    except Exception:
        return None


def load_mapping(mapping_file='organisations.csv'):
    """
    Load organisation mapping from CSV file.

    The mapping file should have columns: Organisation, Team
    where Team contains semicolon-separated GitHub usernames.

    Args:
        mapping_file: Path to the organisations.csv file

    Returns:
        dict: Mapping of github_username -> organisation name
    """
    import csv
    from pathlib import Path

    if not Path(mapping_file).exists():
        print(f"Warning: {mapping_file} not found. All contributors will be marked as Independent.")
        return {}

    mapping = {}
    with open(mapping_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            org = row['Organisation']
            for c in row['Team'].split(';'):
                c = c.strip()
                if c:
                    mapping[c] = org

    print(f"Loaded organisation mapping: {len(mapping)} users mapped to organisations")
    return mapping


def combine(years):
    frames = [load_year(y) for y in years]
    frames = [f for f in frames if f is not None]
    if not frames:
        return None
    combined = pd.concat(frames).groupby('github_username').agg(
        {'pull_requests': 'sum', 'commits': 'sum'}
    ).reset_index()
    # Exclude contributors with 0 PRs and 0 commits
    combined = combined[(combined['pull_requests'] > 0) | (combined['commits'] > 0)]
    return combined.sort_values('pull_requests', ascending=False)


def combine_orgs(years, mapping):
    """
    Combine organisation statistics across multiple years.

    Args:
        years: List of years to include
        mapping: dict mapping github_username -> organisation name

    Returns:
        DataFrame with columns: organisation, PRs, Commits, Contributors
    """
    frames = [load_year(y) for y in years]
    frames = [f for f in frames if f is not None]
    if not frames:
        return None
    df = pd.concat(frames)

    # Apply organisation mapping - unmapped users become "Independent"
    df['organisation'] = df['github_username'].map(mapping).fillna('Independent')

    # Show mapping statistics
    total_users = df['github_username'].nunique()
    mapped_users = df[df['organisation'] != 'Independent']['github_username'].nunique()
    print(f"  Organisation mapping: {mapped_users}/{total_users} unique contributors mapped to organisations")

    agg = df.groupby('organisation').agg(
        PRs=('pull_requests', 'sum'),
        Commits=('commits', 'sum'),
        Contributors=('github_username', 'nunique'),
    ).reset_index()
    # Exclude organizations with 0 PRs and 0 commits
    agg = agg[(agg['PRs'] > 0) | (agg['Commits'] > 0)]
    return agg.sort_values('PRs', ascending=False)


def format_number(n):
    return f"{int(n):,}"


def table(df):
    lines = []
    lines.append("| Rank | Contributor | PRs | Commits |")
    lines.append("|------|-------------|-----|---------|")
    for i, (_, row) in enumerate(df.iterrows(), 1):
        lines.append(
            f"| {i} | {row['github_username']} "
            f"| {format_number(row['pull_requests'])} "
            f"| {format_number(row['commits'])} |"
        )
    return '\n'.join(lines)


def org_table(df):
    lines = []
    lines.append("| Rank | Organisation | PRs | Commits | Contributors |")
    lines.append("|------|-------------|-----|---------|--------------|")
    for i, (_, row) in enumerate(df.iterrows(), 1):
        lines.append(
            f"| {i} | {row['organisation']} "
            f"| {format_number(row['PRs'])} "
            f"| {format_number(row['Commits'])} "
            f"| {int(row['Contributors'])} |"
        )
    return '\n'.join(lines)


def main():
    now = datetime.now()

    print("=" * 60)
    print("Volto Team Report Generator")
    print("=" * 60)
    print()

    # Load organisation mapping from organisations.csv
    mapping = load_mapping()
    print()

    available_years = sorted(
        [int(f.name.split('-')[0]) for f in Path('data').glob('[0-9][0-9][0-9][0-9]-volto-stats.csv')],
        reverse=True
    )

    if not available_years:
        print("ERROR: No volto-stats CSV files found in data/!")
        print("Please run volto_stats.py first to generate the data files.")
        return 1

    last_full_year = now.year - 1
    if last_full_year not in available_years:
        last_full_year = available_years[0]

    three_years = [y for y in available_years if y >= last_full_year - 2]
    all_years = available_years

    report = []
    report.append("# Volto Statistics Report")
    report.append("")
    report.append(f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(f"- **Available years**: {', '.join(map(str, available_years))}")
    report.append(f"- **Last full year**: {last_full_year}")
    report.append(f"- **3-year period**: {min(three_years)}-{max(three_years)}")
    report.append(f"- **All time**: {min(all_years)}-{max(all_years)}")
    report.append("")
    report.append("---")
    report.append("")

    periods = [
        (f"Last Full Year - {last_full_year}", [last_full_year]),
        (f"Past 3 Years: {min(three_years)}-{max(three_years)}", three_years),
        (f"All Time: {min(all_years)}-{max(all_years)}", all_years),
    ]

    print("Generating contributor statistics...")
    for label, years in periods:
        df = combine(years)
        if df is not None:
            print(f"  ✓ {label}: {len(df)} contributors")
            report.append(f"## Volto Contributors ({label})")
            report.append("")
            report.append(table(df))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")
    report.append("## Organisations")
    report.append("")

    print()
    print("Generating organisation statistics...")
    for label, years in periods:
        df = combine_orgs(years, mapping)
        if df is not None:
            print(f"  ✓ {label}: {len(df)} organisations")
            report.append(f"### Organisations ({label})")
            report.append("")
            report.append(org_table(df))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")
    report.append("## Notes")
    report.append("")
    report.append("- **PRs**: Merged pull requests to plone/volto (does not include open or closed/rejected PRs)")
    report.append("- **Commits**: Direct commits to plone/volto")
    report.append("- **Contributors**: Number of team members from this organisation")
    report.append("")
    report.append("Generated by Plone Contributor Statistics Tool")

    out = Path("reports/volto.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text('\n'.join(report))

    print()
    print("=" * 60)
    print(f"✓ Report saved to {out}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
