#!/usr/bin/env python3
"""
Generate 3-Tier PLIP Contributor Levels

This script analyzes PLIP data and generates the approved 3-tier level system:
- 🏆 Platinum: 10+ PLIPs (Core Leaders)
- ⭐ Gold: 3-9 PLIPs (Active Contributors)
- 🌟 Silver: 1-2 PLIPs (Emerging Contributors)
"""

import pandas as pd
import argparse
from datetime import datetime


def load_plip_data(csv_file='plone-plips.csv'):
    """Load PLIP statistics from CSV file"""
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} contributors from {csv_file}")
        return df
    except FileNotFoundError:
        print(f"❌ Error: {csv_file} not found. Please run plone_plips.py first.")
        return None


def categorize_contributors(df):
    """Categorize contributors into 3 tiers"""
    tiers = {
        'platinum': df[df['total_plips'] >= 10],
        'gold': df[(df['total_plips'] >= 3) & (df['total_plips'] < 10)],
        'silver': df[(df['total_plips'] >= 1) & (df['total_plips'] <= 2)]
    }
    return tiers


def display_tier(tier_name, df, emoji):
    """Display contributors in a tier"""
    print(f"\n{emoji} {tier_name.upper()} TIER")
    print("=" * 80)

    df_sorted = df.sort_values('total_plips', ascending=False)

    print(f"Total: {len(df_sorted)} contributors | {df_sorted['total_plips'].sum()} PLIPs")
    print()

    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        years = row['first_plip'][:4] + '-' + row['last_plip'][:4]
        repos = len(row['repositories'].split(','))
        print(f"{i:2d}. {row['username']:<25} {row['total_plips']:3d} PLIPs "
              f"({row['open_plips']:2d} open, {row['closed_plips']:2d} closed) | "
              f"{repos} repos | {years}")


def generate_summary_stats(tiers, total_plips):
    """Generate summary statistics"""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    for tier_name, emoji in [('platinum', '🏆'), ('gold', '⭐'), ('silver', '🌟')]:
        tier_df = tiers[tier_name]
        tier_plips = tier_df['total_plips'].sum()
        pct_contributors = len(tier_df) / sum(len(t) for t in tiers.values()) * 100
        pct_plips = tier_plips / total_plips * 100

        print(f"\n{emoji} {tier_name.upper()}:")
        print(f"  Contributors: {len(tier_df)} ({pct_contributors:.1f}%)")
        print(f"  Total PLIPs: {tier_plips} ({pct_plips:.1f}%)")
        print(f"  Avg PLIPs/person: {tier_plips/len(tier_df):.1f}")
        print(f"  Completion rate: {tier_df['closed_plips'].sum()/tier_plips*100:.1f}%")


def export_tiers_csv(tiers, output_file='plip-3tier-levels.csv'):
    """Export tier assignments to CSV"""

    records = []
    for tier_name, tier_df in [('Platinum', tiers['platinum']),
                                ('Gold', tiers['gold']),
                                ('Silver', tiers['silver'])]:
        for _, row in tier_df.iterrows():
            records.append({
                'username': row['username'],
                'tier': tier_name,
                'total_plips': row['total_plips'],
                'open_plips': row['open_plips'],
                'closed_plips': row['closed_plips'],
                'repositories_count': row['repositories_count'],
                'first_plip': row['first_plip'],
                'last_plip': row['last_plip']
            })

    result_df = pd.DataFrame(records)
    result_df.to_csv(output_file, index=False)
    print(f"\n✅ Tier assignments exported to: {output_file}")


def generate_progression_report(tiers):
    """Show progression paths"""
    print("\n" + "=" * 80)
    print("PROGRESSION PATHS")
    print("=" * 80)

    print("\n🌟 Silver → ⭐ Gold:")
    print("  Requirement: Submit 1-2 more PLIPs (reach 3 total)")
    silver_2 = tiers['silver'][tiers['silver']['total_plips'] == 2]
    silver_1 = tiers['silver'][tiers['silver']['total_plips'] == 1]
    print(f"  - {len(silver_2)} contributors need 1 more PLIP")
    print(f"  - {len(silver_1)} contributors need 2 more PLIPs")

    print("\n⭐ Gold → 🏆 Platinum:")
    print("  Requirement: Submit more PLIPs (reach 10 total)")
    for _, row in tiers['gold'].sort_values('total_plips', ascending=False).iterrows():
        needed = 10 - row['total_plips']
        print(f"  - {row['username']:<20} has {row['total_plips']}, needs {needed} more")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Generate 3-Tier PLIP Contributor Levels',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--input', '-i', type=str, default='plone-plips.csv',
                        help='Input CSV file (default: plone-plips.csv)')
    parser.add_argument('--export', '-e', type=str,
                        help='Export tier assignments to CSV file')

    args = parser.parse_args()

    print("=" * 80)
    print("3-TIER PLIP CONTRIBUTOR LEVEL SYSTEM")
    print("=" * 80)
    print()

    # Load data
    df = load_plip_data(args.input)
    if df is None:
        return 1

    total_plips = df['total_plips'].sum()

    # Categorize
    tiers = categorize_contributors(df)

    # Display each tier
    display_tier('PLATINUM (10+ PLIPs)', tiers['platinum'], '🏆')
    display_tier('GOLD (3-9 PLIPs)', tiers['gold'], '⭐')
    display_tier('SILVER (1-2 PLIPs)', tiers['silver'], '🌟')

    # Summary stats
    generate_summary_stats(tiers, total_plips)

    # Progression paths
    generate_progression_report(tiers)

    # Export if requested
    if args.export:
        export_tiers_csv(tiers, args.export)

    print("\n" + "=" * 80)
    print("✅ 3-Tier PLIP Level Analysis Complete")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
