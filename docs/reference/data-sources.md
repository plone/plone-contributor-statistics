(reference-data-sources)=

# Data sources

This page lists every source of data in the repository, the years it covers, and the script and Make target that collect it.
Years covered are the years for which files exist in the repository.

See {doc}`/explanation/scope` for why these sources were chosen, and {doc}`/explanation/history-and-coverage` for what they cover in each era.

## Collected from APIs

| Source | Origin | Years covered | Script | Output | Make target |
|---|---|---|---|---|---|
| Commits | Local bare clones of all repositories of the `plone` GitHub organisation, accounts linked through the GitHub GraphQL API and `commit_authors.csv` | 2003–2025 | `plone_contributors.py`, `git_history.py` | `data/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats-YYYY` |
| Merged pull requests | GitHub REST API, pull requests of all repositories of the `plone` organisation | 2003–2025 | `plone_contributors.py` | `data/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats-YYYY` |
| Pull request interactions | GitHub GraphQL API, with the REST API for long threads and code review comments | 2010–2025 | `plone_pr_interactions.py` | `data/YYYY-plone-pr-interactions.csv`, `reports/github-pr-interactions-report-YYYY.md` | `make pr-interactions-all-years`, `make pr-interactions-YYYY` |
| Volto contributors | GitHub REST API contributors of `plone/volto`, and the search API per person | 2016–2025 | `volto_stats.py` | `data/YYYY-volto-stats.csv` | `make run-volto-stats-YYYY` |
| PLIPs | GitHub REST API, issues with the PLIP label in `Products.CMFPlone`, `volto` and `plone.restapi` | all years in one file | `plone_plips.py` | `plone-plips.csv`, `plone-plips-detailed.csv` | `make run-plips` |

## Curated by hand

All curated files are in `data/community-contributions/`, one file per year.

| Data | Years covered | File | Source column |
|---|---|---|---|
| Board of Directors | 2004–2025 | `data/community-contributions/YYYY-board-of-directors.csv` | 2004–2025 |
| Plone Conference organisers | 2003–2025 | `data/community-contributions/YYYY-plone-conference.csv` | 2003–2019 |
| Plone Conference trainings | 2020–2025 | `data/community-contributions/YYYY-plone-conference-trainings.csv` | 2020–2024 |
| Release managers | 2004–2025 | `data/community-contributions/YYYY-release-managers.csv` | 2004–2025 |
| Team leaders | 2020–2025 | `data/community-contributions/YYYY-team-leaders.csv` | 2020–2024 |
| Strategic sprints | 2020–2025 | `data/community-contributions/YYYY-strategic-sprints.csv` | 2020–2024 |
| Podcast hosts | 2020–2025 | `data/community-contributions/YYYY-podcasts.csv` | none |
| World Plone Day events | 2021–2025 | `data/community-contributions/YYYY-world-plone-day-event.csv` | `Reference` column |
| World Plone Day talks | 2021–2025 | `data/community-contributions/YYYY-world-plone-day-talks.csv` | `YouTube ID` column |

## Derived from other files

| Data | Inputs | Script | Output | Make target |
|---|---|---|---|---|
| Organisation statistics per year | contributor files, {doc}`mapping files </reference/mapping-files>` | `organisation_stats.py` | `data/YYYY-plone-organisation-contributors.csv` | `make run-organisation-stats`, `make run-organisation-stats-YYYY` |
| Multi-year summaries | organisation and contributor files | `multi_year_summary.py` | `summary-past-*-years-*.csv`, `STATISTICS-PAST-*-YEARS.txt` | `make three-year-summary`, `make five-year-summary`, `make ten-year-summary` |
| Contributor report | contributor and organisation files | `generate_contributor_report.py` | `reports/github-contributor-report.md` | `make generate-report` |
| Volto report | Volto files, mapping files | `generate_volto_team_report.py` | `reports/volto.md` | `make generate-volto-report` |
| PLIPs per organisation | `plone-plips-detailed.csv`, mapping files | `plip_organisation_stats.py` | `plone-plip-organisations.csv` | `make run-plip-organisations` |
| Community recognition | curated files, yearly organisation files, PLIP files, recognition files | `generate_community_recognition_report.py` | `reports/community-recognition.md`, `data/community-contributions/YYYY-community-recognition-report.csv` | `make community-recognition` |
| Yearly activity and graphs | contributor and organisation files | `yearly_activity_analysis.py`, `generate_yearly_graphs.py` | `yearly-activity-statistics.csv`, `graphs/` | `make yearly-activity`, `make yearly-graphs` |
