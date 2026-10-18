"""Where the files of the pipeline live, relative to the repository root.

Scripts run from the repository root (make does this), so every path here is
relative. Change a location here, not in the scripts.
"""

from pathlib import Path

# Curated input: edited by hand, every entry needs a public record
ORGANISATIONS = Path('organisations.csv')
OVERRIDES = Path('organisation_mapping_overrides.csv')
SOURCES = Path('organisation_mapping_sources.csv')
PROPOSALS = Path('organisation_mapping_proposals.csv')
BOT_ACCOUNTS = Path('bot_accounts.csv')
EXCLUDED_REPOSITORIES = Path('excluded_repositories.csv')
COMMIT_AUTHORS = Path('commit_authors.csv')
ACCOUNT_ALIASES = Path('account_aliases.csv')
FULLNAMES = Path('mapping-github-username-to-fullname.csv')
COMMUNITY = Path('data') / 'community-contributions'
RECOGNITION_LEVELS = COMMUNITY / 'community-recognition-levels.csv'

# Collected by the collectors
CONTRIBUTORS_DIR = Path('data')
PR_INTERACTIONS_DIR = Path('data')
VOLTO_DIR = Path('data')
PLIPS = Path('plone-plips.csv')
PLIPS_DETAILED = Path('plone-plips-detailed.csv')

# Derived from the above
ORGANISATION_CONTRIBUTORS_DIR = Path('data')
SUMMARIES_DIR = Path('.')
YEARLY_ACTIVITY = Path('yearly-activity-statistics.csv')
PLIP_ORGANISATIONS = Path('plone-plip-organisations.csv')
RECOGNITION_REPORT_DIR = COMMUNITY

# Reports
REPORTS_DIR = Path('reports')
PR_INTERACTION_REPORTS_DIR = Path('reports')
CONTRIBUTOR_REPORT = Path('reports/github-contributor-report.md')
VOLTO_REPORT = Path('reports/volto.md')
RECOGNITION_REPORT = Path('reports/community-recognition.md')
SUMMARY_REPORTS_DIR = Path('.')
GRAPHS_DIR = Path('graphs')


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
