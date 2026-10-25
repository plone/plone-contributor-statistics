#!/usr/bin/env python3
"""
Generate Community Recognition Report

This script calculates community recognition points based on various contribution
categories and generates both a CSV file and a detailed markdown report.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import argparse

from scripts.lib import paths
from scripts.lib.model import (IN_PERSON, MIN_EPISODES, TALK_TYPES, UNMAPPED, community_folder, community_years, items,
                               load_registry, recognition_levels)
from scripts.lib.model.registers import PERSON_PREFIX
from scripts.lib.years import RECOGNITION_YEAR
from scripts.derive.plip_organisation_stats import organisation_lookup, plips_by_organisation, read_plips

# The recognition year: community work of this year, code of the five years up to it
YEAR = RECOGNITION_YEAR


def five_years(year):
    """The "past five years" of the points file, up to and including the recognition year."""
    return range(year - 4, year + 1)


def load_recognition_levels(path=None):
    """The recognition levels (default: the curated file); the top level has no maximum, `inf`."""
    return [{'name': row['Level'].strip(), 'min_points': row['Min Points'],
             'max_points': float('inf') if row['Max Points'] is None else row['Max Points'],
             'description': (row['Description'] or '').strip()} for row in recognition_levels(path)]


def get_recognition_level(points, levels):
    """The highest level whose minimum the points reach.

    Points can be fractions, because shared events split their points, so a
    level applies from its minimum up to the next level's minimum: 9.5 points
    are still Bronze when Silver starts at 10.
    """
    reached = [level for level in levels if level['min_points'] <= points]
    return max(reached, key=lambda level: level['min_points'])['name'] if reached else 'No Level'


def load_pr_data(years, data_dir=paths.ORGANISATION_CONTRIBUTORS_DIR):
    """Merged PRs per organisation over the years, from the yearly organisation files.

    `rows` says where each count comes from: (year, file, line) for each row of the organisation.
    """
    totals = defaultdict(int)
    rows = defaultdict(list)
    for year in years:
        path = f'{data_dir}/{year}-plone-organisation-contributors.csv'
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['organisation'].strip()
                totals[org] += int(row['total_pull_requests'])
                rows[org].append((str(year), path, reader.line_num))
    return {org: {'total_prs': total, 'avg_per_year': total / len(years), 'rows': tuple(rows[org])}
            for org, total in totals.items()}


def load_plip_data(years, plips_file=paths.PLIPS_DETAILED, registry=None):
    """PLIPs closed in the years, for the author's organisation in the year of closing (#95)."""
    plips = read_plips(plips_file)
    groups = plips_by_organisation(plips, organisation_lookup(registry=registry), years=set(years), closed_only=True)
    return {org: {'closed_plips': len(org_plips)} for org, org_plips in groups.items()}


def require_community_year(community, year):
    """Raise if the curated community data of the year is missing altogether.

    A single missing kind of data is only a warning: some kinds didn't exist in every year.
    """
    folder = Path(community)
    if not folder.is_dir():
        raise FileNotFoundError(f'community data folder {folder} not found')
    if year not in community_years(folder):
        raise FileNotFoundError(f'no curated community data for {year} in {folder}')


@dataclass(frozen=True)
class Contribution:
    """Where points come from: the row of a file, and its public record if it has one.

    Points that add up several files list their rows as (label, file, line) in `rows`.
    """
    text: str
    points: float
    file: str = None
    line: int = None
    source: str = None
    rows: tuple = ()


def _items(year, kind, community_dir):
    """The rows of a kind of the year; a warning when there are none.

    Some kinds of community data didn't exist in every year, so a kind without rows is not an error.
    """
    found = items(year, kind, community_dir)
    if not found:
        print(f"Warning: no {kind} rows for {year}")
    return found


def _name(registry, person_id, item):
    """The display name of a person of a row; KeyError, naming the file and row, for an id the register lacks."""
    if person_id not in registry.people:
        raise KeyError(f'{item.file}:{item.line}: "{person_id}" is not in the people register')
    return registry.display_name(f'{PERSON_PREFIX}{person_id}')


