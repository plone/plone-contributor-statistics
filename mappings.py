"""Read the curated mapping files.

Every loader raises FileNotFoundError when its file is missing: a wrong path
must stop the run instead of producing statistics without the mapping.
"""

import csv

import paths


def _rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_excluded_repositories(path=paths.EXCLUDED_REPOSITORIES):
    """Load the repositories to skip, mapped to the reason for skipping them."""
    return {row['repository'].strip(): row['reason'].strip() for row in _rows(path)}


def load_bot_accounts(path=paths.BOT_ACCOUNTS):
    """Load bot accounts that the GitHub API lists as type User, mapped to a reason."""
    return {row['login'].strip(): row['reason'].strip() for row in _rows(path)}


def load_commit_authors(path=paths.COMMIT_AUTHORS):
    """Load the people behind commit emails that GitHub does not link to an account (#69).

    Maps the email (lower case) to the GitHub login, or to the person's name
    if they have no GitHub account.
    """
    return {row['email'].strip().lower(): row['github_username'].strip() or row['name'].strip()
            for row in _rows(path)}


def load_account_aliases(path=paths.ACCOUNT_ALIASES):
    """Load second GitHub accounts of a person, mapped to their main account (#69)."""
    return {row['alias'].strip(): row['github_username'].strip() for row in _rows(path)}


def read_organisations(path=paths.ORGANISATIONS):
    """The current organisation of each GitHub login in organisations.csv."""
    mapping = {}
    for row in _rows(path):
        for contributor in row['Team'].split(';'):
            contributor = contributor.strip()
            if contributor:
                mapping[contributor] = row['Organisation']
    return mapping


def organisation_names(path=paths.ORGANISATIONS):
    """The spelling of each organisation in organisations.csv, by lower-case name (#86)."""
    return {row['Organisation'].lower(): row['Organisation'] for row in _rows(path)}


def read_overrides(path=paths.OVERRIDES):
    """The year-specific organisations of organisation_mapping_overrides.csv, in file order."""
    return [{
        'github_username': row['github_username'],
        'organisation': row['organisation'],
        'from_year': int(row['from_year']) if row['from_year'] else None,
        'to_year': int(row['to_year']) if row['to_year'] else None,
    } for row in _rows(path)]


def load_organisation_mapping(mapping_file=paths.ORGANISATIONS, overrides_file=paths.OVERRIDES, year=None):
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
