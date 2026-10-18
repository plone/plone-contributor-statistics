#!/usr/bin/env python3
"""
Filter and sort CMFPlone releases to show only final releases.

This script filters out release candidates, dev versions, alpha, and beta releases,
keeping only final stable releases sorted by date.
"""

import csv
from datetime import datetime


def is_final_release(release_name: str) -> bool:
    """
    Check if a release is a final stable release.

    Args:
        release_name: The release tag name

    Returns:
        True if it's a final release, False otherwise
    """
    release_lower = release_name.lower()

    # Exclude specific tags
    if release_name in ['v4.2', 'goldegg-sid-nav']:
        return False

    # Exclude releases containing these markers
    exclude_markers = ['rc', 'dev', 'alpha', 'beta', 'a', 'b']

    # Check if release contains any exclude markers
    # But be careful: we want to exclude '6.1.0a1' but not '6.0.1'
    # So we need to check for these patterns more carefully

    # Simple check: if it contains 'rc', 'dev', 'alpha', 'beta'
    if any(marker in release_lower for marker in ['rc', 'dev', 'alpha', 'beta']):
        return False

    # Check for alpha/beta pattern like '6.1.0a1' or '6.1.0b1'
    # These have a letter directly after the version number
    import re
    if re.search(r'\d+\.\d+\.\d+[ab]\d+', release_name):
        return False

    return True


def filter_and_sort_releases(input_file: str, output_file: str):
    """
    Filter and sort releases from CSV file.

    Args:
        input_file: Input CSV filename
        output_file: Output CSV filename
    """
    releases = []

    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            release_name = row['release']
            release_date = row['date']

            # Skip if no date
            if not release_date:
                continue

            # Check if it's a final release
            if is_final_release(release_name):
                releases.append({
                    'release': release_name,
                    'date': release_date
                })

    # Sort by date (oldest first)
    releases.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))

    # Write output file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['release', 'date'])
        writer.writeheader()
        writer.writerows(releases)

    print(f"Filtered {len(releases)} final releases")
    return releases


def main():
    """Main function."""
    print("Filtering CMFPlone Releases")
    print("=" * 40)

    input_file = 'cmfplone-releases.csv'
    output_file = 'cmfplone-releases-filtered.csv'

    releases = filter_and_sort_releases(input_file, output_file)

    print(f"\nFiltered releases saved to: {output_file}")
    print(f"Total final releases: {len(releases)}")

    # Show first 10 and last 10
    print("\nFirst 10 releases (oldest):")
    print("-" * 40)
    print(f"{'Release':<20} {'Date':<15}")
    print("-" * 40)
    for r in releases[:10]:
        print(f"{r['release']:<20} {r['date']:<15}")

    print("\nLast 10 releases (newest):")
    print("-" * 40)
    print(f"{'Release':<20} {'Date':<15}")
    print("-" * 40)
    for r in releases[-10:]:
        print(f"{r['release']:<20} {r['date']:<15}")

    return 0


if __name__ == "__main__":
    exit(main())