def _organisations(registry, item):
    """The names of the organisations a row names, in its order; an empty cell names none."""
    return [registry.organisation_name(org_id) for org_id in item.organisations if org_id]


def strategic_sprint_points(rows, year, registry, add):
    """12 points per strategic sprint, split among its organisations; one sprint per organisation and year."""
    rewarded = set()
    for item in rows:
        if item.fields['level'] != 'strategic':
            continue
        orgs = _organisations(registry, item)
        for org in orgs:
            if org in rewarded:
                continue
            add(org, 'Strategic Sprint', item.key, 12 / len(orgs), item.file, item.line, item.source)
        rewarded.update(orgs)


def release_manager_points(rows, year, registry, add):
    """12 points per release manager, for the organisation of the person in the year."""
    for item in rows:
        for person in item.people:
            add(registry.organisation_of(person, year), 'Release Manager', _name(registry, person, item), 12,
                item.file, item.line, item.source)


def team_leader_points(rows, year, registry, add):
    """6 points per team, split among its leaders, each share for the leader's organisation."""
    teams = defaultdict(list)
    for item in rows:
        for person in item.people:
            teams[(item.fields['team'] or '').strip()].append((person, item))
    for team, leaders in teams.items():
        for person, item in leaders:
            add(registry.organisation_of(person, year), 'Team Leader', f"{_name(registry, person, item)} ({team})",
                6 / len(leaders), item.file, item.line, item.source)


def board_member_points(rows, year, registry, add):
    """6 points per member of the Board, for the organisation of the person in the year."""
    for item in rows:
        for person in item.people:
            add(registry.organisation_of(person, year), 'Board Member', _name(registry, person, item), 6,
                item.file, item.line, item.source)


def podcast_points(rows, year, registry, add):
    """6 points per series with at least MIN_EPISODES episodes in the year, split among its hosts.

    A row without a person records a series without a known host: it is no host and takes no share.
    """
    series = defaultdict(list)
    for item in rows:
        if (item.fields['episodes'] or 0) < MIN_EPISODES:
            continue
        for person in item.people:
            series[item.key].append((person, item))
    for name, hosts in series.items():
        for person, item in hosts:
            add(registry.organisation_of(person, year), 'Podcast Host', f'{_name(registry, person, item)} ({name})',
                6 / len(hosts), item.file, item.line, item.source)


def world_plone_day_event_points(rows, year, registry, add):
    """3 points per local event held in person or hybrid, split among its organisations (#118)."""
    for item in rows:
        if (item.fields['format'] or '').strip() not in IN_PERSON:
            continue
        orgs = _organisations(registry, item)
        for org in orgs:
            add(org, 'WPD Event', f"Organized WPD Event in {item.key}", 3 / len(orgs), item.file, item.line,
                item.source)


def world_plone_day_talk_points(rows, year, registry, add):
    """1 point per talk for each organisation behind it, at most 4 per organisation and year.

    The organisations of a talk are those of its speakers in the year and those the row names, for a talk
    by a team. Only talks count, not teasers, streams, openings or podcast episodes (#119).
    """
    talks = defaultdict(int)
    for item in rows:
        if (item.fields['type'] or '').strip() not in TALK_TYPES:
            continue
        speakers = [registry.organisation_of(person, year) for person in item.people]
        for org in dict.fromkeys(speakers + _organisations(registry, item)):
            if org == UNMAPPED or talks[org] >= 4:
                continue
            talks[org] += 1
            add(org, 'WPD Talk', item.key, 1, item.file, item.line, item.source)


def conference_points(rows, year, registry, add):
    """24 points split among the rows that name an organisation; a row without one takes no share."""
    organisers = [(org, item) for item in rows for org in _organisations(registry, item)]
    for org, item in organisers:
        add(org, 'Conference Organization', f'Organized Plone Conference {year}', 24 / len(organisers),
            item.file, item.line, item.source)


