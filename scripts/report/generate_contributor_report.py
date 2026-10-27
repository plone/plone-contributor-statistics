#!/usr/bin/env python3
"""
Comprehensive Contributor and Organization Report Generator

Generates a markdown report combining individual contributor and organization
statistics of the last full year and of the past three, five and ten years up
to it, and the changelog entries of 2004-2012 (#71).
"""

import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime

from scripts.lib import paths
from scripts.lib.changelogs import REPORTED_YEARS
from scripts.lib.tables import by_count
from scripts.lib.model import UNMAPPED

COUNTING_RULES = 'https://plone.github.io/plone-contributor-statistics/docs/explanation/counting-rules.html'


def load_contributor_file(year):
    """Load contributor statistics for a specific year."""
    df = pd.read_csv(paths.contributors_file(year))
    df['year'] = year
    return df


def load_organisation_file(year):
    """Load organisation statistics for a specific year."""
    df = pd.read_csv(paths.organisation_contributors_file(year))
    df['year'] = year
    return df


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
    if 'changelog_entries' not in all_data.columns:  # files written before the changelog entries (#71)
        all_data['changelog_entries'] = 0
    aggregated = all_data.groupby('organisation').agg({
        'total_commits': 'sum',
        'total_pull_requests': 'sum',
        'changelog_entries': 'sum',
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


def top_contributors_table(df, n=10):
    """Generate markdown table for top contributors, sorted by PRs."""
    df_sorted = df.sort_values('total_pull_requests', ascending=False).head(n)
    lines = []
    lines.append("| Rank | Contributor | PRs | Commits | Repositories |")
    lines.append("|------|-------------|-----|---------|-------------|")
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        lines.append(
            f"| {i} | {row['username']} | {format_number(row['total_pull_requests'])} "
            f"| {format_number(row['total_commits'])} "
            f"| {int(row['repositories_count'])} |"
        )
    return '\n'.join(lines)


def top_organisations_table(df, n=10):
    """Generate markdown table for top organisations, sorted by PRs.

    Unmapped contributors are not an organisation (#53): they are not ranked,
    but shown in a line below the table.
    """
    unmapped = df[df['organisation'] == UNMAPPED]
    df_sorted = df[df['organisation'] != UNMAPPED].sort_values('total_pull_requests', ascending=False).head(n)
    lines = []
    lines.append("| Rank | Organization | PRs | Commits | Contributors | Repositories |")
    lines.append("|------|-------------|-----|---------|---------------|-------------|")
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        lines.append(
            f"| {i} | {row['organisation']} | {format_number(row['total_pull_requests'])} "
            f"| {format_number(row['total_commits'])} "
            f"| {int(row['contributors_count'])} | {int(row['repositories_count'])} |"
        )
    if not unmapped.empty:
        row = unmapped.iloc[0]
        lines.append("")
        lines.append(
            f"Not mapped to an organisation: {format_number(row['total_pull_requests'])} PRs, "
            f"{format_number(row['total_commits'])} commits by {int(row['contributors_count'])} contributors."
        )
    return '\n'.join(lines)


def combine_changelog_entries(years):
    """Changelog entries and commits per person over the years, for the people with entries.

    `unmatched` is True for names that no identity links to a person.
    """
    frames = [pd.read_csv(paths.changelog_entries_file(year), keep_default_na=False)
              for year in years if paths.changelog_entries_file(year).exists()]
    if not frames:
        return None
    all_data = pd.concat(frames, ignore_index=True)
    all_data['unmatched'] = all_data['matched_by'].astype(str).str.split(';').apply(lambda layers: 'unmatched' in layers)
    entries = all_data.groupby('username', as_index=False).agg({'changelog_entries': 'sum', 'unmatched': 'any'})
    commits = combine_contributor_data(years)[['username', 'total_commits']]
    merged = entries.merge(commits, on='username', how='left')
    merged['total_commits'] = merged['total_commits'].fillna(0).astype(int)
    return merged


def changelog_contributors_table(df, n=10):
    """The people with the most changelog entries, with their commits in the same years."""
    lines = ["| Rank | Contributor | Changelog entries | Commits |",
             "|------|-------------|-------------------|---------|"]
    for i, (_, row) in enumerate(by_count(df, 'changelog_entries', 'username').head(n).iterrows(), 1):
        name = f"*{row['username']}*" if row['unmatched'] else row['username']
        lines.append(f"| {i} | {name} | {format_number(row['changelog_entries'])} | {format_number(row['total_commits'])} |")
    return '\n'.join(lines)


def changelog_organisations_table(df, n=10):
    """The organisations with the most changelog entries; Unmapped is not ranked (#53)."""
    unmapped = df[df['organisation'] == UNMAPPED]
    ranked = by_count(df[df['organisation'] != UNMAPPED], 'changelog_entries', 'organisation').head(n)
    lines = ["| Rank | Organization | Changelog entries | Commits | Contributors |",
             "|------|-------------|-------------------|---------|--------------|"]
    for i, (_, row) in enumerate(ranked.iterrows(), 1):
        lines.append(f"| {i} | {row['organisation']} | {format_number(row['changelog_entries'])} "
                     f"| {format_number(row['total_commits'])} | {int(row['contributors_count'])} |")
    if not unmapped.empty:
        row = unmapped.iloc[0]
        lines.append("")
        lines.append(f"Not mapped to an organisation: {format_number(row['changelog_entries'])} changelog entries, "
                     f"{format_number(row['total_commits'])} commits.")
    return '\n'.join(lines)


def changelog_section(available_years):
    """The section on the changelog entries of the years before pull requests, or [] without data."""
    years = [year for year in REPORTED_YEARS if year in available_years]
    people = combine_changelog_entries(years)
    if people is None or people.empty:
        return []
    label = f"{years[0]}–{years[-1]}"
    lines = [f"## Changelog Entries {label}", ""]
    lines.append("Before pull requests, Plone's changelogs said who made a change: from 2004 on, "
                 "almost every entry ends with the name of the person who made it.")
    lines.append("Each entry counts once, in the year of the release it is listed under, and for every person it names.")
    lines.append("The entries are shown next to the commits of the same years, not added to them.")
    lines.append("Names that no identity links to a person yet are shown as written in the changelogs, in italics.")
    lines.append(f"See [how contributions are counted]({COUNTING_RULES}).")
    lines.append("")
    lines.append(f"### Top 10 Contributors by Changelog Entries ({label})")
    lines.append("")
    lines.append(changelog_contributors_table(people))
    lines.append("")
    lines.append("")
    organisations = combine_organisation_data(years)
    lines.append(f"### Top 10 Organisations by Changelog Entries ({label})")
    lines.append("")
    lines.append(changelog_organisations_table(organisations))
    lines.append("")
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def main():
    print("Plone Contributor Report Generator")
    print("=" * 40)

    now = datetime.now()
    current_year = now.year

    # Find all available years
    available_years = sorted(
        [int(f.name.split('-')[0]) for f in paths.CONTRIBUTORS_DIR.glob('[0-9][0-9][0-9][0-9]-plone-contributors.csv')],
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
    five_year = [y for y in range(last_full_year - 4, last_full_year + 1) if y in available_years]
    ten_year = [y for y in range(last_full_year - 9, last_full_year + 1) if y in available_years]

    report = []
    report.append("# Plone Core Contributor Statistics Report")
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
    if five_year:
        report.append(f"- **5-year period**: {', '.join(map(str, five_year))}")
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
        periods.append((f"Current Year: {current_year}", [current_year]))
    periods.append((f"Last Full Year: {last_full_year}", [last_full_year]))
    if len(three_year) >= 2:
        periods.append((f"Past 3 Years: {three_year[0]}-{three_year[-1]}", three_year))
    if len(five_year) >= 2:
        periods.append((f"Past 5 Years: {five_year[0]}-{five_year[-1]}", five_year))
    if len(ten_year) >= 5:
        periods.append((f"Past 10 Years: {ten_year[0]}-{ten_year[-1]}", ten_year))

    for label, years in periods:
        print(f"Processing contributors for {label}...")
        df = combine_contributor_data(years)
        if df is not None and len(df) > 0:
            report.append(f"### Top 10 Contributors ({label})")
            report.append("")
            report.append(top_contributors_table(df, 10))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")

    # --- Organizations ---
    report.append("## Organisation Contributors")
    report.append("")

    for label, years in periods:
        print(f"Processing organisations for {label}...")
        df = combine_organisation_data(years)
        if df is not None and len(df) > 0:
            report.append(f"### Top 10 Organisation Contributors ({label})")
            report.append("")
            report.append(top_organisations_table(df, 10))
            report.append("")
            report.append("")

    report.append("---")
    report.append("")
    report.extend(changelog_section(available_years))
    report.append("## Notes")
    report.append("")
    report.append("- The tables of contributors and organisations are sorted by number of PRs (descending), "
                  "the tables of changelog entries by number of entries")
    report.append("- **PRs**: Merged pull requests only (excludes open or closed/rejected PRs)")
    report.append("- **Commits**: Direct code commits to repositories")
    report.append("- **Changelog entries**: Entries in the changelogs of the releases, credited to every person they name")
    report.append("- **Contributors**: Number of individual contributors (for organizations)")
    report.append("- **Repositories**: Number of different repositories contributed to")
    report.append("")
    report.append("### Organisation Mapping")
    report.append("")
    report.append("The mapping from individual contributors to organisations is maintained in the `organisations.csv` file, ")
    report.append("which is publicly available for all Plone community members. This makes the mapping transparent and ")
    report.append("traceable for anyone who is interested. If you believe that this mapping does not reflect your actual ")
    report.append("affiliation with an organisation, please create a pull request and we will update the statistics accordingly.")
    report.append("")
    report.append("Generated by Plone Contributor Statistics Tool")

    # Write report
    output_file = paths.CONTRIBUTOR_REPORT
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"\nReport saved to: {output_file}")
    return 0


if __name__ == "__main__":
    # No options; --help says what the script does
    argparse.ArgumentParser(description=__doc__.strip().splitlines()[0]).parse_args()
    exit(main())
