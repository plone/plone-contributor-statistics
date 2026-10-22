# Collected data

Written by the collectors in `scripts/collect/` from GitHub; never edit by hand.
Collect again with `make year YEAR=2025` or the single collection targets; see [Collect the data again](https://plone.github.io/plone-contributor-statistics/docs/how-to/collect-data-again.html).

| Folder | Holds | Make target |
|---|---|---|
| `contributors/` | Commits and merged pull requests per person, one file per year. | `run-stats`, `run-stats-all-years` |
| `pr-interactions/` | Comments and reviews per pull request, one file per year. | `pr-interactions`, `pr-interactions-all-years` |
| `plips/` | All PLIPs, per author and per PLIP. | `run-plips` |
| `changelogs/` | Changelog entries per person, one file per year. | `run-changelogs` |
| `commit-domains/` | Mail domains of the commit authors per person, one file per year. | `run-commit-domains` |

See [Data files](https://plone.github.io/plone-contributor-statistics/docs/reference/data-files.html) for the columns.