def training_points(rows, year, registry, add):
    """4 points per training, split among its trainers, each share for the trainer's organisation in the year."""
    for item in rows:
        for person in item.people:
            add(registry.organisation_of(person, year), 'Training Session', item.key, 4 / len(item.people),
                item.file, item.line, item.source)


# The points from the curated community files, by file kind, in the order of community-recognition-points.csv.
# An organiser role (of a sprint or a conference) is no point source: the organisations of the event are.
COMMUNITY_RULES = (
    ('sprints', strategic_sprint_points),
    ('release-managers', release_manager_points),
    ('team-leaders', team_leader_points),
    ('board-of-directors', board_member_points),
    ('podcasts', podcast_points),
    ('world-plone-day-event', world_plone_day_event_points),
    ('world-plone-day-talks', world_plone_day_talk_points),
    ('plone-conference', conference_points),
    ('plone-conference-trainings', training_points),
)


def calculate_community_recognition_points(year=YEAR, data_dir=paths.ORGANISATION_CONTRIBUTORS_DIR,
                                           community_dir=None, plips_file=paths.PLIPS_DETAILED,
                                           registry=None, contributions=None):
    """Calculate the points of the recognition year, as community-recognition-points.csv says.

    People in the community files count for their organisation in the year, from the registers. If
    `contributions` is a dict, it is filled with the Contribution behind each point:
    {organisation: {category: [Contribution, ...]}}.
    """
    org_points = defaultdict(lambda: defaultdict(float))
    org_details = defaultdict(lambda: defaultdict(list))
    found = defaultdict(lambda: defaultdict(list))

    def add(org, category, text, points, file=None, line=None, source=None, rows=()):
        org_points[org][category] += points
        org_details[org][category].append(text)
        found[org][category].append(Contribution(text, points, file, line, source or None, rows))

    community_dir = community_folder(community_dir)
    require_community_year(community_dir, year)
    registry = registry or load_registry()

    # Load code contribution data (PRs and PLIPs)
    pr_data = load_pr_data(five_years(year), data_dir)
    plip_data = load_plip_data(five_years(year), plips_file, registry)

    # 1.-9. Community contributions
    for kind, rule in COMMUNITY_RULES:
        rule(_items(year, kind, community_dir), year, registry, add)

    # 10. Pull request contributions - average per year over the past five years
    # Criteria: Lead (100+/yr=20pts), Core Member (50-99/yr=10pts), Active Member (20-49/yr=4pts),
    # Team Member (10-19/yr=2pts)
    for org, data in pr_data.items():
        avg_prs = data['avg_per_year']
        if avg_prs >= 100:
            points = 20
            level = 'Lead'
        elif avg_prs >= 50:
            points = 10
            level = 'Core Member'
        elif avg_prs >= 20:
            points = 4
            level = 'Active Member'
        elif avg_prs >= 10:
            points = 2
            level = 'Team Member'
        else:
            continue  # Less than 10 PRs/year, no points

        add(org, 'PR Contributions', f"{level} ({avg_prs:.1f} PRs/year)", points, str(data_dir), rows=data['rows'])

    # 11. PLIP contributions - PLIPs closed in the past five years
    # Criteria: Significant PLIP Contributor (10+=15pts), Regular PLIP Contributor (6+=9pts),
    # Occasional PLIP Contributor (2+=3pts)
    for org, data in plip_data.items():
        total_plips = data['closed_plips']  # closed counts as "merged and released"
        if total_plips >= 10:
            points = 15
            level = 'Significant PLIP Contributor'
        elif total_plips >= 6:
            points = 9
            level = 'Regular PLIP Contributor'
        elif total_plips >= 2:
            points = 3
            level = 'Occasional PLIP Contributor'
        else:
            continue  # Less than 2 PLIPs, no points

        add(org, 'PLIP Contributions', f"{level} ({total_plips} PLIPs)", points, str(plips_file))

    if contributions is not None:
        contributions.update(exclude_unmapped(found))
    return exclude_unmapped(org_points), exclude_unmapped(org_details)


