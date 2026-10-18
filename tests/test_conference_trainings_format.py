"""Format checks for the Plone Conference training files (#30)."""

import csv
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
FILES = sorted(DATA.glob('*-plone-conference-trainings.csv'))


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_one_handle_and_organisation_per_trainer(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames[:4] == ['Title', 'Trainer(s)', 'GitHub Handle(s)', 'Organisation']
        rows = list(reader)

    for row in rows:
        trainers = row['Trainer(s)'].split(';')
        assert ',' not in row['Trainer(s)'], f"use ';' between trainers: {row}"
        assert len(row['GitHub Handle(s)'].split(';')) == len(trainers), row
        assert len(row['Organisation'].split(';')) == len(trainers), row
        # Unmapped or "Name (independent)", see #53
        assert 'Independent' not in row['Organisation'].split(';'), row


@pytest.mark.parametrize('path', [p for p in FILES if p.name < '2025'], ids=lambda p: p.name)
def test_sources(path):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            assert row['Source'].startswith('https://'), row
