.PHONY: help install clean run-stats run-contributors run-companies run-company-stats setup dev-setup lint format check test

# Default target
help:
	@echo "Plone GitHub Statistics Project"
	@echo ""
	@echo "Available commands:"
	@echo "  help              Show this help message"
	@echo "  install           Install Python dependencies"
	@echo "  setup             Setup environment (.env file and dependencies)"
	@echo "  run-stats         Run main statistics extraction"
	@echo "  run-contributors  Run contributor statistics analysis"
	@echo "  run-companies     Run company statistics analysis"
	@echo "  run-company-stats Generate company statistics from individual stats"
	@echo "  clean             Clean up generated files"
	@echo "  lint              Run code linting"
	@echo "  format            Format Python code"
	@echo "  check             Check code quality and dependencies"

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

# Run main statistics extraction
run-stats:
	python plone_stats.py

# Run contributor statistics
run-contributors:
	python plone_contributor_statistics.py

# Run company statistics
run-companies:
	python plone_companies.py

# Generate company statistics from individual contributor stats
run-company-stats:
	python company_stats.py

# Clean generated files
clean:
	rm -f plone_stats_*.csv
	rm -f plone_stats_*.json
	rm -f plone_contributor_stats_*.csv
	rm -f plone_contributor_stats_*.json
	rm -f plone_companies_*.csv
	rm -f plone_companies_*.json
	rm -f company_stats_*.csv
	rm -f company_stats_*.json
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