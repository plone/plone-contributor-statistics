"""Format checks for the sprint files (#72, #86)."""

import csv
import re
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
FILES = sorted(DATA.glob('*-sprints.csv'))
DATE = re.compile(r'(\d{4}(-\d\d(-\d\d)?)?)?')


def test_files_from_2003():
    years = [int(p.name[:4]) for p in FILES]
    assert years == list(range(2003, years[-1] + 1)), 'one file per year, without gaps'


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_one_sourced_row_per_sprint(path):
    year = int(path.name[:4])
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    names = [row['Sprint'] for row in rows]
    assert len(names) == len(set(names)), f'a sprint is listed twice: {names}'
    for row in rows:
        assert row['Sprint'].strip() and row['Organisation'].strip(), row
        assert DATE.fullmatch(row['Start']) and DATE.fullmatch(row['End']), row
        assert row['Source'].startswith('https://'), row
        assert row['Level'] in ('strategic', 'community', ''), row
        # The Foundation only designated or funded strategic sprints from 2011 on
        if year < 2011:
            assert row['Level'] == '', row
        if row['Level']:
            assert 'Board: https://' in row['Source'] or 'plone.org/foundation/meetings' in row['Source'], \
                f'a level needs the Board decision as a source: {row}'
