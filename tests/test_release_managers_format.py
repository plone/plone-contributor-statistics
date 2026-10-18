"""Format checks for the release manager files (#86)."""

import csv
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / 'data' / 'community-contributions'
FILES = sorted(DATA.glob('*-release-managers.csv'))


def test_files_from_2004():
    years = [int(p.name[:4]) for p in FILES]
    assert years == list(range(2004, years[-1] + 1)), 'one file per year, without gaps'


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_one_sourced_row_per_release_manager(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['Name', 'Github', 'Organisation', 'Source']
        rows = list(reader)

    assert rows, 'every year has a release manager'
    names = [row['Name'] for row in rows]
    assert len(names) == len(set(names)), f'a release manager is listed twice: {names}'
    for row in rows:
        assert row['Name'].strip() and row['Github'].strip() and row['Organisation'].strip(), row
        assert row['Source'].startswith('https://'), row