def exclude_unmapped(by_organisation):
    """Unmapped contributors are not an organisation: no points, no level (#53)."""
    return {org: value for org, value in by_organisation.items() if org and org != UNMAPPED}


def write_csv_report(org_points, levels, output_file):
    """Write the community recognition points to a CSV file."""

    # Calculate totals and create output
    results = []
    for org in sorted(org_points.keys()):
        categories = org_points[org]
        total = sum(categories.values())
        level = get_recognition_level(total, levels)

        row = {
            'Organisation': org,
            'Recognition Level': level,
            'Strategic Sprint': categories.get('Strategic Sprint', 0),
            'Release Manager': categories.get('Release Manager', 0),
            'Team Leader': categories.get('Team Leader', 0),
            'Board Member': categories.get('Board Member', 0),
            'Podcast Host': categories.get('Podcast Host', 0),
            'WPD Event': categories.get('WPD Event', 0),
            'WPD Talk': categories.get('WPD Talk', 0),
            'Conference Organization': categories.get('Conference Organization', 0),
            'Training Session': categories.get('Training Session', 0),
            'PR Contributions': categories.get('PR Contributions', 0),
            'PLIP Contributions': categories.get('PLIP Contributions', 0),
            'Total Points': total
        }
        results.append(row)

    # Write to CSV
    fieldnames = ['Organisation', 'Recognition Level', 'Strategic Sprint', 'Release Manager', 'Team Leader',
                  'Board Member', 'Podcast Host', 'WPD Event', 'WPD Talk',
                  'Conference Organization', 'Training Session', 'PR Contributions', 'PLIP Contributions', 'Total Points']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(results, key=lambda x: x['Total Points'], reverse=True):
            writer.writerow(row)

    return results


