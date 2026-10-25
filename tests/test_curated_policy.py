"""Rules about the curated data that the schemas cannot express (#86, #53, #139).

The schemas and `scripts/tools/check.py` check the format; this file checks policy, on the model.
"""

import pytest

from scripts.lib import paths
from scripts.lib.model import items, load_registry, read_rows
from scripts.lib.model.names import fold
from scripts.lib.years import RECOGNITION_YEAR

CURATED_CSV = sorted(path for path in paths.COMMUNITY.parent.rglob('*.csv'))


def years_with(path, keep=lambda row: True):
    """The years of the rows of a community file, sorted, once each."""
    return sorted({row['year'] for row in read_rows(path) if keep(row)})


def test_board_rows_for_every_year_since_2004():
    years = years_with(paths.BOARD_OF_DIRECTORS)
    assert years == list(range(2004, years[-1] + 1)), 'rows for every year, without gaps'


def test_sprint_rows_for_every_year_since_2003():
    years = years_with(paths.EVENTS, lambda row: row['kind'] == 'sprint')
    assert years == list(range(2003, years[-1] + 1)), 'rows for every year, without gaps'


def test_a_sprint_with_a_level_cites_the_board_minutes():
    for row in read_rows(paths.EVENTS):
        if row['kind'] != 'sprint' or not row['level']:
            continue
        # The Foundation only designated or funded strategic sprints from 2011 on
        assert row['year'] >= 2011, f'no level before 2011: {row["name"]}'
        assert 'Board: https://' in row['cited_as'] or 'plone.org/foundation/meetings' in row['cited_as'], \
            f'a level needs the Board decision as a source: {row["name"]}'


def test_team_leader_rows_for_every_year_since_2004():
    years = years_with(paths.TEAM_LEADERS)
    assert years == list(range(2004, years[-1] + 1)), 'rows for every year, without gaps'


def test_the_recognition_year_has_release_managers():
    assert items(RECOGNITION_YEAR, 'release-managers'), f'{RECOGNITION_YEAR} needs at least one release manager'


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
