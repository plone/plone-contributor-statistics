"""The World Plone Day video types are a fixed list; only `Talk` counts as a talk (#119)."""

import csv
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
FILES = sorted(DATA.glob('*-world-plone-day-talks.csv'))
TYPES = {'Talk', 'Teaser', 'Announcement', 'Welcome', 'Recap', 'Duplicate', 'Opening', 'Full stream', 'Newsroom'}


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_known_video_types(path):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            assert row['Type'] in TYPES, f'unknown video type, add it to TYPES and decide whether it is a talk: {row}'
