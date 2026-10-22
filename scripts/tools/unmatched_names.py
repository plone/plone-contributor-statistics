#!/usr/bin/env python3
"""List people of the register without a GitHub login who appear as a login, and propose the login (#117).

A person without a login counts by person id; if their code work comes under a login that the register does
not know, they count twice. This lists the people whose name equals a collected login. With --propose, the
GitHub profile names of the logins the register does not know are fetched (needs GITHUB_TOKEN) and exact,
unique matches are printed as a `github` identity for curated/mappings/identities.csv, citing the GitHub
profile: the login is the person's main account, which their code work counts under. Check each proposal,
capture the profile (the command is printed with it), then add the row.
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
from scripts.lib.model import GITHUB, load_registry, source_id
from scripts.lib.model.names import fold

LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')


def contributor_logins(registry=None, contributors_dir=paths.CONTRIBUTORS_DIR):
    """Every GitHub login with code work in the collected files, or in the register."""
    registry = registry or load_registry()
    logins = {login for login in map(registry.github_of, registry.people) if login}
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
        if not registry.github_of(person.id) and by_key.get(key):
            found[person.id] = sorted(by_key[key])
    return found


def propose(registry, profile_names):
    """(person id, login, profile name) for people without a login whose name is exactly one profile name."""
    logins_by_name = defaultdict(set)
    for login, name in profile_names.items():
        logins_by_name[fold(name)].add(login)
    ids_by_name = defaultdict(set)
    for person in registry.people.values():
        ids_by_name[fold(person.name)].add(person.id)
    proposals = []
    for person in sorted(registry.people.values(), key=lambda person: person.id):
        if registry.github_of(person.id):
            continue
        logins = logins_by_name.get(fold(person.name), set())
        if len(logins) == 1 and len(ids_by_name[fold(person.name)]) == 1:
            login = next(iter(logins))
            if registry.person_for(login=login) is None:
                proposals.append((person.id, login, profile_names[login]))
    return proposals


def proposal_line(person_id, login, name):
    """The proposal as the line --propose prints: the identity row citing the profile, and how to capture it."""
    profile = f'https://github.com/{login}'
    return (f'{person_id},{GITHUB},{login},{source_id(profile)},,  # profile name "{name}"; capture the profile '
            f'first: python -m scripts.tools.capture {profile} --name "{name}"')


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
        print('\nProposals for curated/mappings/identities.csv (check each, capture the profile, then add the row '
              'without the comment):')
        for proposal in propose(registry, fetch_profile_names(session, unregistered(registry, logins))):
            print(proposal_line(*proposal))


if __name__ == '__main__':
    main()
