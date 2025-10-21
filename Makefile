.PHONY: help install clean run-stats run-stats-2025 run-stats-2024 run-stats-2023 run-stats-2022 run-stats-2021 run-stats-2020 run-stats-2019 run-stats-2018 run-stats-2017 run-stats-2016 run-stats-2015 run-stats-2014 run-stats-2013 run-stats-2012 run-stats-2011 run-stats-2010 run-stats-2009 run-stats-2008 run-stats-2007 run-stats-2006 run-stats-2005 run-stats-2004 run-stats-2003 run-stats-2002 run-stats-2001 run-stats-2000 run-stats-custom run-contributors run-organisations run-organisation-stats run-organisation-stats-2025 run-organisation-stats-2024 run-organisation-stats-2023 run-organisation-stats-2022 run-organisation-stats-2021 run-organisation-stats-2020 run-organisation-stats-2019 run-organisation-stats-2018 run-organisation-stats-2017 run-organisation-stats-2016 run-organisation-stats-2015 run-organisation-stats-2014 run-organisation-stats-2013 run-organisation-stats-2012 run-organisation-stats-2011 run-organisation-stats-2010 run-organisation-stats-2009 run-organisation-stats-2008 run-organisation-stats-2007 run-organisation-stats-2006 run-organisation-stats-2005 run-organisation-stats-2004 run-organisation-stats-2003 run-organisation-stats-2002 run-organisation-stats-2001 run-organisation-stats-2000 run-plips run-plip-organisations analyze-independent three-year-summary ten-year-summary flourish-graph-organisation-contributors-csv-file flourish-graph-individual-contributors-csv-file generate-report pr-interactions pr-interactions-2025 pr-interactions-2024 pr-interactions-2023 pr-interactions-2022 pr-interactions-2021 pr-interactions-2020 pr-interactions-2019 pr-interactions-2018 pr-interactions-2017 pr-interactions-2016 pr-interactions-2015 pr-interactions-2014 pr-interactions-2013 pr-interactions-2012 pr-interactions-2011 pr-interactions-2010 pr-interactions-2009 pr-interactions-2008 pr-interactions-2007 pr-interactions-2006 pr-interactions-2005 setup dev-setup lint format check test

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
	@echo "  run-stats-2014    Run statistics for 2014"
	@echo "  run-stats-2013    Run statistics for 2013"
	@echo "  run-stats-2012    Run statistics for 2012"
	@echo "  run-stats-2011    Run statistics for 2011"
	@echo "  run-stats-2010    Run statistics for 2010"
	@echo "  run-stats-2009    Run statistics for 2009"
	@echo "  run-stats-2008    Run statistics for 2008"
	@echo "  run-stats-2007    Run statistics for 2007"
	@echo "  run-stats-2006    Run statistics for 2006"
	@echo "  run-stats-2005    Run statistics for 2005"
	@echo "  run-stats-2004    Run statistics for 2004"
	@echo "  run-stats-2003    Run statistics for 2003"
	@echo "  run-stats-2002    Run statistics for 2002"
	@echo "  run-stats-2001    Run statistics for 2001"
	@echo "  run-stats-2000    Run statistics for 2000"
	@echo "  run-stats-custom  Run statistics with custom date range (see help)"
	@echo "  run-contributors  Run contributor statistics analysis"
	@echo "  run-organisations Run organisation statistics analysis"
	@echo "  run-organisation-stats Generate organisation statistics from individual stats (all available years)"
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
	@echo "  run-organisation-stats-2014 Generate organisation statistics for 2014"
	@echo "  run-organisation-stats-2013 Generate organisation statistics for 2013"
	@echo "  run-organisation-stats-2012 Generate organisation statistics for 2012"
	@echo "  run-organisation-stats-2011 Generate organisation statistics for 2011"
	@echo "  run-organisation-stats-2010 Generate organisation statistics for 2010"
	@echo "  run-organisation-stats-2009 Generate organisation statistics for 2009"
	@echo "  run-organisation-stats-2008 Generate organisation statistics for 2008"
	@echo "  run-organisation-stats-2007 Generate organisation statistics for 2007"
	@echo "  run-organisation-stats-2006 Generate organisation statistics for 2006"
	@echo "  run-organisation-stats-2005 Generate organisation statistics for 2005"
	@echo "  run-organisation-stats-2004 Generate organisation statistics for 2004"
	@echo "  run-organisation-stats-2003 Generate organisation statistics for 2003"
	@echo "  run-organisation-stats-2002 Generate organisation statistics for 2002"
	@echo "  run-organisation-stats-2001 Generate organisation statistics for 2001"
	@echo "  run-organisation-stats-2000 Generate organisation statistics for 2000"
	@echo "  run-plips         Extract PLIP statistics from all repositories"
	@echo "  run-plip-organisations Generate PLIP organisation statistics using organisation mapping"
	@echo "  analyze-independent Analyze Independent contributors for potential organisation mappings"
	@echo "  three-year-summary Generate combined statistics summary for 2022-2024"
	@echo "  five-year-summary Generate combined statistics summary for 2020-2024"
	@echo "  ten-year-summary  Generate combined statistics summary for 2015-2024"
	@echo "  yearly-activity   Generate yearly development activity analysis"
	@echo "  yearly-graphs     Generate visual graphs from yearly activity data"
	@echo "  npm-packages      Analyze NPM packages published by Plone organizations"
	@echo "  pypi-packages     Analyze PyPI packages published by Plone organizations"
	@echo "  flourish-graph-organisation-contributors-csv-file Generate organization CSV for Flourish visualization"
	@echo "  flourish-graph-individual-contributors-csv-file Generate individual contributors CSV for Flourish visualization"
	@echo "  generate-report   Generate comprehensive contributor and organization report"
	@echo "  pr-interactions   Extract pull request comments and interactions from GitHub"
	@echo "  pr-interactions-2025 Extract pull request comments and interactions for 2025"
	@echo "  pr-interactions-2024 Extract pull request comments and interactions for 2024"
	@echo "  pr-interactions-2023 Extract pull request comments and interactions for 2023"
	@echo "  pr-interactions-2022 Extract pull request comments and interactions for 2022"
	@echo "  pr-interactions-2021 Extract pull request comments and interactions for 2021"
	@echo "  pr-interactions-2020 Extract pull request comments and interactions for 2020"
	@echo "  pr-interactions-2019 Extract pull request comments and interactions for 2019"
	@echo "  pr-interactions-2018 Extract pull request comments and interactions for 2018"
	@echo "  pr-interactions-2017 Extract pull request comments and interactions for 2017"
	@echo "  pr-interactions-2016 Extract pull request comments and interactions for 2016"
	@echo "  pr-interactions-2015 Extract pull request comments and interactions for 2015"
	@echo "  pr-interactions-2014 Extract pull request comments and interactions for 2014"
	@echo "  pr-interactions-2013 Extract pull request comments and interactions for 2013"
	@echo "  pr-interactions-2012 Extract pull request comments and interactions for 2012"
	@echo "  pr-interactions-2011 Extract pull request comments and interactions for 2011"
	@echo "  pr-interactions-2010 Extract pull request comments and interactions for 2010"
	@echo "  pr-interactions-2009 Extract pull request comments and interactions for 2009"
	@echo "  pr-interactions-2008 Extract pull request comments and interactions for 2008"
	@echo "  pr-interactions-2007 Extract pull request comments and interactions for 2007"
	@echo "  pr-interactions-2006 Extract pull request comments and interactions for 2006"
	@echo "  pr-interactions-2005 Extract pull request comments and interactions for 2005"
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

