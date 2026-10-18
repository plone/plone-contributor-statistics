(reference-make-targets)=

# Make targets

This page lists the targets of the `Makefile`, grouped by purpose.
`make help` prints the full list.
Targets with `YYYY` exist once per year.

See {doc}`/explanation/known-limitations` for the effect of the broken targets.

## Setup and maintenance

| Target | Does | Status |
|---|---|---|
| `make install` | Installs `requirements.txt`. | works |
| `make setup` | Runs `install` and creates a `.env` template for the GitHub token. | works |
| `make dev-setup` | Runs `setup` and installs development tools. | works |
| `make test` | Runs the test suite with pytest. | works |
| `make check` | Runs `lint`, compiles all scripts and checks the installed requirements. | works |
| `make lint` | Runs flake8 on the scripts, if installed. | works |
| `make format` | Formats the scripts. | works |
| `make clean` | Deletes generated files in the repository root and `graphs/`. | works |
| `make status` | Prints the Python version and whether a GitHub token is configured. | works |

## Collection

| Target | Does | Status |
|---|---|---|
| `make run-stats-all-years` | Collects commits and merged pull requests from 2003 to the current year in one run. | works |
| `make run-stats` | Collects commits and merged pull requests of the current year. | works |
| `make run-stats-YYYY` | Collects commits and merged pull requests of one year. | works |
| `make run-stats-custom` | Prints how to collect a custom date range. | works |
| `make pr-interactions-all-years` | Collects pull request interactions from 2010 to the current year in one run. | works |
| `make pr-interactions` | Collects pull request interactions of the current year. | works |
| `make pr-interactions-YYYY` | Collects pull request interactions of one year. | works |
| `make run-volto-stats` | Collects Volto contributor statistics of the current year. | works |
| `make run-volto-stats-YYYY` | Collects Volto contributor statistics of one year. | works |
| `make run-plips` | Collects all PLIPs. | works |
| `make npm-packages` | Collects npm packages and downloads of the organisations in `npm_mapping.txt`. | works |
| `make pypi-packages` | Should collect PyPI packages. | broken: calls `pypi_package_stats.py`, the script is `pypi_package_statistics.py` |

## Aggregation and reports

| Target | Does | Status |
|---|---|---|
| `make run-organisation-stats` | Writes the organisation statistics of every year with a contributor file. | works |
| `make run-organisation-stats-YYYY` | Writes the organisation statistics of one year. | works |
| `make three-year-summary` | Writes the summary of 2022–2024. | works |
| `make five-year-summary` | Writes the summary of 2020–2024. | works |
| `make ten-year-summary` | Writes the summary of 2015–2024. | works |
| `make generate-report` | Writes `reports/github-contributor-report.md`. | works |
| `make generate-volto-report` | Writes `reports/volto.md`. | works |
| `make community-recognition` | Writes the community recognition report. | works |
| `make yearly-activity` | Writes `yearly-activity-statistics.csv`. | works |
| `make yearly-graphs` | Runs `yearly-activity` and draws the graphs in `graphs/`. | works |
| `make flourish-graph-organisation-contributors-csv-file` | Writes the organisation chart data for Flourish. | works |
| `make flourish-graph-individual-contributors-csv-file` | Writes the contributor chart data for Flourish. | works |
| `make analyze-independent` | Lists unmapped contributors worth researching. | works |
| `make analyze-plip-levels` | Writes a PLIP contributor level analysis to the repository root. | works |
| `make run-plip-organisations` | Should write `plone-plip-organisations.csv`. | broken: `plip_organisation_stats.py` is not in the repository |
| `make generate-plip-report` | Should write `reports/plips.md`. | broken: `generate_plip_report.py` is not in the repository |

## Not part of the current method

| Target | Does | Status |
|---|---|---|
| `make run-contributors` | Runs `plone_contributor_statistics.py`, based on the GitHub contributor statistics API. | not part of the current method |
| `make run-organisations` | Runs `plone_companies.py`, which guessed organisations from GitHub profiles and email domains. | not part of the current method |
| `make run-all` | Should run several collectors. | broken: depends on the missing target `run-companies` |

## Documentation

| Target | Does | Status |
|---|---|---|
| `make docs-install` | Installs `requirements-docs.txt`. | works |
| `make docs` | Builds this documentation to `docs/_build/html`; warnings are errors. | works |
| `make docs-linkcheck` | Checks the links in this documentation. | works |
| `make docs-clean` | Deletes `docs/_build`. | works |
