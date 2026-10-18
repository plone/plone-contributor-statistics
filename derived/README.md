# Derived data

Computed from the collected data and the curated input, mostly by the scripts in `scripts/derive/`; never edit by hand.
It is committed so that every number in the reports can be traced.
After a change to the mapping, regenerate it as described in [Regenerate the statistics after a mapping change](https://plone.github.io/plone-contributor-statistics/how-to/regenerate-after-a-mapping-change.html).

| Path | Holds | Make target |
|---|---|---|
| `organisation-contributors/` | Commits and merged pull requests per organisation, one file per year. | `run-organisation-stats`, `run-organisation-stats-year` |
| `summaries/` | Organisations over the last three, five and ten years. | `three-year-summary`, `five-year-summary`, `ten-year-summary` |
| `community-recognition/` | Recognition points and levels per organisation, one file per year, written by `scripts/report/generate_community_recognition_report.py` together with its report. | `community-recognition` |
| `yearly-activity-statistics.csv` | Totals per year. | `yearly-activity` |
| `plone-plip-organisations.csv` | PLIPs per organisation. | `run-plip-organisations` |
| `community-page.json` | Every number of the community page, from `scripts/derive/community_page.py`. | `community-page` |

See [Data files](https://plone.github.io/plone-contributor-statistics/reference/data-files.html) for the columns.
