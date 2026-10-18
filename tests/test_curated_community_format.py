"""Format checks for all curated community files (#52); see docs/reference/data-files.md."""

import csv
import re
from pathlib import Path

import pytest
from scripts.lib import paths

DATA = Path(__file__).resolve().parent.parent / paths.COMMUNITY
# Allowed headers per kind of file; older years of some kinds have no Source column yet (#86)
KINDS = {
    'board-of-directors': [['Name', 'Organisation', 'Source', 'Role']],
    'plone-conference': [['Organisation', 'Organiser(s)', 'Source', 'Notes'], ['Organisation']],
    'plone-conference-trainings': [['Title', 'Trainer(s)', 'GitHub Handle(s)', 'Organisation', 'Source'],
                                   ['Title', 'Trainer(s)', 'GitHub Handle(s)', 'Organisation']],
    'podcasts': [['Name', 'Organisation']],
    'release-managers': [['Name', 'Github', 'Organisation', 'Source']],
    'strategic-sprints': [['Sprint', 'Organiser/Host', 'Organisation', 'Source'],
                          ['Sprint', 'Organiser/Host', 'Organisation']],
    'team-leaders': [['Name', 'Team', 'Organisation', 'Source']],
    'world-plone-day-event': [['Organisation', 'Reference']],
    'world-plone-day-talks': [['Video Title', 'Speaker(s)', 'Organisation', 'Event / Location', 'Type', 'YouTube ID']],
}
# Columns with several people or handles, separated by semicolons; a comma there is a wrong
# separator. Organisation names may contain commas; test_curated_organisation_names checks them.
MULTI_VALUE = ['Organiser(s)', 'Organiser/Host', 'Trainer(s)', 'GitHub Handle(s)', 'Speaker(s)']
FILES = sorted(DATA.glob('[0-9][0-9][0-9][0-9]-*.csv'))


def kind(path):
    return path.stem[5:]


def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_known_kind_and_header(path):
    assert kind(path) in KINDS, f'unknown kind of curated file: {path.name}'
    assert read(path)[0] in KINDS[kind(path)]


ROOT = Path(__file__).resolve().parent.parent
CURATED = sorted((ROOT / 'curated').rglob('*.csv'))


@pytest.mark.parametrize('path', CURATED, ids=lambda p: str(p.relative_to(ROOT)))
def test_utf8_with_unix_line_endings(path):
    # Hand-edited files: mixed line endings make every edit show up as a change of the whole file
    data = path.read_bytes()
    assert not data.startswith(b'\xef\xbb\xbf'), 'no byte order mark'
    assert b'\r' not in data, 'Unix line endings (LF), not CRLF'
    assert data.endswith(b'\n'), 'a newline at the end'
    data.decode('utf-8')


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_rows_are_complete(path):
    for number, row in enumerate(read(path)[1], 2):
        assert None not in row, f'line {number}: more values than columns'
        assert None not in row.values(), f'line {number}: fewer values than columns'
        # Unmapped when the organisation isn't known, see #53
        assert row['Organisation'].strip(), f'line {number}: no organisation, use Unmapped'


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_multiple_values_are_separated_by_semicolons(path):
    for number, row in enumerate(read(path)[1], 2):
        for column in MULTI_VALUE:
            assert ',' not in row.get(column, ''), f"line {number}: use ';' in {column}: {row[column]!r}"


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_sources_are_links(path):
    for number, row in enumerate(read(path)[1], 2):
        for column in ('Source', 'Reference'):
            if column in row:
                assert re.search(r'https?://', row[column]), f'line {number}: {column} needs a link: {row[column]!r}'
