#!/usr/bin/env python3
"""List people of the register without a GitHub login who appear as a login, and propose the login (#117).

A person without a login counts by person id; if their code work comes under a login that the register does
not know, they count twice. This lists the people whose name equals a collected login. With --propose, the
GitHub profile names of the logins the register does not know are fetched (needs GITHUB_TOKEN) and exact,
unique matches are printed as rows for curated/mappings/identities.csv. Check each proposal before adding it.
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict

import requests
from dotenv import load_dotenv

from scripts.lib import paths
from scripts.lib.github_api import github_graphql
from scripts.lib.model import load_registry
from scripts.lib.model.names import fold

LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')


def contributor_logins(registry=None, contributors_dir=paths.CONTRIBUTORS_DIR):
    """Every GitHub login with code work in the collected files, or in the register."""
    registry = registry or load_registry()
    logins = {person.github for person in registry.people.values() if person.github}
    for path in sorted(contributors_dir.glob('*-plone-contributors.csv')):
        with open(path, newline='', encoding='utf-8') as f:
            logins.update(row['username'] for row in csv.DictReader(f))
    return sorted(login for login in logins if LOGIN.fullmatch(login))


def unregistered(registry, logins):
    """The logins that belong to no person of the register."""
    return [login for login in logins if registry.person_for(login=login) is None]


def unmatched_people(registry, logins):
    """{person id: [logins]} of people without a login whose name, folded without spaces, is an unregistered login."""
    by_key = defaultdict(list)
    for login in unregistered(registry, logins):
        by_key[fold(login).replace(' ', '')].append(login)
    found = {}
    for person in registry.people.values():
        key = fold(person.name).replace(' ', '')
        if not person.github and by_key.get(key):
            found[person.id] = sorted(by_key[key])
    return found


def propose(registry, profile_names):
    """(person, 'login', login, source) for people without a login whose name is exactly one profile name."""
    logins_by_name = defaultdict(set)
    for login, name in profile_names.items():
        logins_by_name[fold(name)].add(login)
    ids_by_name = defaultdict(set)
    for person in registry.people.values():
        ids_by_name[fold(person.name)].add(person.id)
    proposals = []
    for person in sorted(registry.people.values(), key=lambda person: person.id):
        if person.github:
            continue
        logins = logins_by_name.get(fold(person.name), set())
        if len(logins) == 1 and len(ids_by_name[fold(person.name)]) == 1:
            login = next(iter(logins))
            if registry.person_for(login=login) is None:
                proposals.append((person.id, 'login', login, f'https://github.com/{login}'))
    return proposals


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
    parser = argparse.ArgumentParser(description='List people without a GitHub login who appear as a login')
    parser.add_argument('--propose', action='store_true',
                        help='Propose logins from GitHub profile names (needs GITHUB_TOKEN)')
    args = parser.parse_args()
    registry = load_registry()
    logins = contributor_logins(registry)
    found = unmatched_people(registry, logins)
    for person_id, matching in sorted(found.items()):
        print(f"{person_id}\t{registry.people[person_id].name}\tlogin: {'; '.join(matching)}")
    print(f'{len(found)} people without a GitHub login whose name is a login', file=sys.stderr)
    if args.propose:
        load_dotenv()
        session = requests.Session()
        token = os.getenv('GITHUB_TOKEN')
        if token:
            session.headers['Authorization'] = f'token {token}'
        writer = csv.writer(sys.stdout, lineterminator='\n')
        print('\nProposals for identities.csv (check each before adding):')
        writer.writerow(['person', 'kind', 'value', 'source'])
        writer.writerows(propose(registry, fetch_profile_names(session, unregistered(registry, logins))))


if __name__ == '__main__':
    main()
