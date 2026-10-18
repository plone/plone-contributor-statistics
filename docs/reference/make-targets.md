(reference-make-targets)=

# Make targets

This page lists the targets of the `Makefile`, grouped by purpose.
`make help` prints the full list.

Targets of archived scripts were removed; `archive/README.md` lists the scripts.

## Variables

Some targets take a year from a variable.
The defaults are in `scripts/lib/years.py`: the last completed year.
Set a variable on the command line to use another year, for example `make five-year-summary SUMMARY_END=2025`.

| Variable | Used by |
|---|---|
| `SUMMARY_END` | The last year of `three-year-summary`, `five-year-summary` and `ten-year-summary`. |
| `RECOGNITION_YEAR` | The year of `community-recognition`. |
| `YEAR` | The year of `year`, `run-stats`, `pr-interactions` and `run-organisation-stats-year`; defaults to the last completed year. |

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
| `make clean` | Deletes caches, checkpoint files and the built documentation; never committed files. | works |
| `make status` | Prints the Python version and whether a GitHub token is configured. | works |

## A whole year

| Target | Does | Status |
|---|---|---|
| `make year` | Collects, derives and reports `YEAR` in pipeline order, see {doc}`/how-to/prepare-a-new-year`. | works |

## Collection

| Target | Does | Status |
|---|---|---|
| `make run-stats-all-years` | Collects commits and merged pull requests from 2003 to the current year in one run. | works |
| `make run-stats` | Collects commits and merged pull requests of `YEAR`. | works |
| `make run-stats-custom` | Prints how to collect a custom date range. | works |
| `make pr-interactions-all-years` | Collects pull request interactions from 2010 to the current year in one run. | works |
| `make pr-interactions` | Collects pull request interactions of `YEAR`. | works |
| `make run-plips` | Collects all PLIPs. | works |

## Aggregation and reports

| Target | Does | Status |
|---|---|---|
| `make run-organisation-stats` | Writes the organisation statistics of every year with a contributor file. | works |
| `make run-organisation-stats-year` | Writes the organisation statistics of `YEAR`. | works |
| `make three-year-summary` | Writes the summary of the three years up to `SUMMARY_END`. | works |
| `make five-year-summary` | Writes the summary of the five years up to `SUMMARY_END`. | works |
| `make ten-year-summary` | Writes the summary of the ten years up to `SUMMARY_END`. | works |
| `make generate-report` | Writes `reports/github-contributor-report.md`. | works |
| `make community-recognition` | Writes the community recognition report of `RECOGNITION_YEAR`. | works |
| `make yearly-activity` | Writes `derived/yearly-activity-statistics.csv`. | works |
| `make yearly-graphs` | Runs `yearly-activity` and draws the graphs in `reports/graphs/`. | works |
| `make analyze-independent` | Lists unmapped contributors worth researching. | works |
| `make run-plip-organisations` | Writes `derived/plone-plip-organisations.csv` from `collected/plips/plone-plips-detailed.csv` and the mapping files. | works |

## Documentation

| Target | Does | Status |
|---|---|---|
| `make docs-install` | Installs `requirements-docs.txt`. | works |
| `make docs` | Builds this documentation to `docs/_build/html`; warnings are errors. | works |
| `make docs-linkcheck` | Checks the links in this documentation. | works |
| `make docs-clean` | Deletes `docs/_build`. | works |
