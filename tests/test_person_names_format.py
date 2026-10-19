"""Format checks for the name-to-login mapping (#117)."""

import csv
import re
from pathlib import Path

from scripts.lib import paths
from scripts.lib.people import normalise

ROOT = Path(__file__).resolve().parent.parent
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')


def rows():
    with open(ROOT / paths.FULLNAMES, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['github username', 'fullname', 'source']
        return list(reader)


def test_every_row_has_a_login_a_name_and_a_public_record():
    for row in rows():
        assert LOGIN.fullmatch(row['github username']), row
        assert row['fullname'].strip() == row['fullname'] and row['fullname'], row
        # The record links the login's own profile, not someone else's
        assert f"https://github.com/{row['github username']}".casefold() in row['source'].casefold(), row


def test_each_name_maps_to_one_login():
    seen = {}
    for row in rows():
        name = normalise(row['fullname'])
        assert seen.setdefault(name, row['github username']) == row['github username'], name


def test_sorted_by_login():
    logins = [row['github username'].casefold() for row in rows()]
    assert logins == sorted(logins)
