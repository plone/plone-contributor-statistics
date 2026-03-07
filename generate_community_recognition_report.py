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


def calculate_community_recognition_points():
    """Calculate community recognition points from all contribution data."""

    # Initialize points tracking
    org_points = defaultdict(lambda: defaultdict(float))
    org_details = defaultdict(lambda: defaultdict(list))

    data_dir = 'data/community-contributions'

    # 1. Strategic Sprints - 12 points per organization
    try:
        with open(f'{data_dir}/2025-strategic-sprints.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                org = row['Organisation'].strip()
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
                org = row['Organisation'].strip()
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
                org = row['Organisation'].strip()
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
                org = row['Organisation'].strip()
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
                org = row['Organisation'].strip()
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
                org = row['Organisation'].strip()
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

                orgs = [o.strip() for o in orgs_raw.split(';')]
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
            organizers = [row['Organisation'].strip() for row in reader]

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
                orgs = [o.strip() for o in orgs_raw.split(';')]
                points_per_org = 6 / len(orgs)
                for org in orgs:
                    org_points[org]['Training Session'] += points_per_org
                    org_details[org]['Training Session'].append(title)
    except FileNotFoundError:
        print("Warning: 2025-plone-conference-trainings.csv not found")

    return org_points, org_details


def write_csv_report(org_points, output_file):
    """Write the community recognition points to a CSV file."""

    # Calculate totals and create output
    results = []
    for org in sorted(org_points.keys()):
        categories = org_points[org]
        total = sum(categories.values())

        row = {
            'Organisation': org,
            'Strategic Sprint': categories.get('Strategic Sprint', 0),
            'Release Manager': categories.get('Release Manager', 0),
            'Team Leader': categories.get('Team Leader', 0),
            'Board Member': categories.get('Board Member', 0),
            'Podcast Host': categories.get('Podcast Host', 0),
            'WPD Event': categories.get('WPD Event', 0),
            'WPD Talk': categories.get('WPD Talk', 0),
            'Conference Organization': categories.get('Conference Organization', 0),
            'Training Session': categories.get('Training Session', 0),
            'Total Points': total
        }
        results.append(row)

    # Write to CSV
    fieldnames = ['Organisation', 'Strategic Sprint', 'Release Manager', 'Team Leader',
                  'Board Member', 'Podcast Host', 'WPD Event', 'WPD Talk',
                  'Conference Organization', 'Training Session', 'Total Points']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(results, key=lambda x: x['Total Points'], reverse=True):
            writer.writerow(row)

    return results


def write_markdown_report(org_points, org_details, results, output_file):
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

        # Point Categories
        f.write("## Recognition Categories\n\n")
        f.write("| Category | Points | Description |\n")
        f.write("|----------|--------|-------------|\n")
        f.write("| Strategic Sprint | 12 | Organize/host a strategic sprint |\n")
        f.write("| Release Manager | 12 | Serve as a release manager |\n")
        f.write("| Team Leader | 6 | Lead a community team (split among co-leaders) |\n")
        f.write("| Board Member | 6 | Serve on the Foundation Board |\n")
        f.write("| Podcast Host | 6 | Host Plone podcast/live event (split among hosts) |\n")
        f.write("| WPD Event | 3 | Organize World Plone Day event |\n")
        f.write("| WPD Talk | 1 | Give World Plone Day talk (max 4 per org) |\n")
        f.write("| Conference Organization | 24 | Organize Plone Conference (split among organizers) |\n")
        f.write("| Training Session | 6 | Host training at Plone Conference (split among co-trainers) |\n\n")

        # Leaderboard
        f.write("## Recognition Leaderboard\n\n")
        f.write("| Rank | Organization | Total Points |\n")
        f.write("|------|--------------|-------------:|\n")
        for i, row in enumerate(sorted(results, key=lambda x: x['Total Points'], reverse=True), 1):
            f.write(f"| {i} | {row['Organisation']} | {row['Total Points']:.1f} |\n")
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
                       'Training Session']:
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
                       'Training Session']:
                if row[cat] > 0:
                    category_stats[cat]['orgs'] += 1
                    category_stats[cat]['total_points'] += row[cat]

        f.write("| Category | Organizations | Total Points Awarded |\n")
        f.write("|----------|---------------:|---------------------:|\n")
        for cat in ['Strategic Sprint', 'Release Manager', 'Team Leader', 'Board Member',
                   'Podcast Host', 'WPD Event', 'WPD Talk', 'Conference Organization',
                   'Training Session']:
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

    # Write CSV report
    csv_output = 'data/community-contributions/2025-community-recognition-points.csv'
    results = write_csv_report(org_points, csv_output)
    print(f"CSV report written to: {csv_output}")

    # Write Markdown report
    md_output = 'report/community-recognition.md'
    write_markdown_report(org_points, org_details, results, md_output)

    # Print summary
    print(f"\nTop 10 Organizations:")
    print(f"{'Rank':<6} {'Organisation':<40} {'Points':>10}")
    print("=" * 58)
    for i, row in enumerate(sorted(results, key=lambda x: x['Total Points'], reverse=True)[:10], 1):
        print(f"{i:<6} {row['Organisation']:<40} {row['Total Points']:>10.1f}")

    print("\nDone!")


if __name__ == '__main__':
    main()
