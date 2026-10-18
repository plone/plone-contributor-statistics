"""Where the files of the pipeline live, relative to the repository root.

Scripts run from the repository root (make does this), so every path here is
relative. Change a location here, not in the scripts.
"""

from pathlib import Path

# Curated input: edited by hand, every entry needs a public record
MAPPINGS_DIR = Path('curated/mappings')
ORGANISATIONS = MAPPINGS_DIR / 'organisations.csv'
OVERRIDES = MAPPINGS_DIR / 'organisation_mapping_overrides.csv'
SOURCES = MAPPINGS_DIR / 'organisation_mapping_sources.csv'
PROPOSALS = MAPPINGS_DIR / 'organisation_mapping_proposals.csv'
BOT_ACCOUNTS = MAPPINGS_DIR / 'bot_accounts.csv'
EXCLUDED_REPOSITORIES = MAPPINGS_DIR / 'excluded_repositories.csv'
COMMIT_AUTHORS = MAPPINGS_DIR / 'commit_authors.csv'
ACCOUNT_ALIASES = MAPPINGS_DIR / 'account_aliases.csv'
FULLNAMES = MAPPINGS_DIR / 'mapping-github-username-to-fullname.csv'
COMMUNITY = Path('curated/community-contributions')
RECOGNITION_LEVELS = COMMUNITY / 'community-recognition-levels.csv'

# Collected by the collectors; never edit by hand
CONTRIBUTORS_DIR = Path('collected/contributors')
PR_INTERACTIONS_DIR = Path('collected/pr-interactions')
VOLTO_DIR = Path('collected/volto')
PLIPS = Path('collected/plips/plone-plips.csv')
PLIPS_DETAILED = Path('collected/plips/plone-plips-detailed.csv')

# Derived from the above; never edit by hand
ORGANISATION_CONTRIBUTORS_DIR = Path('derived/organisation-contributors')
SUMMARIES_DIR = Path('derived/summaries')
YEARLY_ACTIVITY = Path('derived/yearly-activity-statistics.csv')
PLIP_ORGANISATIONS = Path('derived/plone-plip-organisations.csv')
RECOGNITION_REPORT_DIR = Path('derived/community-recognition')

# Reports; never edit by hand
REPORTS_DIR = Path('reports')
PR_INTERACTION_REPORTS_DIR = Path('reports/pr-interactions')
CONTRIBUTOR_REPORT = Path('reports/github-contributor-report.md')
VOLTO_REPORT = Path('reports/volto.md')
RECOGNITION_REPORT = Path('reports/community-recognition.md')
SUMMARY_REPORTS_DIR = Path('reports/summaries')
GRAPHS_DIR = Path('reports/graphs')


def contributors_file(label):
    """The collected contributors of a year (or a range such as 2023-2024)."""
    return CONTRIBUTORS_DIR / f'{label}-plone-contributors.csv'


def checkpoint_file(label):
    """The checkpoint the contributors collector writes while it runs; label is the output file name."""
    return CONTRIBUTORS_DIR / f'{label}_checkpoint.csv'


def pr_interactions_file(label):
    return PR_INTERACTIONS_DIR / f'{label}-plone-pr-interactions.csv'


def pr_interactions_report(year):
    return PR_INTERACTION_REPORTS_DIR / f'github-pr-interactions-report-{year}.md'


def volto_file(label):
    return VOLTO_DIR / f'{label}-volto-stats.csv'


def organisation_contributors_file(label):
    return ORGANISATION_CONTRIBUTORS_DIR / f'{label}-plone-organisation-contributors.csv'


def recognition_report_file(year):
    return RECOGNITION_REPORT_DIR / f'{year}-community-recognition-report.csv'
