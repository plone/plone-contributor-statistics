(reference-data-sources)=

# Data sources

This page lists every source of data in the repository, the years it covers, and the script and Make target that collect it.
Years covered give the first year for which files exist in the repository; the data reaches up to the last year collected or recorded, unless the range is closed.

See {doc}`/explanation/scope` for why these sources were chosen, and {doc}`/explanation/history-and-coverage` for what they cover in each era.

## Collected from GitHub

| Source | Origin | Years covered | Script | Output | Make target |
|---|---|---|---|---|---|
| Commits | Local bare clones of all repositories of the `plone` GitHub organisation, accounts linked through the GitHub GraphQL API and the identities in `curated/mappings/identities.csv` | from 2003 | `scripts/collect/plone_contributors.py`, `scripts/lib/git_history.py` | `collected/contributors/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats` |
| Merged pull requests | GitHub REST API, pull requests of all repositories of the `plone` organisation | from 2003 | `scripts/collect/plone_contributors.py` | `collected/contributors/YYYY-plone-contributors.csv` | `make run-stats-all-years`, `make run-stats` |
| Pull request interactions | GitHub GraphQL API, with the REST API for long threads and code review comments | from 2010 | `scripts/collect/plone_pr_interactions.py` | `collected/pr-interactions/YYYY-plone-pr-interactions.csv`, `reports/pr-interactions/github-pr-interactions-report-YYYY.md` | `make pr-interactions-all-years`, `make pr-interactions` |
| Changelog entries | The changelog files at the tips of the default branch and the release branches of all repositories of the `plone` organisation, in the same local clones as the commits | from 2002 | `scripts/collect/plone_changelogs.py`, `scripts/lib/changelogs.py`, `scripts/lib/git_history.py` | `collected/changelogs/YYYY-plone-changelog-entries.csv` | `make run-changelogs` |
| Commit mail domains | The author addresses of the commits in the same local clones of all repositories of the `plone` organisation as the changelog entries, the domain only, never the local part of an address | from 2002 | `scripts/collect/plone_commit_domains.py`, `scripts/lib/commit_authors.py`, `scripts/lib/git_history.py` | `collected/commit-domains/YYYY-plone-commit-domains.csv` | `make run-commit-domains` |
| PLIPs | GitHub REST API, issues with the PLIP label in `Products.CMFPlone`, `volto`, `plone.restapi` and `aurora` | all years in one file | `scripts/collect/plone_plips.py` | `collected/plips/plone-plips.csv`, `collected/plips/plone-plips-detailed.csv` | `make run-plips` |

## Curated by hand

The curated community data is in `curated/community/`, one file per kind with the rows of every year; the PLIPs before GitHub are in one file in `curated/plips/`.

Every community row cites its sources by their ids in the source register, in `sources`, and gives them in words in `cited_as`.
Two events of a year may have none: the Plone Conference of a year and the online edition of World Plone Day, which hold the rows that point to them, see {doc}`/explanation/curated-community-data`.
The PLIPs before GitHub give the record of every row in their `Source` column.

| Data | Years covered | File |
|---|---|---|
| Board of Directors | from 2004 | `curated/community/board-of-directors.csv` |
| Plone Conference organisers | from 2003 | `curated/community/organisers.csv` |
| Plone Conference trainings | from 2003 | `curated/community/trainings.csv` |
| Conference talks | from 2003 | `curated/community/talks.csv` |
| Release managers | from 2004 | `curated/community/release-managers.csv` |
| Team leaders | from 2004 | `curated/community/team-leaders.csv` |
| Sprints, with their organisers | from 2003 | `curated/community/events.csv`, `curated/community/organisers.csv` |
| Podcast hosts | from 2020 | `curated/community/podcasts.csv` |
| World Plone Day events, with their organisers | from 2008, none in 2020 | `curated/community/events.csv`, `curated/community/organisers.csv` |
| World Plone Day talks | from 2021 | `curated/community/talks.csv` |
| PLIPs before GitHub | 2004–2013 | `curated/plips/plone-plips-before-github.csv` |
| People, identities, affiliations, citations, organisations, bot accounts and excluded repositories | all years | the registers and lists in `curated/mappings/`, see {doc}`mapping-files` |
| Sources | all years | the source register `curated/sources/sources.csv` and its excerpts, see {doc}`/how-to/capture-a-source` |

## Derived from other files

| Data | Inputs | Script | Output | Make target |
|---|---|---|---|---|
| Organisation statistics per year | contributor and changelog files, the {doc}`registers </reference/mapping-files>` | `scripts/derive/organisation_stats.py` | `derived/organisation-contributors/YYYY-plone-organisation-contributors.csv` | `make run-organisation-stats`, `make run-organisation-stats-year` |
| Multi-year summaries | organisation and contributor files | `scripts/derive/multi_year_summary.py` | `derived/summaries/summary-past-*-years-*.csv`, `reports/summaries/STATISTICS-PAST-*-YEARS.txt` | `make three-year-summary`, `make five-year-summary`, `make ten-year-summary` |
| Contributor report | contributor, changelog and organisation files | `scripts/report/generate_contributor_report.py` | `reports/github-contributor-report.md` | `make generate-report` |
| PLIPs per organisation | `collected/plips/plone-plips-detailed.csv`, the registers | `scripts/derive/plip_organisation_stats.py` | `derived/plone-plip-organisations.csv` | `make run-plip-organisations` |
| Community recognition | curated files, yearly organisation files, PLIP files, the levels file | `scripts/report/generate_community_recognition_report.py` | `reports/community-recognition.md`, `derived/community-recognition/YYYY-community-recognition-report.csv` | `make community-recognition` |
| Community page data | contributor, organisation and curated files, the registers, the recognition | `scripts/derive/community_page.py` | `derived/community-page.json` | `make community-page` |
| Yearly activity and graphs | contributor and organisation files | `scripts/derive/yearly_activity_analysis.py`, `scripts/report/generate_yearly_graphs.py` | `derived/yearly-activity-statistics.csv`, `reports/graphs/` | `make yearly-activity`, `make yearly-graphs` |
