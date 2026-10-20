"""Every person without a GitHub login in the collected data is a person of the register."""

import csv

from tests.conftest import REPO


def usernames(pattern):
    for path in sorted((REPO / 'collected').glob(pattern)):
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                yield path.name, row['username']


def test_collected_person_ids_exist():
    with open(REPO / 'curated/mappings/people.csv', newline='', encoding='utf-8') as f:
        ids = {row['id'] for row in csv.DictReader(f)}
    found = list(usernames('contributors/*-plone-contributors.csv')) + list(
        usernames('changelogs/*-plone-changelog-entries.csv'))

    missing = {(name, username) for name, username in found
               if username.startswith('person:') and username.removeprefix('person:') not in ids}

    assert any(username.startswith('person:') for _, username in found)
    assert not missing
