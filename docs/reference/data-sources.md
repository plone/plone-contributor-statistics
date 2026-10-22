(reference-data-sources)=

# Data sources

This page lists every source of data in the repository, the years it covers, and the script and Make target that collect it.
Years covered are the years for which files exist in the repository.

See {doc}`/explanation/scope` for why these sources were chosen, and {doc}`/explanation/history-and-coverage` for what they cover in each era.

## Collected from APIs

| Source | Origin | Years covered | Script | Output | Make target |
|---|---|---|---|---|---|
| Commits | Local bare clones of all repositories of the `plone` GitHub organisation, accounts linked through the GitHub GraphQL API and the identities in `curated/mappings/identities.csv` | 2003–2025 | `scripts/collect/plone_contributors.py`, `scripts/lib/git_history.py` | `collected/contributors/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats` |
| Merged pull requests | GitHub REST API, pull requests of all repositories of the `plone` organisation | 2003–2025 | `scripts/collect/plone_contributors.py` | `collected/contributors/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats` |
| Pull request interactions | GitHub GraphQL API, with the REST API for long threads and code review comments | 2010–2025 | `scripts/collect/plone_pr_interactions.py` | `collected/pr-interactions/YYYY-plone-pr-interactions.csv`, `reports/pr-interactions/github-pr-interactions-report-YYYY.md` | `make pr-interactions-all-years`, `make pr-interactions` |
| Changelog entries | The changelog files at the tips of the default branch and the release branches of all repositories of the `plone` organisation, in the same local clones as the commits | 2002–2025 | `scripts/collect/plone_changelogs.py`, `scripts/lib/changelogs.py`, `scripts/lib/git_history.py` | `collected/changelogs/YYYY-plone-changelog-entries.csv` | `make run-changelogs` |
| Commit mail domains | The author addresses of the commits in the same local clones of all repositories of the `plone` organisation as the changelog entries, the domain only | 2002–2026 | `scripts/collect/plone_commit_domains.py`, `scripts/lib/commit_authors.py`, `scripts/lib/git_history.py` | `collected/commit-domains/YYYY-plone-commit-domains.csv` | `make run-commit-domains` |
| PLIPs | GitHub REST API, issues with the PLIP label in `Products.CMFPlone`, `volto`, `plone.restapi` and `aurora` | all years in one file | `scripts/collect/plone_plips.py` | `collected/plips/plone-plips.csv`, `collected/plips/plone-plips-detailed.csv` | `make run-plips` |

## Curated by hand

The curated community data is in `curated/community-contributions/`, one file per year; the PLIPs before GitHub are in one file in `curated/plips/`.

| Data | Years covered | File | Source column |
|---|---|---|---|
| Board of Directors | 2004–2025 | `curated/community-contributions/YYYY-board-of-directors.csv` | 2004–2025 |
| Plone Conference organisers | 2003–2025 | `curated/community-contributions/YYYY-plone-conference.csv` | 2003–2025 |
| Plone Conference trainings | 2003–2025 | `curated/community-contributions/YYYY-plone-conference-trainings.csv` | 2003–2024 |
| Conference talks | 2021 | `curated/community-contributions/YYYY-conference-talks.csv` | 2021 |
| Release managers | 2004–2025 | `curated/community-contributions/YYYY-release-managers.csv` | 2004–2025 |
| Team leaders | 2004–2025 | `curated/community-contributions/YYYY-team-leaders.csv` | 2004–2025 |
| Sprints | 2003–2025 | `curated/community-contributions/YYYY-sprints.csv` | 2003–2025 |
| Podcast hosts | 2020–2025 | `curated/community-contributions/YYYY-podcasts.csv` | 2020–2025 |
| World Plone Day events | 2008–2019, 2021–2025 | `curated/community-contributions/YYYY-world-plone-day-event.csv` | 2008–2019, 2021–2025 |
| World Plone Day talks | 2021–2025 | `curated/community-contributions/YYYY-world-plone-day-talks.csv` | 2021–2025 |
| PLIPs before GitHub | 2004–2013 | `curated/plips/plone-plips-before-github.csv` | all rows |

## Derived from other files

| Data | Inputs | Script | Output | Make target |
|---|---|---|---|---|
| Organisation statistics per year | contributor and changelog files, the {doc}`registers </reference/mapping-files>` | `scripts/derive/organisation_stats.py` | `derived/organisation-contributors/YYYY-plone-organisation-contributors.csv` | `make run-organisation-stats`, `make run-organisation-stats-year` |
| Multi-year summaries | organisation and contributor files | `scripts/derive/multi_year_summary.py` | `derived/summaries/summary-past-*-years-*.csv`, `reports/summaries/STATISTICS-PAST-*-YEARS.txt` | `make three-year-summary`, `make five-year-summary`, `make ten-year-summary` |
| Contributor report | contributor, changelog and organisation files | `scripts/report/generate_contributor_report.py` | `reports/github-contributor-report.md` | `make generate-report` |
| PLIPs per organisation | `collected/plips/plone-plips-detailed.csv`, the registers | `scripts/derive/plip_organisation_stats.py` | `derived/plone-plip-organisations.csv` | `make run-plip-organisations` |
| Community recognition | curated files, yearly organisation files, PLIP files, recognition files | `scripts/report/generate_community_recognition_report.py` | `reports/community-recognition.md`, `derived/community-recognition/YYYY-community-recognition-report.csv` | `make community-recognition` |
| Yearly activity and graphs | contributor and organisation files | `scripts/derive/yearly_activity_analysis.py`, `scripts/report/generate_yearly_graphs.py` | `derived/yearly-activity-statistics.csv`, `reports/graphs/` | `make yearly-activity`, `make yearly-graphs` |
