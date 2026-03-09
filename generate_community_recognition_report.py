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


def load_recognition_levels():
    """Load recognition levels from CSV file."""
    levels = []
    try:
        with open('data/community-contributions/community-recognition-levels.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                level = {
                    'name': row['Level'].strip(),
                    'min_points': int(row['Min Points'].strip()),
                    'max_points': float('inf') if not row['Max Points'].strip() else int(row['Max Points'].strip()),
                    'description': row['Description'].strip()
                }
                levels.append(level)
    except FileNotFoundError:
        print("Warning: community-recognition-levels.csv not found")

    return levels


def get_recognition_level(points, levels):
    """Determine the recognition level for a given point total."""
    for level in levels:
        if level['min_points'] <= points <= level['max_points']:
            return level['name']
    return 'No Level'


def normalize_organization_name(org_name):
    """Normalize organization names to handle different naming conventions."""
    # Mapping of variations to canonical names
    org_mapping = {
        'kitconcept': 'kitconcept GmbH',
        'py76': 'PY76',
        'eau-de-web': 'Eau de Web',
        'redturtle': 'RedTurtle',
        'kleinundpartner': 'Klein & Partner KG',
        'klein und partner': 'Klein & Partner KG',
        'nuclia': 'Nuclia',
        'starzel': 'Starzel',
        'codesyntax': 'CodeSyntax',
        'syslab': 'Syslab',
        'freitag': 'Freitag',
        'kombinat': 'Kombinat',
        'agitator': 'Agitator',
        'derico': 'Derico',
        'rohberg': 'Rohberg',
        'vangheem': 'Vangheem',
        'serpro': 'SERPRO',
        'iskra': 'Iskra',
        'university-hospital-dresden': 'University Hospital Dresden',
        'dbain': 'DBA Informatica Notariaal',
        'iham': 'IHAM',
        'pretaweb': 'Pretaweb',
        'zopyx': 'ZOPYX',
        'tkimnguyen': 'Kim Nguyen',
        'stevepiercy': 'Steve Piercy',
        'independent': 'Independent',
    }

    # Try to find a mapping, otherwise return the original name
    normalized = org_mapping.get(org_name.lower(), org_name)
    return normalized


