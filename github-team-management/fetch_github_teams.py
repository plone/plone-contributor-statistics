#!/usr/bin/env python3
"""
Fetch GitHub Team Members and Ensure Alumni Team Exists

Downloads the current member lists for the Plone 'developers' and
'alumni-developers' GitHub teams. Creates the 'alumni-developers' team
if it does not yet exist.

Outputs:
  team-developers.csv        - current developers team members
  team-alumni-developers.csv - current alumni-developers team members

Usage:
  python fetch_github_teams.py
  python fetch_github_teams.py --token ghp_...
  python fetch_github_teams.py --org myorg --developers-team core-devs
"""

import os
import csv
import sys
import argparse
import requests
from pathlib import Path


GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "plone"
DEFAULT_DEVELOPERS_TEAM = "developers"
DEFAULT_ALUMNI_TEAM = "alumni-developers"


def headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def paginate(token: str, url: str, params: dict | None = None) -> list[dict] | None:
    """GET all pages from a GitHub API endpoint. Returns None on 404."""
    results = []
    page = 1
    while True:
        p = {"per_page": 100, "page": page, **(params or {})}
        resp = requests.get(url, headers=headers(token), params=p)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def get_team(token: str, org: str, team_slug: str) -> dict | None:
    """Return team metadata or None if it doesn't exist."""
    resp = requests.get(
        f"{GITHUB_API}/orgs/{org}/teams/{team_slug}",
        headers=headers(token),
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_team_members(token: str, org: str, team_slug: str) -> list[dict] | None:
    """Return list of member dicts or None if the team doesn't exist."""
    url = f"{GITHUB_API}/orgs/{org}/teams/{team_slug}/members"
    return paginate(token, url)


def create_team(
    token: str,
    org: str,
    name: str,
    description: str,
    privacy: str = "closed",
) -> dict:
    """Create a new team and return its metadata."""
    resp = requests.post(
        f"{GITHUB_API}/orgs/{org}/teams",
        headers=headers(token),
        json={"name": name, "description": description, "privacy": privacy},
    )
    resp.raise_for_status()
    return resp.json()


def save_members_csv(members: list[dict], path: Path) -> None:
    """Write a sorted CSV with login,id,profile_url columns."""
    rows = sorted(
        [
            {
                "login": m["login"],
                "github_id": m["id"],
                "profile_url": m["html_url"],
            }
            for m in members
        ],
        key=lambda r: r["login"].lower(),
    )
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["login", "github_id", "profile_url"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows)} members → {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Plone GitHub team members and ensure alumni team exists."
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub personal access token (default: $GITHUB_TOKEN)",
    )
    parser.add_argument("--org", default=DEFAULT_ORG, help=f"GitHub org (default: {DEFAULT_ORG})")
    parser.add_argument(
        "--developers-team",
        default=DEFAULT_DEVELOPERS_TEAM,
        help=f"Developers team slug (default: {DEFAULT_DEVELOPERS_TEAM})",
    )
    parser.add_argument(
        "--alumni-team",
        default=DEFAULT_ALUMNI_TEAM,
        help=f"Alumni team slug (default: {DEFAULT_ALUMNI_TEAM})",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for output CSV files (default: current directory)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.token:
        print("Error: GitHub token required. Set $GITHUB_TOKEN or use --token.")
        return 1

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Org: {args.org}")
    print()

    # --- Developers team ---
    print(f"Fetching '{args.developers_team}' team members...")
    dev_members = get_team_members(args.token, args.org, args.developers_team)
    if dev_members is None:
        print(f"  Error: team '{args.developers_team}' not found in org '{args.org}'.")
        return 1
    dev_csv = out / f"team-{args.developers_team}.csv"
    save_members_csv(dev_members, dev_csv)

    # --- Alumni team ---
    print(f"\nChecking '{args.alumni_team}' team...")
    alumni_team_meta = get_team(args.token, args.org, args.alumni_team)

    if alumni_team_meta is None:
        print(f"  Team '{args.alumni_team}' does not exist — creating it...")
        alumni_team_meta = create_team(
            args.token,
            args.org,
            name="alumni-developers",
            description=(
                "Former active Plone developers who are no longer regularly "
                "contributing to Plone core repositories."
            ),
        )
        print(f"  Created team '{alumni_team_meta['name']}' (id={alumni_team_meta['id']})")
    else:
        print(f"  Team '{args.alumni_team}' already exists (id={alumni_team_meta['id']})")

    alumni_members = get_team_members(args.token, args.org, args.alumni_team) or []
    alumni_csv = out / f"team-{args.alumni_team}.csv"
    save_members_csv(alumni_members, alumni_csv)

    print(f"\nDone.")
    print(f"  Developers:       {len(dev_members)} members")
    print(f"  Alumni-developers:{len(alumni_members)} members")
    return 0


if __name__ == "__main__":
    sys.exit(main())
