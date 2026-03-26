#!/usr/bin/env python3
"""
Extract Active GitHub Users for Plone Repositories

Identifies all GitHub users who have been active in Plone repositories
within the specified years (default: last 3 years). Useful for managing
team membership, e.g. moving inactive developers to an alumni team.

Data sources:
- data/YYYY-plone-contributors.csv  (commits and merged PRs)
- data/YYYY-volto-stats.csv         (Volto-specific activity)

Bot accounts are excluded automatically.
"""

import csv
import argparse
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# Known bot accounts and patterns to exclude
BOT_SUFFIXES = ("-bot", "[bot]")
BOT_USERNAMES = {
    "mister-roboto",
    "docker-library-bot",
}


def is_bot(username: str) -> bool:
    """Return True if the username looks like a bot account."""
    lower = username.lower()
    if lower in BOT_USERNAMES:
        return True
    for suffix in BOT_SUFFIXES:
        if lower.endswith(suffix):
            return True
    return False


def load_contributors_csv(year: int) -> list[dict]:
    """Load data/YYYY-plone-contributors.csv and return rows as dicts."""
    filepath = Path("data") / f"{year}-plone-contributors.csv"
    if not filepath.exists():
        print(f"  Warning: {filepath} not found, skipping.")
        return []
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_volto_stats_csv(year: int) -> list[dict]:
    """Load data/YYYY-volto-stats.csv and return rows as dicts."""
    filepath = Path("data") / f"{year}-volto-stats.csv"
    if not filepath.exists():
        return []
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def collect_active_users(years: list[int]) -> dict:
    """
    Collect active users across all specified years.

    Returns a dict keyed by lowercase username with:
        username, years_active, total_commits, total_prs
    """
    # user_data[username] = {commits: int, prs: int, years: set}
    user_data = defaultdict(lambda: {"commits": 0, "prs": 0, "years": set()})

    for year in years:
        print(f"  Loading {year} contributor data...")

        # Main contributors file
        rows = load_contributors_csv(year)
        for row in rows:
            username = row.get("username", "").strip()
            if not username or is_bot(username):
                continue
            key = username.lower()
            user_data[key]["username"] = username  # preserve original casing
            user_data[key]["commits"] += int(row.get("total_commits", 0) or 0)
            user_data[key]["prs"] += int(row.get("total_pull_requests", 0) or 0)
            user_data[key]["years"].add(year)

        # Volto stats (may include contributors not in main file)
        volto_rows = load_volto_stats_csv(year)
        for row in volto_rows:
            username = row.get("github_username", "").strip()
            if not username or is_bot(username):
                continue
            key = username.lower()
            if "username" not in user_data[key]:
                user_data[key]["username"] = username
            user_data[key]["commits"] += int(row.get("commits", 0) or 0)
            user_data[key]["prs"] += int(row.get("pull_requests", 0) or 0)
            user_data[key]["years"].add(year)

    return user_data


def save_outputs(user_data: dict, years: list[int]) -> tuple[str, str]:
    """Save CSV and plain-text outputs. Returns (csv_path, txt_path)."""
    year_range = f"{min(years)}-{max(years)}"
    csv_path = f"active-github-users-{year_range}.csv"
    txt_path = "ACTIVE-GITHUB-USERS.txt"

    # Sort alphabetically by username (case-insensitive)
    sorted_users = sorted(user_data.values(), key=lambda u: u["username"].lower())

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "years_active", "total_commits", "total_prs"])
        for u in sorted_users:
            years_active = ", ".join(str(y) for y in sorted(u["years"]))
            writer.writerow([u["username"], years_active, u["commits"], u["prs"]])

    # Write plain-text list (one username per line)
    txt_lines = [
        f"# Active Plone GitHub Users ({year_range})",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d')}",
        f"# Sources: data/YYYY-plone-contributors.csv, data/YYYY-volto-stats.csv",
        f"# Total active users: {len(sorted_users)}",
        "",
    ]
    for u in sorted_users:
        txt_lines.append(u["username"])

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    return csv_path, txt_path


def parse_args() -> argparse.Namespace:
    current_year = datetime.now().year
    # Default to the 3 most recently completed calendar years
    default_years = list(range(current_year - 3, current_year))

    parser = argparse.ArgumentParser(
        description="Extract active GitHub users from Plone contributor data."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=default_years,
        help=f"Years to include (default: {default_years})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    years = sorted(args.years)
    year_range = f"{min(years)}-{max(years)}"

    print(f"Extracting active GitHub users for {year_range}")
    print("=" * 50)

    user_data = collect_active_users(years)

    if not user_data:
        print("No active users found. Check that data files exist for the given years.")
        return 1

    csv_path, txt_path = save_outputs(user_data, years)

    print(f"\nFound {len(user_data)} active users across {year_range}.")
    print(f"  CSV: {csv_path}")
    print(f"  List: {txt_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