def write_markdown_report(org_points, org_details, results, levels, output_file, year=YEAR):
    """Write a detailed markdown report."""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        # Header
        f.write(f"# Plone Community Recognition Program {year}\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Organizations**: {len(results)}\n")
        total_points = sum(r['Total Points'] for r in results)
        f.write(f"- **Total Points Awarded**: {total_points:.1f}\n")
        f.write(f"- **Average Points per Organization**: {total_points/len(results):.1f}\n\n")

        # Recognition Levels
        f.write("## Recognition Levels\n\n")
        f.write("| Level | Points Range | Organizations |\n")
        f.write("|-------|--------------|---------------:|\n")

        # Count organizations by level
        level_counts = defaultdict(int)
        for row in results:
            level_counts[row['Recognition Level']] += 1

        # Display levels from highest to lowest
        for level in reversed(levels):
            level_name = level['name']
            if level['max_points'] == float('inf'):
                points_range = f"{level['min_points']}+"
            else:
                points_range = f"{level['min_points']}-{level['max_points']}"
            count = level_counts.get(level_name, 0)
            f.write(f"| {level_name} | {points_range} | {count} |\n")
        f.write("\n")

        # Point Categories
        f.write("## Recognition Categories\n\n")
        f.write("### Community Contributions\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Strategic Sprint | 12 | Organize/host a strategic sprint (split among organizers, one sprint per organization) |\n")
        f.write("| Release Manager | 12 | Serve as a release manager |\n")
        f.write("| Team Leader | 6 | Lead a community team (split among co-leaders) |\n")
        f.write("| Board Member | 6 | Serve on the Foundation Board |\n")
        f.write("| Conference Organization | 24 | Organize Plone Conference (split among organizers) |\n")
        f.write("| Training Session | 4 | Host training at Plone Conference (split among co-trainers) |\n\n")
        f.write("### Marketing Contributions\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Podcast Host | 6 | Host a Plone podcast or live series with at least five episodes in the year (split among hosts) |\n")
        f.write("| WPD Event | 3 | Organize World Plone Day event (split among organizers) |\n")
        f.write("| WPD Talk | 1 | Give World Plone Day talk (max 4 per org) |\n\n")
        f.write(f"### Code Contributions ({year - 4}–{year})\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Lead (PR) | 20 | 100+ PRs/year average |\n")
        f.write("| Core Member (PR) | 10 | 50-99 PRs/year average |\n")
        f.write("| Active Member (PR) | 4 | 20-49 PRs/year average |\n")
        f.write("| Team Member (PR) | 2 | 10-19 PRs/year average |\n")
        f.write("| Significant PLIP Contributor | 15 | 10+ PLIPs closed |\n")
        f.write("| Regular PLIP Contributor | 9 | 6+ PLIPs closed |\n")
        f.write("| Occasional PLIP Contributor | 3 | 2+ PLIPs closed |\n\n")

        # Leaderboard
        f.write("## Recognition Leaderboard\n\n")
        f.write("| Rank | Organization | Recognition Level | Total Points |\n")
        f.write("|------|--------------|-------------------|-------------:|\n")
        for i, row in enumerate(sorted(results, key=lambda x: x['Total Points'], reverse=True), 1):
            f.write(f"| {i} | {row['Organisation']} | {row['Recognition Level']} | {row['Total Points']:.1f} |\n")
        f.write("\n")

        # Code Contribution Highlights
        f.write("## Code Contribution Highlights\n\n")

        # PR Contributions
        f.write("### Pull Request Contributors (Past 5 Years)\n\n")
        pr_contributors = [(row['Organisation'], row['PR Contributions'], org_details[row['Organisation']].get('PR Contributions', []))
                          for row in results if row['PR Contributions'] > 0]

        # Sort by PRs/year (extracted from detail string)
        def extract_prs_year(contributor):
            details = contributor[2]
            if details and "PRs/year)" in details[0]:
                try:
                    return float(details[0].split("(")[1].split(" PRs/year")[0])
                except:
                    return 0
            return 0
        pr_contributors.sort(key=extract_prs_year, reverse=True)

        if pr_contributors:
            f.write("| Rank | Organization | Points | Level | PRs/Year |\n")
            f.write("|------|--------------|-------:|:------|----------|\n")
            for i, (org, points, details) in enumerate(pr_contributors, 1):
                level_detail = details[0] if details else ""
                # Extract PRs/year from detail string like "Lead Contributor (187.6 PRs/year)"
                prs_year = ""
                if "PRs/year)" in level_detail:
                    prs_year = level_detail.split("(")[1].split(" PRs/year")[0]
                level_name = level_detail.split(" (")[0] if level_detail else ""
                f.write(f"| {i} | {org} | {points:.0f} | {level_name} | {prs_year} |\n")
            f.write("\n")

        # PLIP Contributions
        f.write("### PLIP Contributors\n\n")
        plip_contributors = [(row['Organisation'], row['PLIP Contributions'], org_details[row['Organisation']].get('PLIP Contributions', []))
                            for row in results if row['PLIP Contributions'] > 0]

        # Sort by PLIP count (extracted from detail string)
        def extract_plip_count(contributor):
            details = contributor[2]
            if details and "PLIPs)" in details[0]:
                try:
                    return int(details[0].split("(")[1].split(" PLIPs")[0])
                except:
                    return 0
            return 0
        plip_contributors.sort(key=extract_plip_count, reverse=True)

        if plip_contributors:
            f.write("| Rank | Organization | Points | Level | PLIPs |\n")
            f.write("|------|--------------|-------:|:------|-------|\n")
            for i, (org, points, details) in enumerate(plip_contributors, 1):
                level_detail = details[0] if details else ""
                # Extract PLIP count from detail string like "Core Leaders (71 PLIPs)"
                plip_count = ""
                if "PLIPs)" in level_detail:
                    plip_count = level_detail.split("(")[1].split(" PLIPs")[0]
                level_name = level_detail.split(" (")[0] if level_detail else ""
                f.write(f"| {i} | {org} | {points:.0f} | {level_name} | {plip_count} |\n")
            f.write("\n")

        # Detailed Breakdown
        f.write("## Detailed Breakdown by Organization\n\n")

        for row in sorted(results, key=lambda x: x['Total Points'], reverse=True):
            org = row['Organisation']
            total = row['Total Points']

            f.write(f"### {org}\n\n")
            f.write(f"**Total Points: {total:.1f}**\n\n")

            # Create category breakdown table
            categories_with_points = []
            for cat in ['Strategic Sprint', 'Release Manager', 'Team Leader', 'Board Member',
                       'Podcast Host', 'WPD Event', 'WPD Talk', 'Conference Organization',
                       'Training Session', 'PR Contributions', 'PLIP Contributions']:
                if row[cat] > 0:
                    categories_with_points.append((cat, row[cat]))

            if categories_with_points:
                f.write("| Category | Points | Details |\n")
                f.write("|----------|-------:|:--------|\n")

                for cat, points in categories_with_points:
                    details = org_details[org].get(cat, [])
                    if details:
                        detail_str = "<br>".join([f"• {d}" for d in details[:5]])
                        if len(details) > 5:
                            detail_str += f"<br>• ... and {len(details) - 5} more"
                    else:
                        detail_str = "—"
                    f.write(f"| {cat} | {points:.1f} | {detail_str} |\n")
                f.write("\n")

        # Category Statistics
        f.write("## Statistics by Category\n\n")

        category_stats = defaultdict(lambda: {'orgs': 0, 'total_points': 0})
        for row in results:
            for cat in ['Strategic Sprint', 'Release Manager', 'Team Leader', 'Board Member',
                       'Podcast Host', 'WPD Event', 'WPD Talk', 'Conference Organization',
                       'Training Session', 'PR Contributions', 'PLIP Contributions']:
                if row[cat] > 0:
                    category_stats[cat]['orgs'] += 1
                    category_stats[cat]['total_points'] += row[cat]

        f.write("| Category | Organizations | Total Points Awarded |\n")
        f.write("|----------|---------------:|---------------------:|\n")
        for cat in ['Strategic Sprint', 'Release Manager', 'Team Leader', 'Board Member',
                   'Podcast Host', 'WPD Event', 'WPD Talk', 'Conference Organization',
                   'Training Session', 'PR Contributions', 'PLIP Contributions']:
            stats = category_stats[cat]
            f.write(f"| {cat} | {stats['orgs']} | {stats['total_points']:.1f} |\n")
        f.write("\n")

        # Footer
        f.write("---\n\n")
        f.write("*This report was automatically generated from community contribution data.*\n")

    print(f"Markdown report written to: {output_file}")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Calculate the community recognition points and levels of a year')
    parser.add_argument('--year', type=int, default=YEAR, help=f'Recognition year (default: {YEAR})')
    return parser.parse_args()


def main():
    """Main execution function."""
    year = parse_arguments().year

    print("Calculating community recognition points...")
    org_points, org_details = calculate_community_recognition_points(year=year)

    print(f"Found {len(org_points)} organizations")

    # Load recognition levels
    print("Loading recognition levels...")
    levels = load_recognition_levels()

    # Write CSV report
    csv_output = paths.recognition_report_file(year)
    results = write_csv_report(org_points, levels, csv_output)
    print(f"CSV report written to: {csv_output}")

    # Write Markdown report
    md_output = paths.RECOGNITION_REPORT
    write_markdown_report(org_points, org_details, results, levels, md_output, year=year)

    # Print summary
    print(f"\nTop 10 Organizations:")
    print(f"{'Rank':<6} {'Organisation':<40} {'Level':<25} {'Points':>10}")
    print("=" * 83)
    for i, row in enumerate(sorted(results, key=lambda x: x['Total Points'], reverse=True)[:10], 1):
        print(f"{i:<6} {row['Organisation']:<40} {row['Recognition Level']:<25} {row['Total Points']:>10.1f}")

    print("\nDone!")


if __name__ == '__main__':
    main()
