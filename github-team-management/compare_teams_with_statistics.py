#!/usr/bin/env python3
"""
Compare GitHub Team Membership with Contributor Statistics

Reads the active-github-users CSV produced by extract_active_github_users.py
and the team member CSVs produced by fetch_github_teams.py, then produces a
report showing:

  - Developers who are still active  → stay in developers team
  - Developers who are no longer active → move to alumni-developers
  - Active contributors not yet in the developers team (for reference)

All output is read-only — no changes are made to GitHub. Use the
generated report to decide who to move.

Usage:
  python compare_teams_with_statistics.py
  python compare_teams_with_statistics.py \\
      --active-users ../active-github-users-2023-2025.csv \\
      --developers-csv team-developers.csv \\
      --alumni-csv team-alumni-developers.csv
"""

import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime


def load_csv_logins(path: Path) -> set[str]:
    """Return a set of lowercase logins from a team CSV (login column)."""
    logins = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            login = row.get("login", "").strip()
            if login:
                logins.add(login.lower())
    return logins


def load_active_users(path: Path) -> dict[str, dict]:
    """Return a dict keyed by lowercase username from the active-users CSV."""
    users = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get("username", "").strip()
            if username:
                users[username.lower()] = {
                    "username": username,
                    "years_active": row.get("years_active", ""),
                    "total_commits": int(row.get("total_commits", 0) or 0),
                    "total_prs": int(row.get("total_prs", 0) or 0),
                }
    return users


def find_active_users_csv(script_dir: Path) -> Path | None:
    """Find the most recent active-github-users CSV in the parent directory."""
    parent = script_dir.parent
    candidates = sorted(parent.glob("active-github-users-*.csv"), reverse=True)
    return candidates[0] if candidates else None


