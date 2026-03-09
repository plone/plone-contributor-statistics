# AI Agent Conventions for Plone Contributor Statistics

This document outlines conventions, tools, and workflows for AI agents working with this repository.

## Repository Purpose

This repository tracks and analyzes Plone community contributions through GitHub statistics, conference data, and contributor information.

## CSV File Conventions

### Multi-Value Cells
- **Use semicolons (`;`)** to separate multiple values within a single CSV cell
- Example: `Karel Calitz;Kim Paulissen` or `Juizi;KU Leuven`
- **Do NOT use `&`** for separating values
- Rationale: Semicolons are standard for multi-value CSV fields and easy to parse with `.split(';')`

### Quoting Values with Commas
- **Use double quotes (`"`)** around values that contain commas
- Example: `"Big Corp, Inc."` or `"Federal Senate (Interlegis Program)"`
- This ensures proper CSV parsing and prevents values from being split into multiple columns
- Apply quotes only when necessary (when the value contains a comma)

### Column Guidelines
- Remove unnecessary columns like `#` (row numbers) unless specifically needed
- Remove `Date` columns when not essential for the data analysis
- Keep column names descriptive and consistent

### Organisation Column Consistency
- **Always check `organisations.csv`** when working with any CSV file that has an `Organisation` column
- Ensure organisation names match exactly with entries in `organisations.csv`
- Common consistency rules:
  - Use `kitconcept GmbH` (not `kitconcept`)
  - Use `RedTurtle` (not `Red Turtle`)
  - Use `University of Jyväskylä` (not `Jyväskylä University`, `Uni. Jyväskylä`, or `Uni. Jyvaskylä`)
  - Use `Klein & Partner KG` (not `Klein und Partner` or `Klein & Partner`)
  - Use `CMS Communications Inc.` (not `CMS Communications`)
  - Use `Codesyntax` (not `CodeSyntax`)
  - Use `PY76` (not `Py76`)
  - Use `Simples Consultoria` (not `SimplesConsultorias`)
  - Use `UNAM` (not `Mathematics Institute UNAM` or `Mathematics Institute at UNAM`)
- When adding new organisations to CSV files, also add them to `organisations.csv`
- Before completing any task involving Organisation columns, verify consistency across all files

### File Locations
- Year-specific contributor data: Root directory (e.g., `2025-plone-contributors.csv`)
- Event/conference data: Root directory (e.g., `2025-plone-conference-trainings.csv`, `2025-world-plone-day.csv`)
- Detailed statistics and interactions: `data/` directory (e.g., `data/2025-plone-pr-interactions.csv`)

## GitHub Username to Fullname Mapping

### Primary Source: Mapping File
Always check `mapping-github-username-to-fullname.csv` first when you need to map GitHub usernames to full names.

**File format:**
```csv
github username,fullname
datakurre,Asko Soukka
pbauer,Philip Bauer
```

### Fallback: GitHub API Script
If a username is not found in the mapping file, use the `get_github_name.py` script:

```bash
# Single user
python get_github_name.py <github_handle>

# Multiple users
python get_github_name.py <handle1> <handle2> <handle3>
```

**Important:** After retrieving new mappings via the script, add them to `mapping-github-username-to-fullname.csv` for future use.

### Authentication
The `get_github_name.py` script uses GitHub token authentication from `.env` file:
- Token variable: `GITHUB_TOKEN`
- Supports both Bearer and legacy token formats
- Falls back to unauthenticated requests if token is invalid
- Authenticated: 5000 requests/hour
- Unauthenticated: 60 requests/hour

## Python Scripts and Tools

### GitHub API Scripts
- All scripts use `python-dotenv` to load `GITHUB_TOKEN` from `.env`
- Follow the pattern from `plone_contributor_statistics.py` for authentication
- Always reload environment with `load_dotenv(override=True)` to ensure fresh token

### Common Dependencies
- `requests` - HTTP requests to GitHub API
- `pandas` - CSV and data manipulation
- `python-dotenv` - Environment variable management

## Data Processing Patterns

### When Creating New CSV Files
1. Check existing CSV files for format consistency
2. Apply multi-value separator convention (`;`)
3. Remove unnecessary columns (`#`, `Date` if not needed)
4. Place file in appropriate location (root vs `data/`)
5. If the file has an `Organisation` column, verify all values against `organisations.csv` for consistency

### When Working with GitHub Data
1. Check `mapping-github-username-to-fullname.csv` first
2. Use `get_github_name.py` for missing usernames
3. Update mapping file with new entries
4. Respect API rate limits (add delays between requests)

## Repository Structure

```
.
├── data/                           # Detailed statistics and time-series data
│   ├── YYYY-plone-contributors.csv
│   ├── YYYY-plone-pr-interactions.csv
│   └── YYYY-volto-team-stats.csv
├── YYYY-plone-contributors.csv     # Year-specific contributor summaries
├── YYYY-plone-conference-*.csv     # Conference and event data
├── mapping-github-username-to-fullname.csv  # GitHub username mappings
├── get_github_name.py              # GitHub API tool for name lookup
└── *.py                            # Various analysis and statistics scripts
```

## Best Practices

1. **Prefer editing over creating** - Always prefer editing existing files rather than creating new ones unless specifically required
2. **Consistency** - Follow existing patterns in CSV structure and naming
3. **Documentation** - Update this file when establishing new conventions
4. **Data integrity** - Validate CSV format before committing
5. **API efficiency** - Use mapping file to minimize GitHub API calls
6. **Manual corrections** - The mapping file allows for manual corrections (e.g., when GitHub profile name differs from preferred name)

## Common Tasks

### Adding Conference/Event Data
1. Create CSV in root directory with format: `YYYY-event-name.csv`
2. Use `;` for multi-value cells
3. Common columns: Title, Speaker(s), GitHub Handle(s), Company / Org, Type

### Looking Up GitHub Names
```bash
# Check mapping file first
grep "username" mapping-github-username-to-fullname.csv

# If not found, use script
python get_github_name.py username

# Add to mapping file
echo "username,Full Name" >> mapping-github-username-to-fullname.csv
```

### Updating Statistics
Most Python scripts follow the pattern:
1. Load environment variables
2. Authenticate with GitHub API
3. Fetch data from GitHub
4. Process and analyze
5. Export to CSV

---

**Last Updated:** 2026-03-07
**Maintained by:** Plone community with AI agent assistance
