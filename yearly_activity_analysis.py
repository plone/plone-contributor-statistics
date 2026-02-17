#!/usr/bin/env python3
"""
Yearly Activity Analysis for Plone GitHub Statistics

Aggregates per-year contributor and organisation CSV files into a single
yearly-activity-statistics.csv for use by the graph generator.
"""

import pandas as pd
from pathlib import Path
import glob


def main():
    print("Plone Yearly Activity Analysis")
    print("=" * 40)

    rows = []

    # Find all yearly contributor CSV files
    contributor_files = sorted(glob.glob("[0-9][0-9][0-9][0-9]-plone-contributors.csv"))

    if not contributor_files:
        print("No yearly contributor CSV files found!")
        return 1

    for contrib_file in contributor_files:
        year = int(Path(contrib_file).name.split("-")[0])
        org_file = f"{year}-plone-organisation-contributors.csv"

        # Load contributor data
        try:
            contrib_df = pd.read_csv(contrib_file)
        except Exception as e:
            print(f"  Skipping {year}: error reading {contrib_file}: {e}")
            continue

        total_commits = int(contrib_df["total_commits"].sum())
        total_prs = int(contrib_df["total_pull_requests"].sum())
        total_contributors = len(contrib_df)

        # Count unique repositories across all contributors
        unique_repos = set()
        for repos_str in contrib_df["repositories"].dropna():
            for repo in str(repos_str).split(", "):
                repo = repo.strip()
                if repo:
                    unique_repos.add(repo)

        # Load organisation data if available
        total_orgs = 0
        if Path(org_file).exists():
            try:
                org_df = pd.read_csv(org_file)
                total_orgs = len(org_df)
            except Exception:
                pass

        pr_to_commit_ratio = (total_prs / total_commits * 100) if total_commits > 0 else 0
        commits_per_contributor = (total_commits / total_contributors) if total_contributors > 0 else 0
        prs_per_contributor = (total_prs / total_contributors) if total_contributors > 0 else 0

        rows.append({
            "year": year,
            "total_commits": total_commits,
            "total_pull_requests": total_prs,
            "total_contributors": total_contributors,
            "total_organisations": total_orgs,
            "unique_repositories": len(unique_repos),
            "pr_to_commit_ratio": round(pr_to_commit_ratio, 2),
            "commits_per_contributor": round(commits_per_contributor, 2),
            "prs_per_contributor": round(prs_per_contributor, 2),
        })

        print(f"  {year}: {total_commits} commits, {total_prs} PRs, "
              f"{total_contributors} contributors, {total_orgs} orgs, "
              f"{len(unique_repos)} repos")

    df = pd.DataFrame(rows)
    df = df.sort_values("year")

    # Calculate year-over-year growth rates
    df["commits_growth"] = df["total_commits"].pct_change() * 100
    df["prs_growth"] = df["total_pull_requests"].pct_change() * 100
    df["contributors_growth"] = df["total_contributors"].pct_change() * 100
    df["orgs_growth"] = df["total_organisations"].pct_change() * 100

    # Round growth rates
    for col in ["commits_growth", "prs_growth", "contributors_growth", "orgs_growth"]:
        df[col] = df[col].round(1)

    output_file = "yearly-activity-statistics.csv"
    df.to_csv(output_file, index=False)

    print(f"\nSaved {len(df)} years of data to {output_file}")
    print(f"Year range: {df['year'].min()}-{df['year'].max()}")

    return 0


if __name__ == "__main__":
    exit(main())
