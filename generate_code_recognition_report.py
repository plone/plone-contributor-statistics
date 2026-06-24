#!/usr/bin/env python3
"""
Generate Code Recognition Report

Calculates code contribution recognition tiers (Bronze → Titanium) for
organisations and individual contributors based on:
  - PR contributions: average merged PRs per year over a 5-year window
  - PLIP contributions: all-time closed PLIPs

Outputs:
  - data/code-contributions/{year}-code-recognition-organisations.csv
  - data/code-contributions/{year}-code-recognition-individuals.csv
  - reports/code-recognition.md

Usage:
  python generate_code_recognition_report.py
  python generate_code_recognition_report.py --years 2021 2022 2023 2024 2025
"""

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ── Points tables ─────────────────────────────────────────────────────────────

PR_POINTS = [
    ('Lead Author',    100, float('inf'), 20),
    ('Core Author',     50,           99, 10),
    ('Active Author',   20,           49,  4),
    ('Author',          10,           19,  2),
]

PLIP_POINTS = [
    ('Lead Architect', 10, float('inf'), 15),
    ('Core Architect',  6,            9,  9),
    ('Architect',       2,            5,  3),
]

TIERS = [
    ('Bronze',    1,  5),
    ('Silver',    6, 11),
    ('Gold',     12, 23),
    ('Platinum', 24, 49),
    ('Diamond',  50, 74),
    ('Titanium', 75, float('inf')),
]


# ── Tier helpers ──────────────────────────────────────────────────────────────

def get_tier(points):
    for name, min_p, max_p in TIERS:
        if min_p <= points <= max_p:
            return name
    return 'No Level'


def get_pr_level_and_points(avg_prs_per_year):
    for name, min_v, max_v, pts in PR_POINTS:
        if min_v <= avg_prs_per_year <= max_v:
            return name, pts
    return '', 0


