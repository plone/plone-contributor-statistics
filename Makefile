# Plone contributor statistics; see docs/reference/make-targets.md
# Scripts run from the repository root as modules: python -m scripts.<stage>.<name>

# The year to collect and derive; defaults to the last completed year
YEAR ?= $(shell python -c 'from scripts.lib.years import last_completed_year; print(last_completed_year())')
# Default years of the summaries and the recognition report, from scripts/lib/years.py
SUMMARY_END ?= $(shell python -c 'from scripts.lib.years import SUMMARY_END_YEAR; print(SUMMARY_END_YEAR)')
RECOGNITION_YEAR ?= $(shell python -c 'from scripts.lib.years import RECOGNITION_YEAR; print(RECOGNITION_YEAR)')
# The $(1) years up to and including SUMMARY_END
summary_years = $(shell seq $$(($(SUMMARY_END) - $(1) + 1)) $(SUMMARY_END))

.PHONY: help install setup dev-setup year \
	run-stats run-stats-all-years run-stats-custom pr-interactions pr-interactions-all-years \
	run-volto-stats run-plips \
	run-organisation-stats run-organisation-stats-year run-plip-organisations \
	three-year-summary five-year-summary ten-year-summary yearly-activity \
	yearly-graphs generate-report generate-volto-report community-recognition \
	analyze-independent clean lint format check test status \
	docs-install docs docs-linkcheck docs-clean

help:
	@echo "Plone contributor statistics"
	@echo ""
	@echo "Setup:"
	@echo "  install           Install Python dependencies"
	@echo "  setup             Install dependencies and create a .env template for the GitHub token"
	@echo "  dev-setup         Setup plus development tools"
	@echo ""
	@echo "A whole year (YEAR, default: the last completed year):"
	@echo "  year              Collect, derive and report YEAR, in pipeline order"
	@echo ""
	@echo "Collect (needs a GitHub token):"
	@echo "  run-stats         Commits and merged pull requests of YEAR"
	@echo "  run-stats-all-years Commits and merged pull requests, 2003 to now, in one run"
	@echo "  run-stats-custom  Print how to collect a custom date range"
	@echo "  pr-interactions   Pull request interactions of YEAR"
	@echo "  pr-interactions-all-years Pull request interactions, 2010 to now, in one run"
	@echo "  run-volto-stats   Volto contributor statistics of YEAR"
	@echo "  run-plips         All PLIPs"
	@echo ""
	@echo "Derive:"
	@echo "  run-organisation-stats Organisation statistics of every year with a contributor file"
	@echo "  run-organisation-stats-year Organisation statistics of YEAR"
	@echo "  run-plip-organisations PLIPs per organisation"
	@echo "  three-year-summary Summary of the 3 years up to SUMMARY_END ($(SUMMARY_END))"
	@echo "  five-year-summary Summary of the 5 years up to SUMMARY_END"
	@echo "  ten-year-summary  Summary of the 10 years up to SUMMARY_END"
	@echo "  yearly-activity   Yearly totals of all years"
	@echo ""
	@echo "Report:"
	@echo "  yearly-graphs     Graphs of the yearly totals (runs yearly-activity)"
	@echo "  generate-report   Contributor and organisation report"
	@echo "  generate-volto-report Volto report"
	@echo "  community-recognition Community recognition report of RECOGNITION_YEAR ($(RECOGNITION_YEAR))"
	@echo ""
	@echo "Tools:"
	@echo "  analyze-independent List unmapped contributors worth researching"
	@echo ""
	@echo "Maintenance:"
	@echo "  test              Run the test suite (pytest)"
	@echo "  check             Lint, compile all scripts and check the requirements"
	@echo "  lint              Run flake8"
	@echo "  format            Format the code with black"
	@echo "  clean             Delete caches, checkpoints and the built docs (never committed files)"
	@echo "  status            Show the Python version and whether a GitHub token is configured"
	@echo "  docs-install      Install the documentation dependencies"
	@echo "  docs              Build the documentation (warnings are errors)"
	@echo "  docs-linkcheck    Check the links in the documentation"
	@echo "  docs-clean        Remove the built documentation"
	@echo ""
	@echo "Examples:"
	@echo "  make year YEAR=2026"
	@echo "  make run-stats YEAR=2024"
	@echo "  make five-year-summary SUMMARY_END=2025"

# Setup

install:
	pip install -r requirements.txt

setup: install
	@if [ ! -f .env ]; then \
		echo "Creating .env file template..."; \
		echo "GITHUB_TOKEN=your_token_here" > .env; \
		echo "Please edit .env and add your GitHub token"; \
	else \
		echo ".env file already exists"; \
	fi

