"""The migration check of the usernames: every person counts under the same username as before the migration."""

import csv
from pathlib import Path

from scripts.lib.model import load_registry

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def test_username_of_unchanged_on_real_registers():
    # The logins of people.csv before the switch to identities (git HEAD before the migration, plan 2c): the
    # collected files count every person under the same username as before
    registry = load_registry(REPO / 'curated/mappings')
    with open(HERE / 'people-github-before-citations.csv', newline='', encoding='utf-8') as f:
        before = {row['id']: row['github'] or f'person:{row["id"]}' for row in csv.DictReader(f)}
    assert {person_id: registry.username_of(person) for person_id, person in registry.people.items()} == before