def get_plip_level_and_points(closed_plips):
    for name, min_v, max_v, pts in PLIP_POINTS:
        if min_v <= closed_plips <= max_v:
            return name, pts
    return '', 0


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_individual_pr_data(years):
    """Aggregate total merged PRs per contributor across the given years."""
    totals = defaultdict(int)
    for year in years:
        filepath = Path(f'data/{year}-plone-contributors.csv')
        if not filepath.exists():
            print(f"  Warning: {filepath} not found, skipping")
            continue
        with open(filepath, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                username = row['username'].strip()
                prs = int(row['total_pull_requests'] or 0)
                if prs > 0:
                    totals[username] += prs
    return totals


def load_org_pr_data(years):
    """Aggregate total merged PRs per organisation across the given years."""
    totals = defaultdict(int)
    for year in years:
        filepath = Path(f'data/{year}-plone-organisation-contributors.csv')
        if not filepath.exists():
            print(f"  Warning: {filepath} not found, skipping")
            continue
        with open(filepath, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                org = row['organisation'].strip()
                prs = int(row['total_pull_requests'] or 0)
                if prs > 0:
                    totals[org] += prs
    return totals


def load_individual_plip_data():
    """Load all-time closed PLIP counts per individual contributor."""
    data = {}
    filepath = Path('plone-plips.csv')
    if not filepath.exists():
        print("  Warning: plone-plips.csv not found")
        return data
    with open(filepath, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            username = row['username'].strip()
            data[username] = int(row['closed_plips'] or 0)
    return data


def load_org_plip_data():
    """Load all-time closed PLIP counts per organisation."""
    data = {}
    filepath = Path('plone-plip-organisations.csv')
    if not filepath.exists():
        print("  Warning: plone-plip-organisations.csv not found")
        return data
    with open(filepath, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            org = row['organisation'].strip()
            data[org] = int(row['closed_plips'] or 0)
    return data


def detect_available_years():
    """Detect years that have a contributor CSV file in data/."""
    years = []
    for p in Path('data').glob('[0-9][0-9][0-9][0-9]-plone-contributors.csv'):
        try:
            years.append(int(p.name[:4]))
        except ValueError:
            pass
    return sorted(years)


# ── Score calculation ─────────────────────────────────────────────────────────

def calculate_scores(pr_totals, plip_data, num_years):
    """Compute points and tiers for all entities that have at least 1 point."""
    results = []
    all_entities = set(pr_totals) | set(plip_data)

    for entity in sorted(all_entities):
        total_prs = pr_totals.get(entity, 0)
        avg_prs = total_prs / num_years

        pr_level, pr_pts = get_pr_level_and_points(avg_prs)

        closed_plips = plip_data.get(entity, 0)
        plip_level, plip_pts = get_plip_level_and_points(closed_plips)

        total_points = pr_pts + plip_pts
        if total_points == 0:
            continue

        results.append({
            'entity': entity,
            'avg_prs_per_year': round(avg_prs, 1),
            'pr_level': pr_level,
            'pr_points': pr_pts,
            'closed_plips': closed_plips,
            'plip_level': plip_level,
            'plip_points': plip_pts,
            'total_points': total_points,
            'tier': get_tier(total_points),
        })

    results.sort(key=lambda x: x['total_points'], reverse=True)
    return results


# ── Output writers ────────────────────────────────────────────────────────────

def write_csv(results, output_file, entity_col):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fieldnames = [entity_col, 'Tier', 'Total Points', 'PR Level', 'PR Points',
                  'Avg PRs/Year', 'PLIP Level', 'PLIP Points', 'Closed PLIPs']
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                entity_col: r['entity'],
                'Tier': r['tier'],
                'Total Points': r['total_points'],
                'PR Level': r['pr_level'],
                'PR Points': r['pr_points'],
                'Avg PRs/Year': r['avg_prs_per_year'],
                'PLIP Level': r['plip_level'],
                'PLIP Points': r['plip_points'],
                'Closed PLIPs': r['closed_plips'],
            })


def _tier_table(results):
    """Return markdown lines for a tier distribution table."""
    counts = defaultdict(int)
    for r in results:
        counts[r['tier']] += 1
    lines = ['| Tier | Count |', '|------|------:|']
    for name, _, _ in reversed(TIERS):
        if counts[name]:
            lines.append(f'| {name} | {counts[name]} |')
    return lines


def _leaderboard_table(results, entity_col, n=20):
    """Return markdown lines for a leaderboard table."""
    lines = [
        f'| Rank | {entity_col} | Tier | Points | PR Level | Avg PRs/yr | PLIP Level | Closed PLIPs |',
        f'|------|{"---" * (len(entity_col) // 3 + 1)}|------|-------:|----------|------------|------------|-------------|',
    ]
    for i, r in enumerate(results[:n], 1):
        lines.append(
            f'| {i} | {r["entity"]} | {r["tier"]} | {r["total_points"]} '
            f'| {r["pr_level"]} | {r["avg_prs_per_year"]} '
            f'| {r["plip_level"]} | {r["closed_plips"]} |'
        )
    return lines


def write_markdown(org_results, ind_results, years, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    year_range = f'{min(years)}-{max(years)}'
    num_years = len(years)

    lines = []
    lines.append('# Plone Code Recognition Report')
    lines.append('')
    lines.append(f'*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  ')
    lines.append(f'*Period: {year_range} ({num_years} years)*')
    lines.append('')
    lines.append('> **Note on PLIPs**: PLIP counts are all-time (not limited to the period above).')
    lines.append('> PR averages are computed over the stated period.')
    lines.append('')

    # Points tables
    lines.append('## Points Table')
    lines.append('')
    lines.append('### PR Contributions (average merged PRs per year over the period)')
    lines.append('')
    lines.append('| Level | Threshold | Points |')
    lines.append('|-------|-----------|-------:|')
    for name, min_v, max_v, pts in PR_POINTS:
        thresh = f'{min_v}+' if max_v == float('inf') else f'{min_v}–{int(max_v)}'
        lines.append(f'| {name} | {thresh} PRs/year | {pts} |')
    lines.append('')
    lines.append('### PLIP Contributions (all-time closed PLIPs)')
    lines.append('')
    lines.append('| Level | Threshold | Points |')
    lines.append('|-------|-----------|-------:|')
    for name, min_v, max_v, pts in PLIP_POINTS:
        thresh = f'{min_v}+' if max_v == float('inf') else f'{min_v}–{int(max_v)}'
        lines.append(f'| {name} | {thresh} PLIPs | {pts} |')
    lines.append('')

    # Tiers
    lines.append('## Recognition Tiers')
    lines.append('')
    lines.append('| Tier | Points |')
    lines.append('|------|--------|')
    for name, min_p, max_p in TIERS:
        range_str = f'{min_p}+' if max_p == float('inf') else f'{min_p}–{max_p}'
        lines.append(f'| {name} | {range_str} |')
    lines.append('')

    # Organisation leaderboard
    lines.append('## Organisation Leaderboard')
    lines.append('')
    lines.extend(_leaderboard_table(org_results, 'Organisation'))
    lines.append('')

    # Individual leaderboard
    lines.append('## Individual Contributor Leaderboard')
    lines.append('')
    lines.extend(_leaderboard_table(ind_results, 'Contributor'))
    lines.append('')

    # Tier distribution
    lines.append('## Tier Distribution')
    lines.append('')
    lines.append('### Organisations')
    lines.append('')
    lines.extend(_tier_table(org_results))
    lines.append('')
    lines.append('### Individual Contributors')
    lines.append('')
    lines.extend(_tier_table(ind_results))
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('*Generated by Plone Contributor Statistics Tool*  ')
    lines.append('*For community activity recognition see `reports/community-recognition.md`*')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate code recognition report for organisations and individual contributors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_code_recognition_report.py
  python generate_code_recognition_report.py --years 2021 2022 2023 2024 2025
        """
    )
    parser.add_argument(
        '--years', nargs='+', type=int, default=None,
        help='Years to include (default: 5 most recent years with data)'
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.years:
        years = sorted(args.years)
    else:
        all_years = detect_available_years()
        years = all_years[-5:] if len(all_years) >= 5 else all_years

    if not years:
        print("No contributor data files found in data/. Run make run-stats first.")
        return 1

    num_years = len(years)
    year_range = f'{min(years)}-{max(years)}'
    report_year = max(years)

    print("Code Recognition Report Generator")
    print("=" * 40)
    print(f"Period: {year_range} ({num_years} years)")
    print()

    # Load data
    print("Loading individual PR data...")
    ind_pr_totals = load_individual_pr_data(years)
    print(f"  {len(ind_pr_totals)} contributors with merged PRs")

    print("Loading individual PLIP data...")
    ind_plip_data = load_individual_plip_data()
    print(f"  {len(ind_plip_data)} contributors with PLIPs")

    print("Loading organisation PR data...")
    org_pr_totals = load_org_pr_data(years)
    print(f"  {len(org_pr_totals)} organisations with merged PRs")

    print("Loading organisation PLIP data...")
    org_plip_data = load_org_plip_data()
    print(f"  {len(org_plip_data)} organisations with PLIPs")

    # Calculate scores
    print()
    print("Calculating scores...")
    ind_results = calculate_scores(ind_pr_totals, ind_plip_data, num_years)
    org_results = calculate_scores(org_pr_totals, org_plip_data, num_years)
    print(f"  {len(ind_results)} individuals with ≥1 point")
    print(f"  {len(org_results)} organisations with ≥1 point")

    # Write outputs
    ind_csv = f'data/code-contributions/{report_year}-code-recognition-individuals.csv'
    org_csv = f'data/code-contributions/{report_year}-code-recognition-organisations.csv'
    md_file = 'reports/code-recognition.md'

    write_csv(ind_results, ind_csv, 'Contributor')
    write_csv(org_results, org_csv, 'Organisation')
    write_markdown(org_results, ind_results, years, md_file)

    print()
    print(f"✅ Individual report:     {ind_csv}")
    print(f"✅ Organisation report:   {org_csv}")
    print(f"✅ Markdown report:       {md_file}")

    # Console summary
    print()
    print("Top 10 Organisations:")
    print(f"{'Rank':<5} {'Organisation':<35} {'Tier':<12} {'Points':>8}")
    print("-" * 65)
    for i, r in enumerate(org_results[:10], 1):
        print(f"{i:<5} {r['entity']:<35} {r['tier']:<12} {r['total_points']:>8}")

    print()
    print("Top 10 Individual Contributors:")
    print(f"{'Rank':<5} {'Contributor':<25} {'Tier':<12} {'Points':>8}")
    print("-" * 55)
    for i, r in enumerate(ind_results[:10], 1):
        print(f"{i:<5} {r['entity']:<25} {r['tier']:<12} {r['total_points']:>8}")

    return 0


if __name__ == '__main__':
    exit(main())