run-stats-2014:
	python plone_stats.py --year 2014

run-stats-2013:
	python plone_stats.py --year 2013

run-stats-2012:
	python plone_stats.py --year 2012

run-stats-2011:
	python plone_stats.py --year 2011

run-stats-2010:
	python plone_stats.py --year 2010

run-stats-2009:
	python plone_stats.py --year 2009

run-stats-2008:
	python plone_stats.py --year 2008

run-stats-2007:
	python plone_stats.py --year 2007

run-stats-2006:
	python plone_stats.py --year 2006

run-stats-2005:
	python plone_stats.py --year 2005

run-stats-2004:
	python plone_stats.py --year 2004

run-stats-2003:
	python plone_stats.py --year 2003

run-stats-2002:
	python plone_stats.py --year 2002

run-stats-2001:
	python plone_stats.py --year 2001

run-stats-2000:
	python plone_stats.py --year 2000

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

# Generate organisation statistics from individual contributor stats (all available years)
run-organisation-stats:
	@echo "Running organisation statistics for all available years..."
	@for year_file in *-plone-contributors.csv; do \
		if [ -f "$$year_file" ]; then \
			year=$$(echo $$year_file | sed 's/-plone-contributors.csv//'); \
			echo "Processing $$year..."; \
			python organisation_stats.py --year $$year; \
		fi \
	done
	@echo "Finished generating organisation statistics for all years"

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

run-organisation-stats-2014:
	python organisation_stats.py --year 2014

run-organisation-stats-2013:
	python organisation_stats.py --year 2013

run-organisation-stats-2012:
	python organisation_stats.py --year 2012

run-organisation-stats-2011:
	python organisation_stats.py --year 2011

run-organisation-stats-2010:
	python organisation_stats.py --year 2010

run-organisation-stats-2009:
	python organisation_stats.py --year 2009

run-organisation-stats-2008:
	python organisation_stats.py --year 2008

run-organisation-stats-2007:
	python organisation_stats.py --year 2007

run-organisation-stats-2006:
	python organisation_stats.py --year 2006

run-organisation-stats-2005:
	python organisation_stats.py --year 2005

run-organisation-stats-2004:
	python organisation_stats.py --year 2004

run-organisation-stats-2003:
	python organisation_stats.py --year 2003

run-organisation-stats-2002:
	python organisation_stats.py --year 2002

