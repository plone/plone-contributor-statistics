.PHONY: help install clean run-stats run-stats-2024 run-stats-2023 run-stats-2022 run-stats-2021 run-stats-2020 run-stats-custom run-contributors run-companies run-company-stats run-company-stats-2024 run-company-stats-2023 run-company-stats-2022 run-company-stats-2021 run-plips run-plip-companies setup dev-setup lint format check test

# Default target
help:
	@echo "Plone GitHub Statistics Project"
	@echo ""
	@echo "Available commands:"
	@echo "  help              Show this help message"
	@echo "  install           Install Python dependencies"
	@echo "  setup             Setup environment (.env file and dependencies)"
	@echo "  run-stats         Run main statistics extraction (current year)"
	@echo "  run-stats-2024    Run statistics for 2024"
	@echo "  run-stats-2023    Run statistics for 2023"
	@echo "  run-stats-2022    Run statistics for 2022"
	@echo "  run-stats-2021    Run statistics for 2021"
	@echo "  run-stats-2020    Run statistics for 2020"
	@echo "  run-stats-custom  Run statistics with custom date range (see help)"
	@echo "  run-contributors  Run contributor statistics analysis"
	@echo "  run-companies     Run company statistics analysis"
	@echo "  run-company-stats Generate company statistics from individual stats (current year)"
	@echo "  run-company-stats-2024 Generate company statistics for 2024"
	@echo "  run-company-stats-2023 Generate company statistics for 2023"
	@echo "  run-company-stats-2022 Generate company statistics for 2022"
	@echo "  run-company-stats-2021 Generate company statistics for 2021"
	@echo "  run-plips         Extract PLIP statistics from all repositories"
	@echo "  run-plip-companies Generate PLIP company statistics using company mapping"
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

# Run statistics for 2024
run-stats-2024:
	python plone_stats.py --year 2024

# Run statistics for 2023
run-stats-2023:
	python plone_stats.py --year 2023

# Run statistics for 2022
run-stats-2022:
	python plone_stats.py --year 2022

# Run statistics for 2021
run-stats-2021:
	python plone_stats.py --year 2021

# Run statistics for 2020
run-stats-2020:
	python plone_stats.py --year 2020

# Run statistics with custom date range
run-stats-custom:
	@echo "Usage examples:"
	@echo "  python plone_stats.py --year 2023"
	@echo "  python plone_stats.py --start-date 2024-01-01 --end-date 2024-12-31"
	@echo "  python plone_stats.py --start-date 2023-01-01 --end-date 2024-12-31"

# Run contributor statistics
run-contributors:
	python plone_contributor_statistics.py

# Run company statistics
run-companies:
	python plone_companies.py

# Generate company statistics from individual contributor stats
run-company-stats:
	python company_stats.py

# Generate company statistics for specific years
run-company-stats-2024:
	python company_stats.py --year 2024

run-company-stats-2023:
	python company_stats.py --year 2023

run-company-stats-2022:
	python company_stats.py --year 2022

run-company-stats-2021:
	python company_stats.py --year 2021

# Extract PLIP statistics
run-plips:
	python plone_plips.py

# Generate PLIP company statistics
run-plip-companies:
	python plip_company_stats.py

# Clean generated files
clean:
	rm -f *-plone-contributors*.csv
	rm -f plone-contributors*.csv
	rm -f *-plone-company-contributors*.csv
	rm -f plone-company-contributors*.csv
	rm -f plone-plips.csv
	rm -f plone-plips-detailed.csv
	rm -f plone-plip-companies.csv
	rm -f plone_contributors*.csv
	rm -f plone_contributor_stats*.csv
	rm -f plone_companies*.csv
	rm -f plone_company_contributors*.csv
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