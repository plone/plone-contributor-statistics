#!/usr/bin/env python3
"""
Comprehensive Contributor and Organization Report Generator

Generates a markdown report combining individual contributor and organization
statistics across multiple time periods (current year, last full year,
3-year and 10-year summaries).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def load_contributor_file(year):
    """Load contributor statistics for a specific year."""
    filepath = Path(f"data/{year}-plone-contributors.csv")
    if not filepath.exists():
        return None
    try:
        df = pd.read_csv(filepath)
        df['year'] = year
        return df
    except Exception:
        return None


def load_organisation_file(year):
    """Load organisation statistics for a specific year."""
    filepath = Path(f"data/{year}-plone-organisation-contributors.csv")
    if not filepath.exists():
        return None
    try:
        df = pd.read_csv(filepath)
        df['year'] = year
        return df
    except Exception:
        return None


def combine_contributor_data(years):
    """Combine contributor data across multiple years."""
    frames = []
    for year in years:
        df = load_contributor_file(year)
        if df is not None:
            frames.append(df)
    if not frames:
        return None

    all_data = pd.concat(frames, ignore_index=True)
    aggregated = all_data.groupby('username').agg({
        'total_commits': 'sum',
        'total_pull_requests': 'sum',
    }).reset_index()

    # Combine repositories across years
    repo_counts = []
    for username in aggregated['username']:
        user_data = all_data[all_data['username'] == username]
        all_repos = set()
        for repos_str in user_data['repositories'].dropna():
            for repo in str(repos_str).split(', '):
                repo = repo.strip()
                if repo:
                    all_repos.add(repo)
        repo_counts.append(len(all_repos))
    aggregated['repositories_count'] = repo_counts

    return aggregated


def combine_organisation_data(years):
    """Combine organisation data across multiple years."""
    frames = []
    for year in years:
        df = load_organisation_file(year)
        if df is not None:
            frames.append(df)
    if not frames:
        return None

    all_data = pd.concat(frames, ignore_index=True)
    aggregated = all_data.groupby('organisation').agg({
        'total_commits': 'sum',
        'total_pull_requests': 'sum',
    }).reset_index()

    # Combine contributors and repositories across years
    contrib_counts = []
    repo_counts = []
    for org in aggregated['organisation']:
        org_data = all_data[all_data['organisation'] == org]
        all_contribs = set()
        all_repos = set()
        for contribs_str in org_data['contributors'].dropna():
            for c in str(contribs_str).split(', '):
                c = c.strip()
                if c:
                    all_contribs.add(c)
        for repos_str in org_data['repositories'].dropna():
            for r in str(repos_str).split(', '):
                r = r.strip()
                if r:
                    all_repos.add(r)
        contrib_counts.append(len(all_contribs))
        repo_counts.append(len(all_repos))
    aggregated['contributors_count'] = contrib_counts
    aggregated['repositories_count'] = repo_counts

    return aggregated


def format_number(n):
    """Format number with comma separator."""
    return f"{int(n):,}"


def top_contributors_table(df, n=10, sort_by='total_commits'):
    """Generate markdown table for top contributors."""
    df_sorted = df.sort_values(sort_by, ascending=False).head(n)
    lines = []
    if sort_by == 'total_pull_requests':
        lines.append("| Rank | Contributor | PRs | Commits | Total | Repositories |")
        lines.append("|------|-------------|-----|---------|-------|-------------|")
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            total = int(row['total_commits']) + int(row['total_pull_requests'])
            lines.append(
                f"| {i} | {row['username']} | {format_number(row['total_pull_requests'])} "
                f"| {format_number(row['total_commits'])} | {format_number(total)} "
                f"| {int(row['repositories_count'])} |"
            )
    else:
        lines.append("| Rank | Contributor | Commits | PRs | Total | Repositories |")
        lines.append("|------|-------------|---------|-----|-------|-------------|")
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            total = int(row['total_commits']) + int(row['total_pull_requests'])
            lines.append(
                f"| {i} | {row['username']} | {format_number(row['total_commits'])} "
                f"| {format_number(row['total_pull_requests'])} | {format_number(total)} "
                f"| {int(row['repositories_count'])} |"
            )
    return '\n'.join(lines)


def top_organisations_table(df, n=10, sort_by='total_commits'):
    """Generate markdown table for top organisations."""
    df_sorted = df.sort_values(sort_by, ascending=False).head(n)
    lines = []
    if sort_by == 'total_pull_requests':
        lines.append("| Rank | Organization | PRs | Commits | Total | Contributors |")
        lines.append("|------|-------------|-----|---------|-------|-------------|")
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            total = int(row['total_commits']) + int(row['total_pull_requests'])
            lines.append(
                f"| {i} | {row['organisation']} | {format_number(row['total_pull_requests'])} "
                f"| {format_number(row['total_commits'])} | {format_number(total)} "
                f"| {int(row['contributors_count'])} |"
            )
    else:
        lines.append("| Rank | Organization | Commits | PRs | Total | Contributors | Repositories |")
        lines.append("|------|-------------|---------|-----|-------|---------------|-------------|")
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            total = int(row['total_commits']) + int(row['total_pull_requests'])
            lines.append(
                f"| {i} | {row['organisation']} | {format_number(row['total_commits'])} "
                f"| {format_number(row['total_pull_requests'])} | {format_number(total)} "
                f"| {int(row['contributors_count'])} | {int(row['repositories_count'])} |"
            )
    return '\n'.join(lines)


def main():
    print("Plone Contributor Report Generator")
    print("=" * 40)

    now = datetime.now()
    current_year = now.year

    # Find all available years
    available_years = sorted(
        [int(f.name.split('-')[0]) for f in Path('data').glob('[0-9][0-9][0-9][0-9]-plone-contributors.csv')],
        reverse=True
    )

    if not available_years:
        print("No contributor CSV files found!")
        return 1

    print(f"Available years: {', '.join(map(str, available_years))}")

    # Determine the most recent full year
    last_full_year = current_year - 1
    if last_full_year not in available_years:
        last_full_year = available_years[0]

    # Define periods
    current_year_data = current_year if current_year in available_years else None
    three_year = [y for y in range(last_full_year - 2, last_full_year + 1) if y in available_years]
    ten_year = [y for y in range(last_full_year - 9, last_full_year + 1) if y in available_years]

    report = []
    report.append("# Plone Contributor Statistics Report")
    report.append("")
    report.append(f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("This report shows the top contributors and organizations in the Plone ecosystem across different time periods.")
    report.append("")
    report.append("## Data Overview")
    report.append("")
    report.append(f"- **Available years**: {', '.join(map(str, available_years))}")
    if current_year_data:
        report.append(f"- **Current year**: {current_year} (full year)")
    report.append(f"- **Last full year**: {last_full_year}")
    if three_year:
        report.append(f"- **3-year period**: {', '.join(map(str, three_year))}")
    if ten_year:
        report.append(f"- **10-year period**: {', '.join(map(str, ten_year))}")
    report.append("")
    report.append("---")
    report.append("")

    # --- Individual Contributors ---
    report.append("## Individual Contributors")
    report.append("")

    periods = []
    if current_year_data:
        periods.append((f"Current Year - {current_year}", [current_year]))
    periods.append((f"Last Full Year - {last_full_year}", [last_full_year]))
    if len(three_year) >= 2:
        periods.append((f"Past 3 Years: {three_year[0]}-{three_year[-1]}", three_year))
    if len(ten_year) >= 5:
        periods.append((f"Past 10 Years: {ten_year[0]}-{ten_year[-1]}", ten_year))

    for label, years in periods:
        print(f"Processing contributors for {label}...")
        df = combine_contributor_data(years)
        if df is not None and len(df) > 0:
            report.append(f"### Top 10 Individual Contributors ({label})")
            report.append("")
            report.append(top_contributors_table(df, 10, 'total_commits'))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")

    # --- Organizations ---
    report.append("## Organizations")
    report.append("")

    for label, years in periods:
        print(f"Processing organisations for {label}...")
        df = combine_organisation_data(years)
        if df is not None and len(df) > 0:
            report.append(f"### Top 10 Organizations ({label})")
            report.append("")
            report.append(top_organisations_table(df, 10, 'total_commits'))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")

    # --- PR Leaders ---
    report.append("## Pull Request Leaders")
    report.append("")

    for label, years in periods:
        df = combine_contributor_data(years)
        if df is not None and len(df) > 0:
            report.append(f"### Top 10 Pull Request Contributors ({label})")
            report.append("")
            report.append(top_contributors_table(df, 10, 'total_pull_requests'))
            report.append("")
            report.append("")

    report.append("### Organizations by Pull Requests")
    report.append("")

    for label, years in periods:
        df = combine_organisation_data(years)
        if df is not None and len(df) > 0:
            report.append(f"#### Top 10 Organizations by Pull Requests ({label})")
            report.append("")
            report.append(top_organisations_table(df, 10, 'total_pull_requests'))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")
    report.append("## Notes")
    report.append("")
    report.append("- **Commits**: Direct code commits to repositories")
    report.append("- **PRs**: Pull requests submitted (includes both merged and unmerged)")
    report.append("- **Total**: Sum of commits and pull requests")
    report.append("- **Contributors**: Number of individual contributors (for organizations)")
    report.append("- **Repositories**: Number of different repositories contributed to")
    report.append("")
    report.append("Generated by Plone Contributor Statistics Tool")

    # Write report
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "github-contributor-report.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"\nReport saved to: {output_file}")
    return 0


if __name__ == "__main__":
    exit(main())