run-organisation-stats-2001:
	python organisation_stats.py --year 2001

run-organisation-stats-2000:
	python organisation_stats.py --year 2000

# Extract PLIP statistics
run-plips:
	python plone_plips.py

# Generate PLIP organisation statistics
run-plip-organisations:
	python plip_organisation_stats.py

# Analyze Independent contributors for potential organisation mappings
analyze-independent:
	python analyze_independent_contributors.py

# Generate three-year summary combining 2022-2024 organisation statistics
three-year-summary:
	python multi_year_summary.py

# Generate five-year summary combining 2020-2024 organisation statistics
five-year-summary:
	python multi_year_summary.py --years 2020 2021 2022 2023 2024

# Generate ten-year summary combining 2015-2024 organisation statistics
ten-year-summary:
	python multi_year_summary.py --years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024

# Generate yearly development activity analysis
yearly-activity:
	python yearly_activity_analysis.py

# Generate visual graphs from yearly activity data
yearly-graphs:
	python generate_yearly_graphs.py

# Analyze NPM packages published by Plone organizations
npm-packages:
	python npm_package_stats.py

# Analyze PyPI packages published by Plone organizations
pypi-packages:
	python pypi_package_stats.py

# Generate organization CSV for Flourish visualization
flourish-graph-organisation-contributors-csv-file:
	python create_organization_flourish_csv.py

# Generate individual contributors CSV for Flourish visualization
flourish-graph-individual-contributors-csv-file:
	python create_individual_contributors_flourish_csv.py

# Generate comprehensive contributor and organization report
generate-report:
	python generate_contributor_report.py

# Extract pull request comments and interactions from GitHub
pr-interactions:
	python plone_pr_interactions.py

# Extract pull request comments and interactions for 2025
pr-interactions-2025:
	python plone_pr_interactions.py --year 2025

# Extract pull request comments and interactions for 2024
pr-interactions-2024:
	python plone_pr_interactions.py --year 2024

# Extract pull request comments and interactions for 2023
pr-interactions-2023:
	python plone_pr_interactions.py --year 2023

# Extract pull request comments and interactions for 2022
pr-interactions-2022:
	python plone_pr_interactions.py --year 2022

# Extract pull request comments and interactions for 2021
pr-interactions-2021:
	python plone_pr_interactions.py --year 2021

# Extract pull request comments and interactions for 2020
pr-interactions-2020:
	python plone_pr_interactions.py --year 2020

# Extract pull request comments and interactions for 2019
pr-interactions-2019:
	python plone_pr_interactions.py --year 2019

# Extract pull request comments and interactions for 2018
pr-interactions-2018:
	python plone_pr_interactions.py --year 2018

# Extract pull request comments and interactions for 2017
pr-interactions-2017:
	python plone_pr_interactions.py --year 2017

# Extract pull request comments and interactions for 2016
pr-interactions-2016:
	python plone_pr_interactions.py --year 2016

# Extract pull request comments and interactions for 2015
pr-interactions-2015:
	python plone_pr_interactions.py --year 2015

# Extract pull request comments and interactions for 2014
pr-interactions-2014:
	python plone_pr_interactions.py --year 2014

# Extract pull request comments and interactions for 2013
pr-interactions-2013:
	python plone_pr_interactions.py --year 2013

# Extract pull request comments and interactions for 2012
pr-interactions-2012:
	python plone_pr_interactions.py --year 2012

# Extract pull request comments and interactions for 2011
pr-interactions-2011:
	python plone_pr_interactions.py --year 2011

# Extract pull request comments and interactions for 2010
pr-interactions-2010:
	python plone_pr_interactions.py --year 2010

# Extract pull request comments and interactions for 2009
pr-interactions-2009:
	python plone_pr_interactions.py --year 2009

# Extract pull request comments and interactions for 2008
pr-interactions-2008:
	python plone_pr_interactions.py --year 2008

# Extract pull request comments and interactions for 2007
pr-interactions-2007:
	python plone_pr_interactions.py --year 2007

# Extract pull request comments and interactions for 2006
pr-interactions-2006:
	python plone_pr_interactions.py --year 2006

# Extract pull request comments and interactions for 2005
pr-interactions-2005:
	python plone_pr_interactions.py --year 2005

# Clean generated files
clean:
	rm -f *-plone-contributors*.csv
	rm -f plone-contributors*.csv
	rm -f *-plone-organisation-contributors*.csv
	rm -f plone-organisation-contributors*.csv
	rm -f plone-plips.csv
	rm -f plone-plips-detailed.csv
	rm -f plone-plip-organisations.csv
	rm -f summary-past-*-years-*.csv
	rm -f STATISTICS-PAST-*-YEARS.txt
	rm -f yearly-activity-statistics.csv
	rm -f YEARLY-ACTIVITY-ANALYSIS.md
	rm -rf graphs/
	rm -f npm-packages-*.md
	rm -f npm-packages-*.csv
	rm -f pypi-packages-*.md
	rm -f pypi-packages-*.csv
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