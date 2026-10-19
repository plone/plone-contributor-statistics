"""Format checks for the PLIPs from before GitHub (#14)."""

import csv
import re
from pathlib import Path

from scripts.lib import paths

FILE = Path(__file__).resolve().parent.parent / paths.PLIPS_BEFORE_GITHUB
COLUMNS = ['Number', 'Numbering', 'Title', 'Proposer', 'Implementers', 'State', 'Proposed', 'Completed',
           'Release', 'Same as', 'Source', 'Quote', 'Notes']
DATE = re.compile(r'(\d{4}(-\d\d(-\d\d)?)?)?')


def read():
    with open(FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_columns():
    assert read()[0] == COLUMNS


def test_one_sourced_row_per_plip():
    rows = read()[1]
    keys = [(row['Numbering'], row['Number']) for row in rows]
    assert len(keys) == len(set(keys)), 'a PLIP is listed twice under the same number'
    for row in rows:
        assert row['Numbering'] in ('roadmap', 'trac'), row
        assert row['Number'].isdigit() and row['Title'].strip(), row
        assert row['Source'].startswith('https://'), row
        assert DATE.fullmatch(row['Proposed']) and DATE.fullmatch(row['Completed']), row
        assert '&' not in row['Proposer'] + row['Implementers'], 'separate names with semicolons'


def test_same_as_points_back():
    rows = read()[1]
    keys = {f"{row['Numbering']} {row['Number']}": row for row in rows}
    for key, row in keys.items():
        if row['Same as']:
            assert keys[row['Same as']]['Same as'] == key, row
