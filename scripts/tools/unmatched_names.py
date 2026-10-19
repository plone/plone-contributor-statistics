#!/usr/bin/env python3
"""List people in the community data whose name isn't linked to a GitHub login.

Such people count by name, so someone with code work and community work can be
counted twice (#117). With --propose, the GitHub profile names of all Plone
contributors are fetched (needs GITHUB_TOKEN) and exact, unique matches are
printed as rows for curated/mappings/mapping-github-username-to-fullname.csv.
Check each proposal before adding it.
"""

import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict

import requests
from dotenv import load_dotenv

from scripts.lib import community, paths, people
from scripts.lib.github_api import github_graphql
from scripts.lib.mappings import organisation_names, read_organisations
from scripts.lib.years import RECOGNITION_YEAR

LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')


def unmatched_names(years):
    """{normalised name: {spelling, years, mentions}} of community records without a login."""
    records = [r for year in years for r in community.community_records(year)]
    index = people.build_person_index(records, organisations=set(organisation_names().values()))
    found = {}
    for record in records:
        key = index.key(record.person, record.handle, community.split(record.organisation))
        if key and key.startswith('name:'):
            entry = found.setdefault(key[5:], {'spelling': record.person, 'years': set(), 'mentions': 0})
            entry['years'].add(record.year)
            entry['mentions'] += 1
    return {name: {**entry, 'years': sorted(entry['years'])} for name, entry in found.items()}


def propose(unmatched, profile_names):
    """(login, name, source) for names that equal exactly one GitHub profile name."""
    logins_by_name = defaultdict(set)
    for login, name in profile_names.items():
        logins_by_name[people.normalise(name)].add(login)
    proposals = []
    for name, entry in sorted(unmatched.items()):
        logins = logins_by_name.get(name, set())
        if len(logins) == 1:
            login = next(iter(logins))
            proposals.append((login, entry['spelling'], f'GitHub profile name: https://github.com/{login}'))
    return proposals


def contributor_logins():
    """Every GitHub login with code work, or in organisations.csv."""
    logins = set(read_organisations())
    for path in glob.glob(str(paths.CONTRIBUTORS_DIR / '*-plone-contributors.csv')):
        with open(path, newline='', encoding='utf-8') as f:
            logins.update(row['username'] for row in csv.DictReader(f))
    return sorted(login for login in logins if LOGIN.fullmatch(login))


def fetch_profile_names(session, logins, batch=50):
    """{login: public profile name} from the GitHub GraphQL API."""
    names = {}
    for start in range(0, len(logins), batch):
        chunk = logins[start:start + batch]
        query = 'query {' + ' '.join(
            f'u{n}: repositoryOwner(login: "{login}") {{ login ... on User {{ name }} }}'
            for n, login in enumerate(chunk)) + '}'
        for owner in github_graphql(session, query).values():
            if owner and owner.get('name'):
                names[owner['login']] = owner['name'].strip()
    return names


def main():
    parser = argparse.ArgumentParser(description='List community names without a GitHub login')
    parser.add_argument('--since', type=int, default=2003, help='First year to check (default: 2003)')
    parser.add_argument('--propose', action='store_true',
                        help='Propose logins from GitHub profile names (needs GITHUB_TOKEN)')
    args = parser.parse_args()
    found = unmatched_names(range(args.since, RECOGNITION_YEAR + 1))
    for entry in sorted(found.values(), key=lambda entry: (-entry['mentions'], entry['spelling'].casefold())):
        print(f"{entry['spelling']}\t{entry['mentions']} mentions\t{entry['years'][0]}–{entry['years'][-1]}")
    print(f'{len(found)} names without a GitHub login', file=sys.stderr)
    if args.propose:
        load_dotenv()
        session = requests.Session()
        token = os.getenv('GITHUB_TOKEN')
        if token:
            session.headers['Authorization'] = f'token {token}'
        writer = csv.writer(sys.stdout, lineterminator='\n')
        print('\nProposals (check each before adding):')
        writer.writerows(propose(found, fetch_profile_names(session, contributor_logins())))


if __name__ == '__main__':
    main()
