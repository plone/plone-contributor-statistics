"""Format checks for the Board of Directors files (#86)."""

import csv
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
FILES = sorted(DATA.glob('*-board-of-directors.csv'))


def test_files_from_2004():
    years = [int(p.name[:4]) for p in FILES]
    assert years == list(range(2004, years[-1] + 1)), 'one file per year, without gaps'


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_one_sourced_row_per_member(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['Name', 'Organisation', 'Source', 'Role']
        rows = list(reader)

    names = [row['Name'] for row in rows]
    assert len(names) == len(set(names)), f'a member is listed twice: {names}'
    for row in rows:
        assert row['Name'].strip() and row['Organisation'].strip(), row
        # Unmapped or "Name (independent)", see #53
        assert row['Organisation'] not in ('Independent', 'independent', 'freelancer'), row
        assert row['Source'].startswith('https://'), row
        assert row['Role'] in ('voting', 'non-voting'), row
