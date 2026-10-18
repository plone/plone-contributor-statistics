"""Format checks for the team leader files (#86)."""

import csv
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
FILES = sorted(DATA.glob('*-team-leaders.csv'))


def test_files_from_2004():
    years = [int(p.name[:4]) for p in FILES]
    assert years == list(range(2004, years[-1] + 1)), 'one file per year, without gaps'


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_one_sourced_row_per_leader_and_team(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['Name', 'Team', 'Organisation', 'Source']
        rows = list(reader)

    assert rows, 'every year has a team leader'
    keys = [(row['Name'], row['Team']) for row in rows]
    assert len(keys) == len(set(keys)), f'a leader is listed twice for a team: {keys}'
    for row in rows:
        assert row['Name'].strip() and row['Team'].strip() and row['Organisation'].strip(), row
        assert row['Source'].startswith('https://'), row
