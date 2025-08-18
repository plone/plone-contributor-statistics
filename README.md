# Plone GitHub Statistics Extractor

Python script to extract comprehensive GitHub statistics from the Plone organization, including commits, pull requests, and contributor activity across all repositories.

## Features

- **Complete Repository Coverage**: Processes all repositories in the Plone organization
- **Date Range Filtering**: Defaults to current year, customizable date ranges
- **Comprehensive Contributor Data**: Tracks commits, pull requests, and repository contributions per person  
- **GitHub API Integration**: Handles authentication, rate limiting, and pagination
- **Multiple Export Formats**: Saves data to both CSV and JSON formats
- **Real-time Progress**: Shows processing status and repository counts

## Setup

1. Install required dependencies:
```bash
pip install requests pandas python-dotenv
```

2. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Create a new token with `public_repo` and `read:org` scopes
   - Copy the token

3. Create `.env` file:
```bash
echo "GITHUB_TOKEN=your_token_here" > .env
```

## Usage

### Basic Usage (Current Year)
```bash
python plone_stats.py
```

This will:
- Process **all** repositories in the Plone organization
- Filter data to the current year (2025)
- Display total repository count
- Save results with timestamp

### Custom Date Range
```python
from datetime import datetime
from plone_stats import PloneStatsExtractor

# Custom date range example
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
extractor = PloneStatsExtractor(start_date=start_date, end_date=end_date)
extractor.extract_all_stats()
```

## Output Files

- `plone_stats_YYYYMMDD_HHMMSS.csv` - Contributor statistics in tabular format
- `plone_stats_YYYYMMDD_HHMMSS.json` - Raw data with detailed contributor information

## Data Collected

For each contributor, the script tracks:
- **Total commits** across all repositories within the date range
- **Total pull requests** created within the date range  
- **Repository count** - number of repositories contributed to
- **Repository list** - names of all repositories with contributions
- **First contribution** - earliest activity date in the time period
- **Last contribution** - most recent activity date in the time period

## Script Features

- **No Limits**: Processes all repositories and all contributors (previous 10-repo limit removed)
- **Date Filtering**: Only includes activity within the specified date range
- **Authentication**: Requires GitHub token for API access and higher rate limits
- **Progress Tracking**: Real-time status updates during processing
- **Error Handling**: Graceful handling of API rate limits and network issues
- **Resume Capability**: Can be rerun to get updated data

## GitHub API Rate Limits

- **With token**: 5,000 requests per hour
- **Without token**: 60 requests per hour (not recommended)
- The script includes built-in rate limiting and retry logic