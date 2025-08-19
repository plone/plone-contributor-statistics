.PHONY: help install clean run-stats run-stats-2025 run-stats-2024 run-stats-2023 run-stats-2022 run-stats-2021 run-stats-2020 run-stats-2019 run-stats-2018 run-stats-2017 run-stats-2016 run-stats-2015 run-stats-custom run-contributors run-organisations run-organisation-stats run-organisation-stats-2025 run-organisation-stats-2024 run-organisation-stats-2023 run-organisation-stats-2022 run-organisation-stats-2021 run-organisation-stats-2020 run-organisation-stats-2019 run-organisation-stats-2018 run-organisation-stats-2017 run-organisation-stats-2016 run-organisation-stats-2015 run-plips run-plip-organisations analyze-independent setup dev-setup lint format check test

# Default target
help:
	@echo "Plone GitHub Statistics Project"
	@echo ""
	@echo "Available commands:"
	@echo "  help              Show this help message"
	@echo "  install           Install Python dependencies"
	@echo "  setup             Setup environment (.env file and dependencies)"
	@echo "  run-stats         Run main statistics extraction (current year)"
	@echo "  run-stats-2025    Run statistics for 2025"
	@echo "  run-stats-2024    Run statistics for 2024"
	@echo "  run-stats-2023    Run statistics for 2023"
	@echo "  run-stats-2022    Run statistics for 2022"
	@echo "  run-stats-2021    Run statistics for 2021"
	@echo "  run-stats-2020    Run statistics for 2020"
	@echo "  run-stats-2019    Run statistics for 2019"
	@echo "  run-stats-2018    Run statistics for 2018"
	@echo "  run-stats-2017    Run statistics for 2017"
	@echo "  run-stats-2016    Run statistics for 2016"
	@echo "  run-stats-2015    Run statistics for 2015"
	@echo "  run-stats-custom  Run statistics with custom date range (see help)"
	@echo "  run-contributors  Run contributor statistics analysis"
	@echo "  run-organisations Run organisation statistics analysis"
	@echo "  run-organisation-stats Generate organisation statistics from individual stats (current year)"
	@echo "  run-organisation-stats-2025 Generate organisation statistics for 2025"
	@echo "  run-organisation-stats-2024 Generate organisation statistics for 2024"
	@echo "  run-organisation-stats-2023 Generate organisation statistics for 2023"
	@echo "  run-organisation-stats-2022 Generate organisation statistics for 2022"
	@echo "  run-organisation-stats-2021 Generate organisation statistics for 2021"
	@echo "  run-organisation-stats-2020 Generate organisation statistics for 2020"
	@echo "  run-organisation-stats-2019 Generate organisation statistics for 2019"
	@echo "  run-organisation-stats-2018 Generate organisation statistics for 2018"
	@echo "  run-organisation-stats-2017 Generate organisation statistics for 2017"
	@echo "  run-organisation-stats-2016 Generate organisation statistics for 2016"
	@echo "  run-organisation-stats-2015 Generate organisation statistics for 2015"
	@echo "  run-plips         Extract PLIP statistics from all repositories"
	@echo "  run-plip-organisations Generate PLIP organisation statistics using organisation mapping"
	@echo "  analyze-independent Analyze Independent contributors for potential organisation mappings"
	@echo "  clean             Clean up generated files"
	@echo "  lint              Run code linting"
	@echo "  format            Format Python code"
	@echo "  check             Check code quality and dependencies"
	@echo ""
	@echo "Date range examples:"
	@echo "  python plone_stats.py --year 2024"
	@echo "  python plone_stats.py --start-date 2024-01-01 --end-date 2024-06-30"

# Install dependencies
install:
	pip install -r requirements.txt

# Setup development environment
setup: install
	@if [ ! -f .env ]; then \
		echo "Creating .env file template..."; \
		echo "GITHUB_TOKEN=your_token_here" > .env; \
		echo "Please edit .env and add your GitHub token"; \
	else \
		echo ".env file already exists"; \
	fi