def load_pr_data():
    """Load PR statistics from past 5 years summary."""
    pr_stats = {}
    try:
        with open('summary-past-five-years-2020-2024.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['organisation'].strip())
                total_prs = int(row['total_pull_requests'])
                avg_prs_per_year = total_prs / 5  # 5 years
                pr_stats[org] = {
                    'total_prs': total_prs,
                    'avg_per_year': avg_prs_per_year
                }
    except FileNotFoundError:
        print("Warning: summary-past-five-years-2020-2024.csv not found")
    except Exception as e:
        print(f"Warning: Error loading PR data: {e}")

    return pr_stats


def load_plip_data():
    """Load PLIP statistics."""
    plip_stats = {}
    try:
        with open('plone-plip-organisations.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['organisation'].strip())
                # Note: Using total_plips as all-time count
                # Ideally we'd filter to past 5 years, but data doesn't have dates
                total_plips = int(row['total_plips'])
                closed_plips = int(row['closed_plips'])
                plip_stats[org] = {
                    'total_plips': total_plips,
                    'closed_plips': closed_plips
                }
    except FileNotFoundError:
        print("Warning: plone-plip-organisations.csv not found")
    except Exception as e:
        print(f"Warning: Error loading PLIP data: {e}")

    return plip_stats


def calculate_community_recognition_points():
    """Calculate community recognition points from all contribution data."""

    # Initialize points tracking
    org_points = defaultdict(lambda: defaultdict(float))
    org_details = defaultdict(lambda: defaultdict(list))

    data_dir = 'data/community-contributions'

    # Load code contribution data (PRs and PLIPs)
    pr_data = load_pr_data()
    plip_data = load_plip_data()

    # 1. Strategic Sprints - 12 points per organization
    try:
        with open(f'{data_dir}/2025-strategic-sprints.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['Organisation'].strip())
                sprint = row['Sprint'].strip()
                org_points[org]['Strategic Sprint'] += 12
                org_details[org]['Strategic Sprint'].append(sprint)
    except FileNotFoundError:
        print("Warning: 2025-strategic-sprints.csv not found")

    # 2. Release Managers - 12 points per person
    try:
        with open(f'{data_dir}/2025-release-managers.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['Organisation'].strip())
                name = row['Name'].strip()
                org_points[org]['Release Manager'] += 12
                org_details[org]['Release Manager'].append(name)
    except FileNotFoundError:
        print("Warning: 2025-release-managers.csv not found")

    # 3. Team Leaders - 6 points per team, split among leaders
    try:
        team_leaders = defaultdict(list)
        with open(f'{data_dir}/2025-team-leaders.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = row['Team'].strip()
                org = normalize_organization_name(row['Organisation'].strip())
                name = row['Name'].strip()
                team_leaders[team].append((org, name))

        for team, leaders in team_leaders.items():
            points_per_leader = 6 / len(leaders)
            for org, name in leaders:
                org_points[org]['Team Leader'] += points_per_leader
                org_details[org]['Team Leader'].append(f"{name} ({team})")
    except FileNotFoundError:
        print("Warning: 2025-team-leaders.csv not found")

    # 4. Board of Directors - 6 points per member
    try:
        with open(f'{data_dir}/2025-board-of-directors.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['Organisation'].strip())
                name = row['Name'].strip()
                org_points[org]['Board Member'] += 6
                org_details[org]['Board Member'].append(name)
    except FileNotFoundError:
        print("Warning: 2025-board-of-directors.csv not found")

    # 5. Podcasts - 6 points per series, split among hosts
    try:
        with open(f'{data_dir}/2025-podcasts.csv', 'r') as f:
            reader = csv.DictReader(f)
            hosts = []
            for row in reader:
                org = normalize_organization_name(row['Organisation'].strip())
                name = row['Name'].strip()
                hosts.append((org, name))

            if hosts:
                points_per_host = 6 / len(hosts)
                for org, name in hosts:
                    org_points[org]['Podcast Host'] += points_per_host
                    org_details[org]['Podcast Host'].append(name)
    except FileNotFoundError:
        print("Warning: 2025-podcasts.csv not found")

    # 6. World Plone Day Events - 3 points per event
    try:
        with open(f'{data_dir}/2025-world-plone-day-event.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = normalize_organization_name(row['Organisation'].strip())
                org_points[org]['WPD Event'] += 3
                org_details[org]['WPD Event'].append('Organized WPD Event')
    except FileNotFoundError:
        print("Warning: 2025-world-plone-day-event.csv not found")

    # 7. World Plone Day Talks - 1 point per talk, max 4 per organization
    try:
        talk_count = defaultdict(int)
        with open(f'{data_dir}/2025-world-plone-day-talks.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                orgs_raw = row['Organisation'].strip()
                video_type = row.get('Type', '').strip()
                video_title = row['Video Title'].strip()

                # Skip duplicates, teasers, announcements, welcomes, recaps
                if video_type in ['Duplicate', 'Teaser', 'Announcement', 'Welcome', 'Recap']:
                    continue

                if not orgs_raw:
                    continue

                orgs = [normalize_organization_name(o.strip()) for o in orgs_raw.split(';')]
                for org in orgs:
                    if talk_count[org] < 4:
                        talk_count[org] += 1
                        org_points[org]['WPD Talk'] += 1
                        org_details[org]['WPD Talk'].append(video_title)
    except FileNotFoundError:
        print("Warning: 2025-world-plone-day-talks.csv not found")

    # 8. Conference Organization - 24 points split among organizers
    try:
        with open(f'{data_dir}/2025-plone-conference.csv', 'r') as f:
            reader = csv.DictReader(f)
            organizers = [normalize_organization_name(row['Organisation'].strip()) for row in reader]

            if organizers:
                points_per_org = 24 / len(organizers)
                for org in organizers:
                    org_points[org]['Conference Organization'] += points_per_org
                    org_details[org]['Conference Organization'].append('Organized Plone Conference 2025')
    except FileNotFoundError:
        print("Warning: 2025-plone-conference.csv not found")

    # 9. Training Sessions - 6 points per session, split among co-trainers
    try:
        with open(f'{data_dir}/2025-plone-conference-trainings.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                orgs_raw = row['Organisation'].strip()
                title = row['Title'].strip()
                orgs = [normalize_organization_name(o.strip()) for o in orgs_raw.split(';')]
                points_per_org = 6 / len(orgs)
                for org in orgs:
                    org_points[org]['Training Session'] += points_per_org
                    org_details[org]['Training Session'].append(title)
    except FileNotFoundError:
        print("Warning: 2025-plone-conference-trainings.csv not found")

    # 10. Pull Request Contributions - Based on 5-year average
    # Criteria: Lead (100+/yr=20pts), Core (50-99/yr=10pts), Active (20-49/yr=4pts), Contributor (10-19/yr=2pts)
    for org, data in pr_data.items():
        avg_prs = data['avg_per_year']
        if avg_prs >= 100:
            points = 20
            level = 'Lead Contributor'
        elif avg_prs >= 50:
            points = 10
            level = 'Core Member'
        elif avg_prs >= 20:
            points = 4
            level = 'Active Member'
        elif avg_prs >= 10:
            points = 2
            level = 'Contributor'
        else:
            continue  # Less than 10 PRs/year, no points

        org_points[org]['PR Contributions'] += points
        org_details[org]['PR Contributions'].append(f"{level} ({avg_prs:.1f} PRs/year)")

    # 11. PLIP Contributions - Based on total PLIPs (all-time, ideally would be 5 years)
    # Criteria: Core Leaders (10+=15pts), Active Core (6+=9pts), Emerging (2+=3pts)
    for org, data in plip_data.items():
        total_plips = data['closed_plips']  # Using closed PLIPs as "merged and released"
        if total_plips >= 10:
            points = 15
            level = 'Core Leaders'
        elif total_plips >= 6:
            points = 9
            level = 'Active Core Contributor'
        elif total_plips >= 2:
            points = 3
            level = 'Emerging Core Contributor'
        else:
            continue  # Less than 2 PLIPs, no points

        org_points[org]['PLIP Contributions'] += points
        org_details[org]['PLIP Contributions'].append(f"{level} ({total_plips} PLIPs)")

    return org_points, org_details


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


def write_markdown_report(org_points, org_details, results, levels, output_file):
    """Write a detailed markdown report."""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        # Header
        f.write("# Plone Community Recognition Program 2025\n\n")
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

        for level in levels:
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
        f.write("| Strategic Sprint | 12 | Organize/host a strategic sprint |\n")
        f.write("| Release Manager | 12 | Serve as a release manager |\n")
        f.write("| Team Leader | 6 | Lead a community team (split among co-leaders) |\n")
        f.write("| Board Member | 6 | Serve on the Foundation Board |\n")
        f.write("| Conference Organization | 24 | Organize Plone Conference (split among organizers) |\n")
        f.write("| Training Session | 6 | Host training at Plone Conference (split among co-trainers) |\n\n")
        f.write("### Marketing Contributions\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Podcast Host | 6 | Host Plone podcast/live event (split among hosts) |\n")
        f.write("| WPD Event | 3 | Organize World Plone Day event |\n")
        f.write("| WPD Talk | 1 | Give World Plone Day talk (max 4 per org) |\n\n")
        f.write("### Code Contributions (Past 5 Years)\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Lead Contributor (PR) | 20 | 100+ PRs/year average |\n")
        f.write("| Core Member (PR) | 10 | 50-99 PRs/year average |\n")
        f.write("| Active Member (PR) | 4 | 20-49 PRs/year average |\n")
        f.write("| Contributor (PR) | 2 | 10-19 PRs/year average |\n")
        f.write("| Core Leaders (PLIP) | 15 | 10+ PLIPs merged and released |\n")
        f.write("| Active Core Contributor (PLIP) | 9 | 6+ PLIPs merged and released |\n")
        f.write("| Emerging Core Contributor (PLIP) | 3 | 2+ PLIPs merged and released |\n\n")

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
        pr_contributors.sort(key=lambda x: x[1], reverse=True)

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
        plip_contributors.sort(key=lambda x: x[1], reverse=True)

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


def main():
    """Main execution function."""

    print("Calculating community recognition points...")
    org_points, org_details = calculate_community_recognition_points()

    print(f"Found {len(org_points)} organizations")

    # Load recognition levels
    print("Loading recognition levels...")
    levels = load_recognition_levels()

    # Write CSV report
    csv_output = 'data/community-contributions/2025-community-recognition-report.csv'
    results = write_csv_report(org_points, levels, csv_output)
    print(f"CSV report written to: {csv_output}")

    # Write Markdown report
    md_output = 'report/community-recognition.md'
    write_markdown_report(org_points, org_details, results, levels, md_output)

    # Print summary
    print(f"\nTop 10 Organizations:")
    print(f"{'Rank':<6} {'Organisation':<40} {'Level':<25} {'Points':>10}")
    print("=" * 83)
    for i, row in enumerate(sorted(results, key=lambda x: x['Total Points'], reverse=True)[:10], 1):
        print(f"{i:<6} {row['Organisation']:<40} {row['Recognition Level']:<25} {row['Total Points']:>10.1f}")

    print("\nDone!")


if __name__ == '__main__':
    main()
