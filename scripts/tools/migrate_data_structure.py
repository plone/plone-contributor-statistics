#!/usr/bin/env python3
"""Migrate the curated files to the people register (#139).

fetch-names is the one online step: it fetches the GitHub profile names of the
logins that no curated file names, and writes them to a file that the
migration reads. It needs GITHUB_TOKEN in the environment.
"""

import argparse
import csv
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

from scripts.lib import community, paths
from scripts.lib.mappings import _rows
from scripts.tools.unmatched_names import fetch_profile_names

FIRST_YEAR = 2003
LAST_YEAR = 2026


def _login_cells(root):
    """Every login that the mapping files name, as a set."""
    logins = set()
    for row in _rows(root / paths.ORGANISATIONS):
        logins.update(part.strip() for part in row['Team'].split(';') if part.strip())
    for path in (paths.OVERRIDES, paths.SOURCES):
        if (root / path).exists():
            logins.update(row['github_username'].strip() for row in _rows(root / path))
    logins.update(row['github_username'].strip() for row in _rows(root / paths.COMMIT_AUTHORS))
    logins.update(row['github_username'].strip() for row in _rows(root / paths.ACCOUNT_ALIASES))
    logins.discard('')
    return logins


def logins_without_a_name(root=Path('.')):
    """Logins of the mapping files that no curated file gives a name.

    A login is named by a row of the fullname mapping, by a handle column of
    the community data, or by a name in commit_authors.csv.
    """
    root = Path(root)
    named = {row['github username'].strip().casefold() for row in _rows(root / paths.FULLNAMES)}
    named.update(row['github_username'].strip().casefold()
                 for row in _rows(root / paths.COMMIT_AUTHORS) if row['name'].strip())
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        named.update(record.handle.casefold()
                     for record in community.community_records(year, root / paths.COMMUNITY) if record.handle)
    return {login for login in _login_cells(root) if login.casefold() not in named}


def write_profile_names(names, path):
    """Write login, name and fetch date, sorted by login; a login without a profile name is its own name."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['login', 'name', 'fetched'])
        for login in sorted(names):
            writer.writerow([login, names[login] or login, today])


def fetch_names(out):
    """Fetch the profile names of the unnamed logins and write them to `out`."""
    load_dotenv()
    session = requests.Session()
    token = os.getenv('GITHUB_TOKEN')
    if token:
        session.headers['Authorization'] = f'token {token}'
    logins = sorted(logins_without_a_name())
    fetched = fetch_profile_names(session, logins)
    write_profile_names({login: fetched.get(login, '') for login in logins}, out)
    print(f'{len(logins)} logins, {sum(1 for login in logins if fetched.get(login))} with a profile name')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Migrate the curated files to the people register')
    commands = parser.add_subparsers(dest='command', required=True)
    fetch = commands.add_parser('fetch-names', help='Fetch the GitHub profile names the migration needs '
                                                    '(needs GITHUB_TOKEN)')
    fetch.add_argument('--out', required=True, help='The CSV file to write: login, name, fetched')
    args = parser.parse_args(argv)
    if args.command == 'fetch-names':
        fetch_names(args.out)


if __name__ == '__main__':
    main()
