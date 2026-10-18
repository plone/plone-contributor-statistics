"""The curated files of the recognition year spell organisations as in organisations.csv (#86)."""

import csv
from pathlib import Path

import pytest
from scripts.lib import paths

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / paths.COMMUNITY
FILES = [p for p in sorted(DATA.glob('2025-*.csv')) if 'recognition' not in p.name]
# Not organisations, but kept apart in the report
LABELS = {'Unmapped', 'Plone Foundation', 'Plone Foundation (community volunteer)'}


def organisation_names():
    with open(ROOT / paths.ORGANISATIONS, newline='', encoding='utf-8') as f:
        return {row['Organisation'] for row in csv.DictReader(f)}


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_organisations_are_listed(path):
    names = organisation_names() | LABELS
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            for organisation in filter(None, (o.strip() for o in (row.get('Organisation') or '').split(';'))):
                assert organisation in names, f'{organisation!r} is not spelled as in organisations.csv: {row}'
