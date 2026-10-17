"""Checks that keep the archive and the docs honest (docs cleanup)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / 'archive'

# Old analyses and agent notes, moved unchanged from the repository root
ARCHIVED = [
    'DATA-TRENDS.md',
    'FINAL-3-tier-plip-levels.md',
    'comparison-plone-vs-volto.md',
    'contributor-levels.md',
    'plone-core-team.md',
    'plip-contributor-level-analysis',
    'volto.md',
    'team-volto.md',
    'individual_contributors.txt',
    '.claude/README.md',
]


@pytest.mark.parametrize('name', ARCHIVED)
def test_archived_file_moved(name):
    assert (ARCHIVE / name).exists()
    assert not (ROOT / name).exists()


def test_archive_readme_lists_every_file():
    table_paths = re.findall(r'^\| `([^`]+)`', (ARCHIVE / 'README.md').read_text(), re.M)
    listed = {path.rstrip('/').split('/')[0] for path in table_paths}
    on_disk = {p.name for p in ARCHIVE.iterdir() if p.name != 'README.md'}
    assert listed == on_disk


def _code_files():
    yield from ROOT.glob('*.py')
    yield ROOT / 'Makefile'
    yield from (ROOT / '.github' / 'workflows').glob('*.yml')


@pytest.mark.parametrize('name', ARCHIVED)
def test_archived_files_not_referenced(name):
    # A file name on its own, not part of a longer name or path:
    # 'reports/volto.md' and the default output 'plip-contributor-levels.md'
    # of analyze_plip_contributor_levels.py are other files.
    pattern = re.compile(r'''(?<![\w./-])''' + re.escape(name) + r'''(?![\w-])''')
    for path in _code_files():
        assert not pattern.search(path.read_text(encoding='utf-8')), path.name