# Development setup with additional tools
dev-setup: setup
	pip install black flake8 mypy

# Run main statistics extraction (current year)
run-stats:
	python plone_stats.py

# Run statistics for specific years
run-stats-2025:
	python plone_stats.py --year 2025

run-stats-2024:
	python plone_stats.py --year 2024

run-stats-2023:
	python plone_stats.py --year 2023

run-stats-2022:
	python plone_stats.py --year 2022

run-stats-2021:
	python plone_stats.py --year 2021

run-stats-2020:
	python plone_stats.py --year 2020

run-stats-2019:
	python plone_stats.py --year 2019

run-stats-2018:
	python plone_stats.py --year 2018

run-stats-2017:
	python plone_stats.py --year 2017

run-stats-2016:
	python plone_stats.py --year 2016

run-stats-2015:
	python plone_stats.py --year 2015

# Run statistics with custom date range
run-stats-custom:
	@echo "Usage examples:"
	@echo "  python plone_stats.py --year 2023"
	@echo "  python plone_stats.py --start-date 2024-01-01 --end-date 2024-12-31"
	@echo "  python plone_stats.py --start-date 2023-01-01 --end-date 2024-12-31"

# Run contributor statistics
run-contributors:
	python plone_contributor_statistics.py

# Run organisation statistics
run-organisations:
	python plone_companies.py

# Generate organisation statistics from individual contributor stats
run-organisation-stats:
	python organisation_stats.py

# Generate organisation statistics for specific years
run-organisation-stats-2025:
	python organisation_stats.py --year 2025

run-organisation-stats-2024:
	python organisation_stats.py --year 2024

run-organisation-stats-2023:
	python organisation_stats.py --year 2023

run-organisation-stats-2022:
	python organisation_stats.py --year 2022

run-organisation-stats-2021:
	python organisation_stats.py --year 2021

run-organisation-stats-2020:
	python organisation_stats.py --year 2020

run-organisation-stats-2019:
	python organisation_stats.py --year 2019

run-organisation-stats-2018:
	python organisation_stats.py --year 2018

run-organisation-stats-2017:
	python organisation_stats.py --year 2017

run-organisation-stats-2016:
	python organisation_stats.py --year 2016

run-organisation-stats-2015:
	python organisation_stats.py --year 2015

# Extract PLIP statistics
run-plips:
	python plone_plips.py

# Generate PLIP organisation statistics
run-plip-organisations:
	python plip_organisation_stats.py

# Analyze Independent contributors for potential organisation mappings
analyze-independent:
	python analyze_independent_contributors.py

# Clean generated files
clean:
	rm -f *-plone-contributors*.csv
	rm -f plone-contributors*.csv
	rm -f *-plone-organisation-contributors*.csv
	rm -f plone-organisation-contributors*.csv
	rm -f plone-plips.csv
	rm -f plone-plips-detailed.csv
	rm -f plone-plip-organisations.csv
	rm -f plone_contributors*.csv
	rm -f plone_contributor_stats*.csv
	rm -f plone_companies*.csv
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Code quality checks
lint:
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 *.py; \
	else \
		echo "flake8 not installed. Run 'make dev-setup' first."; \
	fi

format:
	@if command -v black >/dev/null 2>&1; then \
		black *.py; \
	else \
		echo "black not installed. Run 'make dev-setup' first."; \
	fi

check: lint
	@echo "Checking Python syntax..."
	@python -m py_compile *.py
	@echo "All Python files compile successfully!"
	@echo "Checking requirements..."
	@pip check

# Run all scripts
run-all: run-stats run-contributors run-companies

# Show current status
status:
	@echo "Project: Plone GitHub Statistics"
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo ""
	@echo "Generated files:"
	@ls -la *.csv *.json 2>/dev/null || echo "No output files found"
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