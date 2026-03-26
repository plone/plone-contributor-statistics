# GitHub Team Management

Scripts for comparing Plone contributor activity with GitHub team membership,
to help move inactive developers to the `alumni-developers` team.

## Workflow

### 1. Fetch current team members

```bash
export GITHUB_TOKEN=ghp_your_token_here

python fetch_github_teams.py
```

This will:
- Download all members of the `plone/developers` team → `team-developers.csv`
- Check if `plone/alumni-developers` exists; **create it** if not → `team-alumni-developers.csv`

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--token` | `$GITHUB_TOKEN` | GitHub personal access token |
| `--org` | `plone` | GitHub organisation |
| `--developers-team` | `developers` | Developers team slug |
| `--alumni-team` | `alumni-developers` | Alumni team slug |
| `--output-dir` | `.` | Where to write the CSV files |

The token needs the `read:org` scope to read team members and `write:org` to
create the alumni team if it doesn't exist yet.

---

### 2. Generate the active-users list (if not already done)

From the repository root:

```bash
python extract_active_github_users.py
# produces: active-github-users-2023-2025.csv
```

---

### 3. Compare team membership with contributor statistics

```bash
python compare_teams_with_statistics.py
```

The script auto-detects the most recent `active-github-users-*.csv` in the
parent directory. It produces:

- `TEAM-COMPARISON-REPORT.txt` — full human-readable report with three sections:
  - **Move to alumni-developers** — in the developers team but not active
  - **Stay in developers team** — active developers to keep
  - **Active but not in team** — informational, for reference
- `move-to-alumni.txt` — plain list of usernames to move (one per line)

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--active-users` | auto-detected | Path to `active-github-users-*.csv` |
| `--developers-csv` | `./team-developers.csv` | Developers team CSV |
| `--alumni-csv` | `./team-alumni-developers.csv` | Alumni team CSV |
| `--output` | `./TEAM-COMPARISON-REPORT.txt` | Report output path |
| `--min-commits` | `0` | Minimum commits to count as active |
| `--min-prs` | `0` | Minimum PRs to count as active |

Use `--min-commits` and `--min-prs` to raise the activity threshold if you
want to be stricter:

```bash
# Only keep developers with at least 1 PR or 5 commits in the last 3 years
python compare_teams_with_statistics.py --min-prs 1
python compare_teams_with_statistics.py --min-commits 5
```

---

## Output files (gitignored)

| File | Description |
|------|-------------|
| `team-developers.csv` | Current developers team snapshot |
| `team-alumni-developers.csv` | Current alumni-developers team snapshot |
| `TEAM-COMPARISON-REPORT.txt` | Full comparison report |
| `move-to-alumni.txt` | Plain list of alumni candidates |

These files contain GitHub usernames but no secrets, so they are safe to
commit if you want to track the snapshot over time.

---

## Token permissions required

| Action | Scope needed |
|--------|-------------|
| Read team members | `read:org` |
| Create alumni team | `write:org` |