dev-setup: setup
	pip install black flake8 mypy pytest pytest-timeout

# A whole year, in pipeline order: collect, derive, report

year:
	$(MAKE) run-stats YEAR=$(YEAR)
	$(MAKE) pr-interactions YEAR=$(YEAR)
	$(MAKE) run-volto-stats YEAR=$(YEAR)
	$(MAKE) run-plips
	$(MAKE) run-organisation-stats-year YEAR=$(YEAR)
	$(MAKE) run-plip-organisations
	$(MAKE) three-year-summary five-year-summary ten-year-summary SUMMARY_END=$(YEAR)
	$(MAKE) yearly-graphs
	$(MAKE) generate-report
	$(MAKE) generate-volto-report
	$(MAKE) community-recognition RECOGNITION_YEAR=$(YEAR)

# Collect

run-stats:
	python -m scripts.collect.plone_contributors --year $(YEAR)

# One file per year, in one run
run-stats-all-years:
	python -m scripts.collect.plone_contributors --from-year 2003 --to-year $$(date +%Y)

run-stats-custom:
	@echo "Usage examples:"
	@echo "  python -m scripts.collect.plone_contributors --year 2023"
	@echo "  python -m scripts.collect.plone_contributors --start-date 2024-01-01 --end-date 2024-12-31"
	@echo "  python -m scripts.collect.plone_contributors --start-date 2023-01-01 --end-date 2024-12-31"

pr-interactions:
	python -m scripts.collect.plone_pr_interactions --year $(YEAR)

pr-interactions-all-years:
	python -m scripts.collect.plone_pr_interactions --from-year 2010 --to-year $$(date +%Y)

run-volto-stats:
	python -m scripts.collect.volto_stats --year $(YEAR)

run-plips:
	python -m scripts.collect.plone_plips

# Derive

run-organisation-stats:
	@echo "Running organisation statistics for all available years..."
	@for year_file in data/*-plone-contributors.csv; do \
		if [ -f "$$year_file" ]; then \
			year=$$(basename $$year_file | sed 's/-plone-contributors.csv//'); \
			echo "Processing $$year..."; \
			python -m scripts.derive.organisation_stats --year $$year; \
		fi \
	done
	@echo "Finished generating organisation statistics for all years"

run-organisation-stats-year:
	python -m scripts.derive.organisation_stats --year $(YEAR)

run-plip-organisations:
	python -m scripts.derive.plip_organisation_stats

three-year-summary:
	python -m scripts.derive.multi_year_summary --years $(call summary_years,3)

five-year-summary:
	python -m scripts.derive.multi_year_summary --years $(call summary_years,5)

ten-year-summary:
	python -m scripts.derive.multi_year_summary --years $(call summary_years,10)

yearly-activity:
	python -m scripts.derive.yearly_activity_analysis

# Report

yearly-graphs: yearly-activity
	python -m scripts.report.generate_yearly_graphs

generate-report:
	python -m scripts.report.generate_contributor_report

generate-volto-report:
	python -m scripts.report.generate_volto_team_report

community-recognition:
	python -m scripts.report.generate_community_recognition_report --year $(RECOGNITION_YEAR)

# Tools

analyze-independent:
	python -m scripts.tools.analyze_independent_contributors

# Maintenance

clean:
	rm -f data/*_checkpoint.csv
	rm -rf .pytest_cache docs/_build
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

lint:
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 scripts tests; \
	else \
		echo "flake8 not installed. Run 'make dev-setup' first."; \
	fi

format:
	@if command -v black >/dev/null 2>&1; then \
		black scripts tests; \
	else \
		echo "black not installed. Run 'make dev-setup' first."; \
	fi

check: lint
	@echo "Checking Python syntax..."
	@python -m compileall -q scripts tests
	@echo "All Python files compile successfully!"
	@echo "Checking requirements..."
	@pip check

test:
	python -m pytest tests

status:
	@echo "Python version: $$(python --version)"
	@echo ""
	@echo "Environment:"
	@if [ -f .env ]; then \
		echo ".env file exists"; \
		if grep -q "your_token_here" .env; then \
			echo "⚠️  Please configure your GitHub token in .env"; \
		else \
			echo "✅ GitHub token configured"; \
		fi \
	else \
		echo "❌ .env file missing - run 'make setup'"; \
	fi

# Documentation

docs-install:
	pip install -r requirements-docs.txt

docs:
	python -m sphinx -W --keep-going -n -b html docs docs/_build/html

docs-linkcheck:
	python -m sphinx -b linkcheck docs docs/_build/linkcheck

docs-clean:
	rm -rf docs/_build