def write_report(
    lines: list[str],
    out_path: Path,
) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).parent
    default_active = find_active_users_csv(script_dir)

    parser = argparse.ArgumentParser(
        description="Compare GitHub team membership with contributor activity statistics."
    )
    parser.add_argument(
        "--active-users",
        default=str(default_active) if default_active else "",
        help="Path to active-github-users CSV (default: auto-detect in parent dir)",
    )
    parser.add_argument(
        "--developers-csv",
        default=str(script_dir / "team-developers.csv"),
        help="Path to team-developers.csv (default: ./team-developers.csv)",
    )
    parser.add_argument(
        "--alumni-csv",
        default=str(script_dir / "team-alumni-developers.csv"),
        help="Path to team-alumni-developers.csv (default: ./team-alumni-developers.csv)",
    )
    parser.add_argument(
        "--output",
        default=str(script_dir / "TEAM-COMPARISON-REPORT.txt"),
        help="Path for the output report (default: ./TEAM-COMPARISON-REPORT.txt)",
    )
    parser.add_argument(
        "--min-commits",
        type=int,
        default=0,
        help="Minimum total commits required to count as active (default: 0)",
    )
    parser.add_argument(
        "--min-prs",
        type=int,
        default=0,
        help="Minimum total PRs required to count as active (default: 0)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # --- Validate inputs ---
    if not args.active_users:
        print("Error: could not find active-github-users CSV. Use --active-users.")
        return 1

    active_path = Path(args.active_users)
    dev_path = Path(args.developers_csv)
    alumni_path = Path(args.alumni_csv)

    for p in (active_path, dev_path):
        if not p.exists():
            print(f"Error: file not found: {p}")
            return 1

    # alumni CSV may be empty if team was just created
    alumni_logins: set[str] = set()
    if alumni_path.exists():
        alumni_logins = load_csv_logins(alumni_path)

    active_users = load_active_users(active_path)
    dev_logins = load_csv_logins(dev_path)

    # Apply optional activity thresholds
    def is_active(info: dict) -> bool:
        return (
            info["total_commits"] >= args.min_commits
            and info["total_prs"] >= args.min_prs
        )

    # Classify each developer team member
    stay: list[dict] = []        # active → remain developers
    move_to_alumni: list[dict] = []  # inactive → alumni

    for login in sorted(dev_logins):
        info = active_users.get(login)
        if info and is_active(info):
            stay.append(info)
        else:
            # Not in active stats at all, or below threshold
            move_to_alumni.append(
                info
                if info
                else {
                    "username": login,
                    "years_active": "—",
                    "total_commits": 0,
                    "total_prs": 0,
                }
            )

    # Active contributors who aren't in the developers team (informational)
    not_in_team: list[dict] = [
        info
        for login, info in sorted(active_users.items())
        if login not in dev_logins and login not in alumni_logins and is_active(info)
    ]

    # --- Build report ---
    now = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []

    lines += [
        f"# GitHub Team Comparison Report",
        f"# Generated: {now}",
        f"# Active users source: {active_path.name}",
        f"# Developers team CSV: {dev_path.name}",
        f"# Alumni team CSV: {alumni_path.name if alumni_path.exists() else '(not found)'}",
        "",
    ]

    # Summary
    lines += [
        "## Summary",
        "",
        f"  Developers team members:      {len(dev_logins)}",
        f"  Active in contributor stats:  {len(active_users)}",
        f"  Alumni team members:          {len(alumni_logins)}",
        "",
        f"  Stay in developers team:      {len(stay)}",
        f"  Move to alumni-developers:    {len(move_to_alumni)}",
        f"  Active but not in team:       {len(not_in_team)}",
        "",
    ]

    # --- Section 1: Move to alumni ---
    lines += [
        "## Move to alumni-developers",
        "",
        "These developers team members have no recorded activity in the",
        f"tracked period ({active_path.stem.replace('active-github-users-', '')}).",
        "",
        f"  {'Username':<30} {'Years active':<20} {'Commits':>8} {'PRs':>6}",
        f"  {'-'*30} {'-'*20} {'-'*8} {'-'*6}",
    ]
    for u in sorted(move_to_alumni, key=lambda x: x["username"].lower()):
        lines.append(
            f"  {u['username']:<30} {u['years_active']:<20} {u['total_commits']:>8} {u['total_prs']:>6}"
        )
    lines.append("")

    # --- Section 2: Stay in developers ---
    lines += [
        "## Stay in developers team",
        "",
        f"  {'Username':<30} {'Years active':<20} {'Commits':>8} {'PRs':>6}",
        f"  {'-'*30} {'-'*20} {'-'*8} {'-'*6}",
    ]
    for u in sorted(stay, key=lambda x: x["username"].lower()):
        lines.append(
            f"  {u['username']:<30} {u['years_active']:<20} {u['total_commits']:>8} {u['total_prs']:>6}"
        )
    lines.append("")

    # --- Section 3: Active but not in team ---
    lines += [
        "## Active contributors not in developers team (informational)",
        "",
        "These users appear in the contributor statistics but are not",
        "members of the developers team. Listed for reference only.",
        "",
        f"  {'Username':<30} {'Years active':<20} {'Commits':>8} {'PRs':>6}",
        f"  {'-'*30} {'-'*20} {'-'*8} {'-'*6}",
    ]
    for u in sorted(not_in_team, key=lambda x: x["username"].lower()):
        lines.append(
            f"  {u['username']:<30} {u['years_active']:<20} {u['total_commits']:>8} {u['total_prs']:>6}"
        )
    lines.append("")

    # --- Print and save ---
    report_text = "\n".join(lines)
    print(report_text)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(lines, out_path)
    print(f"\nReport saved to: {out_path}")

    # Machine-readable alumni candidates list
    alumni_list_path = out_path.parent / "move-to-alumni.txt"
    with open(alumni_list_path, "w", encoding="utf-8") as f:
        for u in sorted(move_to_alumni, key=lambda x: x["username"].lower()):
            f.write(u["username"] + "\n")
    print(f"Alumni candidate list saved to: {alumni_list_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
