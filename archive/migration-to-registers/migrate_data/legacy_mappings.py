"""The old mapping files of the migration (#139): read before the registers replaced them.

These loaders serve the migration only; the registers are read through scripts.lib.model.

Every loader raises FileNotFoundError when its file is missing: a wrong path
must stop the run instead of producing statistics without the mapping.
"""

import csv

from scripts.lib import paths
from scripts.lib.model.registers import load_bot_accounts, load_excluded_repositories  # noqa: F401

# The old files, which paths.py no longer lists
OVERRIDES = paths.MAPPINGS_DIR / 'organisation_mapping_overrides.csv'
SOURCES = paths.MAPPINGS_DIR / 'organisation_mapping_sources.csv'
PROPOSALS = paths.MAPPINGS_DIR / 'organisation_mapping_proposals.csv'
COMMIT_AUTHORS = paths.MAPPINGS_DIR / 'commit_authors.csv'
ACCOUNT_ALIASES = paths.MAPPINGS_DIR / 'account_aliases.csv'
FULLNAMES = paths.MAPPINGS_DIR / 'mapping-github-username-to-fullname.csv'
CHANGELOG_NAMES = paths.MAPPINGS_DIR / 'changelog_names.csv'
# organisations.csv has a new format; the old one is read from here
OLD_ORGANISATIONS = paths.MAPPINGS_DIR / 'organisations.csv'


def _rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_commit_authors(path=COMMIT_AUTHORS):
    """Load the people behind commit emails that GitHub does not link to an account (#69).

    Maps the email (lower case) to the GitHub login, or to the person's name
    if they have no GitHub account.
    """
    return {row['email'].strip().lower(): row['github_username'].strip() or row['name'].strip()
            for row in _rows(path)}


def load_commit_author_names(path=COMMIT_AUTHORS):
    """The names in commit_authors.csv, mapped to the GitHub login, or to the name if there is none."""
    return {row['name'].strip(): row['github_username'].strip() or row['name'].strip()
            for row in _rows(path) if row['name'].strip()}


def load_changelog_names(path=CHANGELOG_NAMES):
    """Load the people behind names in changelog entries (#71).

    Maps the name as the changelog spells it to the GitHub login, or to the
    person's name if they have no GitHub account.
    """
    return {row['changelog_name'].strip(): row['github_username'].strip() or row['name'].strip()
            for row in _rows(path)}


def load_fullnames(path=FULLNAMES):
    """The names of mapping-github-username-to-fullname.csv, mapped to the GitHub login."""
    return {row['fullname'].strip(): row['github username'].strip() for row in _rows(path)}


def load_account_aliases(path=ACCOUNT_ALIASES):
    """Load second GitHub accounts of a person, mapped to their main account (#69)."""
    return {row['alias'].strip(): row['github_username'].strip() for row in _rows(path)}


def read_organisations(path=OLD_ORGANISATIONS):
    """The current organisation of each GitHub login in organisations.csv."""
    mapping = {}
    for row in _rows(path):
        for contributor in row['Team'].split(';'):
            contributor = contributor.strip()
            if contributor:
                mapping[contributor] = row['Organisation']
    return mapping


def organisation_names(path=OLD_ORGANISATIONS):
    """The spelling of each organisation in organisations.csv, by lower-case name (#86)."""
    return {row['Organisation'].lower(): row['Organisation'] for row in _rows(path)}


def read_overrides(path=OVERRIDES):
    """The year-specific organisations of organisation_mapping_overrides.csv, in file order."""
    return [{
        'github_username': row['github_username'],
        'organisation': row['organisation'],
        'from_year': int(row['from_year']) if row['from_year'] else None,
        'to_year': int(row['to_year']) if row['to_year'] else None,
    } for row in _rows(path)]


def load_organisation_mapping(mapping_file=OLD_ORGANISATIONS, overrides_file=OVERRIDES, year=None):
    """The organisation of each GitHub login, with the overrides for `year` applied."""
    organisation_mapping = read_organisations(mapping_file)

    if year:
        overrides = 0
        for row in read_overrides(overrides_file):
            from_year, to_year = row['from_year'], row['to_year']
            if from_year and from_year <= year and (not to_year or year <= to_year):
                organisation_mapping[row['github_username']] = row['organisation']
                overrides += 1
        if overrides:
            print(f"Applied {overrides} year-specific override(s) for {year}")

    print(f"Loaded mapping for {len(organisation_mapping)} contributors across {len(set(organisation_mapping.values()))} organisations")
    return organisation_mapping
