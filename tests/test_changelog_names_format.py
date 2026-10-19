"""Format of curated/mappings/changelog_names.csv (#71)."""

import csv
import re
from pathlib import Path

from scripts.lib import paths

ROOT = Path(__file__).resolve().parent.parent
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?')
URL = re.compile(r'https?://\S+')


def rows():
    with open(ROOT / paths.CHANGELOG_NAMES, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_columns():
    fields, _ = rows()
    assert fields == ['changelog_name', 'github_username', 'name', 'source']


def test_each_name_once():
    _, found = rows()
    names = [row['changelog_name'].strip().casefold() for row in found]
    assert len(names) == len(set(names)), 'a changelog name is listed twice'


def test_rows():
    _, found = rows()
    for row in found:
        assert row['changelog_name'].strip() == row['changelog_name'] and row['changelog_name'], row
        if row['github_username']:
            assert LOGIN.fullmatch(row['github_username']), row
        else:
            # A person without a GitHub account counts by name; a name is no valid login
            assert row['name'].strip() and not LOGIN.fullmatch(row['name']), row
        # The changelog entry and the public record that links the name to the person
        assert URL.search(row['source']), row


def test_sorted_by_name():
    _, found = rows()
    names = [row['changelog_name'].casefold() for row in found]
    assert names == sorted(names)
