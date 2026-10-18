# Plan: calculate the recognition points as the points file says

Decided by Jens Klein (option A): the script applies `community-recognition-points.csv` as written to the corrected data.
The published levels of August 2026 are explained in the docs, not reproduced.
Closes #95, refs #56, #14.

## Rules taken from the points file

- Report year Y = 2025.
  Community points come from the curated files of Y ("1 year").
  Code points come from the five years Y-4 to Y ("past five years"), so 2021–2025.
- Strategic sprint: 12 points per sprint, split equally among its organising entities; each entity gets points for at most one sprint per year.
- Release manager: 12 points per person.
- Team leader: 6 points per team, limited to one leader, so split among the listed leaders (unchanged).
- Board: 6 points per member, including the non-voting officers (#97).
- Podcast: 6 points per series, split among its hosts (unchanged; no podcasts in 2025).
- World Plone Day event: 3 points per event, split among its organising entities.
- World Plone Day talk: 1 point per talk, at most 4 per organisation (unchanged).
- Conference: 24 points split among the organisers of the previous edition (unchanged).
- Training: 4 points per training, split among the trainers' organisations.
- PRs: the average number of merged PRs per year over the five years, from the yearly organisation files with the yearly overrides; thresholds 100/50/20/10 give 20/10/4/2 points.
- PLIPs: the PLIPs closed in the five years, counted for the author's organisation in the year the PLIP was closed; thresholds 10/6/2 give 15/9/3 points.
  "Merged and released" can't be checked from the data, so closed counts as merged.

## Code

1. `plip_organisation_stats.py` (the Make target `run-plip-organisations` already calls it): maps each PLIP to an organisation by the year it was closed, or created if open; writes `plone-plip-organisations.csv` with the existing columns.
2. `generate_community_recognition_report.py`: report year and window as parameters, PRs from the yearly organisation files, PLIPs from `plip_organisation_stats`, the changed sprint, WPD event and training rules, the paths as parameters for tests.
3. Offline tests for every changed rule and for the PLIP mapping.

## Docs

- `docs/explanation/community-recognition.md`: how the script calculates; why the published levels differ (the reconstruction, the fork, Érico Andrei's comment in #28); only repositories of the `plone` organisation count.
- `docs/reference/make-targets.md` and `docs/explanation/known-limitations.md`: the PLIP file.

## Check

- Regenerate `plone-plip-organisations.csv` and the report.
- Compare the levels with the report on main and with the published levels; explain the differences in the pull request.
