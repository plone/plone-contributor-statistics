# Plone Contributor Statistics Extractor

Comprehensive GitHub statistics extraction and analysis system for the Plone ecosystem, including individual contributor stats, organisation attribution, and PLIP (Plone Improvement Proposals) tracking across all Plone repositories.

## Features

- **Complete Repository Coverage**: Processes all 300+ repositories in the Plone organization
- **Multi-Year Analysis**: Historical data extraction from 2005-2025
- **Organisation Mapping**: Attribution system mapping 109+ contributors to 54+ organisations
- **PLIP Tracking**: Extract and analyze Plone Improvement Proposals across repositories
- **Cross-Year Analysis**: Identify Independent contributors for organisation mapping
- **GitHub API Integration**: Handles authentication, rate limiting, and pagination
- **Automated Workflows**: Makefile commands for all analysis tasks

## Quick Start

```bash
# Setup environment and dependencies
make setup

# Run current year statistics
make run-stats

# Generate organisation statistics (you have to run "run-stats" first)
make run-organisation-stats

# Extract PLIP statistics
make run-plips

# Show all available commands
make help
```

## Main Makefile Commands

### Individual Contributor Statistics

```bash
# Current year (2025)
make run-stats

# Specific years (2005-2025 available)
make run-stats-2024
make run-stats-2023
make run-stats-2022
# ... (all years 2005-2025)

# Custom date range
python plone_stats.py --start-date 2024-01-01 --end-date 2024-06-30
```

### Organisation Statistics

```bash
# Current year organisation stats
make run-organisation-stats

# Specific years (2005-2025 available)
make run-organisation-stats-2024
make run-organisation-stats-2023
make run-organisation-stats-2022
# ... (all years 2005-2025)
```

### PLIP (Plone Improvement Proposals) Analysis

```bash
# Extract PLIP statistics from all repositories
make run-plips

# Generate PLIP organisation statistics
make run-plip-organisations
```

### Analysis and Maintenance

```bash
# Analyze Independent contributors for organisation mapping
make analyze-independent

# Clean generated files
make clean

# Code quality checks
make lint
make format
make check
```

## Generated Files

### Individual Statistics

- `YYYY-plone-contributors.csv` - Individual contributor stats by year
- Raw data with commits, PRs, repositories, and date ranges per contributor

### Organisation Statistics

- `YYYY-plone-organisation-contributors.csv` - Organisation-aggregated stats
- Shows total activity by organisation with contributor attribution

### PLIP Statistics

- `plone-plips.csv` - PLIP counts per author (aggregated)
- `plone-plips-detailed.csv` - Individual PLIP records
- `plone-plip-organisations.csv` - PLIP statistics by organisation

### Flourish Charts

- Individual Contributors: https://public.flourish.studio/visualisation/24775871/
- Organisations: https://public.flourish.studio/visualisation/24775561/

### Configuration

- `organisation_mapping.txt` - Maps contributors to organisations
- Format: `organisation:contributor1,contributor2,contributor3`

## Key Features

### Organisation Mapping System

The system maps 109+ contributors across 54+ organisations including:

- **kitconcept**: Leading contributor with comprehensive Plone development
- **nuclia**: Significant PLIP contributions and core development
- **syslab**: Multi-year contributor across various repositories
- **Independent**: Unmapped individual contributors

### PLIP Tracking

Extracts PLIPs from three main repositories:

- **Products.CMFPlone**: Core Plone functionality (222 PLIPs)
- **volto**: Modern frontend (75 PLIPs)
- **plone.restapi**: REST API (6 PLIPs)

### Cross-Year Analysis

- Track contributor activity patterns across years
- Identify Independent contributors for potential organisation mapping
- Generate comprehensive statistics from 2005-2025

## Setup

1. **Install dependencies**:

```bash
make install
# or manually: pip install requests pandas python-dotenv
```

2. **GitHub Token Setup**:

```bash
make setup
# Edit .env file with your GitHub token
```

3. **Development Setup** (optional):

```bash
make dev-setup  # Includes linting and formatting tools
```

## Usage Examples

### Complete Analysis Workflow

```bash
# 1. Extract individual stats for 2024
make run-stats-2024

# 2. Generate organisation stats for 2024
make run-organisation-stats-2024

# 3. Analyze remaining Independent contributors
make analyze-independent

# 4. Extract PLIP statistics
make run-plips

# 5. Generate PLIP organisation statistics
make run-plip-organisations
```

### Multi-Year Organisation Analysis

```bash
# Generate organisation stats for multiple years
make run-organisation-stats-2024
make run-organisation-stats-2023
make run-organisation-stats-2022
```

## Data Analysis Results

### Top Organisations by Activity (2024 example)

- **kitconcept**: ~2,000+ commits across 100+ repositories
- **nuclia**: Major PLIP contributor with 37 proposals
- **syslab**: Consistent multi-repository contributor
- **py76**: High-volume individual contributor

### PLIP Statistics

- **Total PLIPs**: 303 (87 open, 216 closed)
- **Top PLIP Authors**: tisto (61), sneridagh (30), bloodbare (20)
- **Repository Distribution**: Products.CMFPlone (73%), volto (25%), plone.restapi (2%)

## GitHub API Considerations

- **With token**: 5,000 requests per hour
- **Without token**: 60 requests per hour (not recommended)
- Built-in rate limiting and retry logic
- Handles pagination for large datasets
