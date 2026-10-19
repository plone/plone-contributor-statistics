"""Rules about the curated data that the schemas cannot express (#86, #53, #139).

The schemas and `scripts/tools/check.py` check the format; this file checks policy, on the model.
"""

import pytest

from scripts.lib import paths
from scripts.lib.model import load_registry, read_rows
from scripts.lib.model.names import fold
from scripts.lib.years import RECOGNITION_YEAR

BOARD_FILES = sorted(paths.COMMUNITY.glob('*-board-of-directors.csv'))
SPRINT_FILES = sorted(paths.COMMUNITY.glob('*-sprints.csv'))
CURATED_CSV = sorted(path for path in paths.COMMUNITY.parent.rglob('*.csv'))


def years_of(files):
    return [int(path.name[:4]) for path in files]


def test_a_board_file_for_every_year_since_2004():
    years = years_of(BOARD_FILES)
    assert years == list(range(2004, years[-1] + 1)), 'one file per year, without gaps'


def test_a_sprint_file_for_every_year_since_2003():
    years = years_of(SPRINT_FILES)
    assert years == list(range(2003, years[-1] + 1)), 'one file per year, without gaps'


@pytest.mark.parametrize('path', SPRINT_FILES, ids=lambda p: p.name)
def test_a_sprint_with_a_level_cites_the_board_minutes(path):
    year = int(path.name[:4])
    for row in read_rows(path):
        if not row['level']:
            continue
        # The Foundation only designated or funded strategic sprints from 2011 on
        assert year >= 2011, f'no level before 2011: {row["sprint"]}'
        assert 'Board: https://' in row['source'] or 'plone.org/foundation/meetings' in row['source'], \
            f'a level needs the Board decision as a source: {row["sprint"]}'


def test_team_leaders_file_for_every_year_since_2004():
    files = sorted(paths.COMMUNITY.glob('*-team-leaders.csv'))
    years = years_of(files)
    assert years == list(range(2004, years[-1] + 1)), 'one file per year, without gaps'
    for path in files:
        assert read_rows(path), f'{path.name} needs at least one team leader'


def test_the_recognition_year_has_release_managers():
    path = paths.COMMUNITY / f'{RECOGNITION_YEAR}-release-managers.csv'
    assert read_rows(path), f'{path.name} needs at least one release manager'


def test_no_organisation_is_called_independent():
    # An independent person has an organisation of kind `independent`, see #53; the word is no organisation
    for organisation in load_registry().organisations.values():
        for name in (organisation.name, *organisation.aliases):
            assert fold(name) != 'independent', f'{organisation.id}: use Unmapped or an independent organisation'


@pytest.mark.parametrize('path', CURATED_CSV, ids=lambda p: p.as_posix())
def test_utf8_with_unix_line_endings(path):
    # Hand-edited files: mixed line endings make every edit show up as a change of the whole file
    data = path.read_bytes()
    assert not data.startswith(b'\xef\xbb\xbf'), 'no byte order mark'
    assert b'\r' not in data, 'Unix line endings (LF), not CRLF'
    assert data.endswith(b'\n'), 'a newline at the end'
    data.decode('utf-8')
