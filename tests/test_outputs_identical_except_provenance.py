"""The switch to events changed no count, point, level or name: only where a contribution's row is (#139, plan 3b).

Regenerates derived/ and reports/ offline in a copy of the repository, as tests/test_reproducible_outputs.py does,
and compares them with the outputs of the commit before the switch, column by column. Only the provenance of a
contribution may differ: its `file` and `line`, which now name a row of curated/community/. The links of the
community page must point to those rows.
"""

import csv
import io
import json
import subprocess
from pathlib import Path

import pytest

from tests.test_reproducible_outputs import COMPARED, GENERATED, ROOT, outputs, regenerated  # noqa: F401

# The last commit with the yearly community files
BEFORE = '122a213'
# The columns of a contribution that say where its row is
PROVENANCE = ('file', 'line')
# The outputs compared, as tests/test_reproducible_outputs.py compares them
SUFFIXES = ('.csv', '.md', '.txt', '.json')


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')


def before(path):
    """The text of an output file at the commit before the switch."""
    return _git('show', f'{BEFORE}:{path.as_posix()}').stdout


def without_provenance(value):
    if isinstance(value, dict):
        return {key: without_provenance(item) for key, item in value.items() if key not in PROVENANCE}
    if isinstance(value, list):
        return [without_provenance(item) for item in value]
    return value


def contributions(page):
    """Every contribution of the community page data."""
    for organisation in page['organisations'].values():
        for category in organisation['categories'].values():
            yield from category['contributions']


@pytest.fixture(scope='module')
def available():
    if _git('cat-file', '-e', f'{BEFORE}^{{commit}}').returncode:
        pytest.skip(f'the commit {BEFORE} is not in this clone')


@pytest.mark.timeout(600)
def test_the_outputs_differ_from_those_before_the_switch_only_in_provenance(available, regenerated):  # noqa: F811
    fresh = outputs(regenerated)
    listed = _git('ls-tree', '-r', '--name-only', BEFORE, *COMPARED).stdout.split('\n')
    assert {Path(name) for name in listed if Path(name).suffix in SUFFIXES and Path(name).name != 'README.md'} == set(
        fresh), 'the same files'
    changed = []
    for path in sorted(fresh):
        new_text, old_text = fresh[path].read_text(encoding='utf-8'), before(path)
        if GENERATED.sub('', new_text) == GENERATED.sub('', old_text):
            continue
        changed.append(path.as_posix())
        if path.suffix == '.json':
            assert without_provenance(json.loads(new_text)) == without_provenance(json.loads(old_text)), path
        elif path.suffix == '.csv':
            new_rows, old_rows = (list(csv.DictReader(io.StringIO(t))) for t in (new_text, old_text))
            assert [without_provenance(r) for r in new_rows] == [without_provenance(r) for r in old_rows], path
        else:
            pytest.fail(f'{path} changed')
    # The page links its contributions to their rows, and those moved
    assert changed == ['derived/community-page.json']


def test_the_page_links_the_rows_of_the_community_files(available, regenerated):  # noqa: F811
    page = json.loads((regenerated / 'derived/community-page.json').read_text(encoding='utf-8'))
    linked = [c for c in contributions(page) if c['file'].startswith('curated/')]
    assert linked
    for contribution in linked:
        assert contribution['file'].startswith('curated/community/'), contribution
        with open(ROOT / contribution['file'], newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        # Line 1 is the header; the row's citation is the source the page shows
        row = rows[contribution['line'] - 2]
        assert (row['cited_as'].strip() or None) == contribution['source'], contribution
