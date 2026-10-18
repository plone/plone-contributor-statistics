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


DOCS = ROOT / 'docs'

# Files and Make targets the docs name on purpose although they don't
# exist: they are broken or missing, see docs/explanation/known-limitations.md
KNOWN_MISSING = {
    'generate_plip_report.py',  # make generate-plip-report
    'plip_organisation_stats.py',  # make run-plip-organisations
    'pypi_package_stats.py',  # make pypi-packages, the script is pypi_package_statistics.py
}


def docs_pages():
    return sorted(p for p in DOCS.rglob('*.md') if '_build' not in p.parts)


def test_docs_exist():
    assert (DOCS / 'index.md').exists()


def test_docs_reference_existing_files():
    path_pattern = re.compile(r'`([\w./*-]+\.(?:py|csv|txt|md|yml|ini))`')
    for page in docs_pages():
        for path in path_pattern.findall(page.read_text(encoding='utf-8')):
            if path in KNOWN_MISSING:
                continue
            assert list(ROOT.glob(path.replace('YYYY', '*'))), f'{page.relative_to(ROOT)}: {path}'


def test_docs_reference_existing_make_targets():
    makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
    targets = set(re.findall(r'^([a-z0-9-]+):', makefile, re.M))
    for page in docs_pages():
        for target in re.findall(r'`make ([a-zA-Z0-9-]+)', page.read_text(encoding='utf-8')):
            if target in KNOWN_MISSING:
                continue
            assert target.replace('YYYY', '2024') in targets, f'{page.relative_to(ROOT)}: make {target}'


def _workflow_jobs(name):
    """The jobs of a workflow, as {job name: job text}, without a YAML parser."""
    text = (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8')
    jobs = text.split('\njobs:\n', 1)[1]
    parts = re.split(r'^  ([\w-]+):\n', jobs, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def test_docs_workflow_jobs_can_read_pages():
    # actions/configure-pages reads the Pages site, which needs the pages permission;
    # the top-level "contents: read" sets every other permission to none.
    for job, text in _workflow_jobs('docs.yml').items():
        if 'actions/configure-pages' in text:
            assert re.search(r'^\s+pages: (read|write)$', text, re.M), job


def test_docs_workflow_deploys_only_from_main():
    deploy = _workflow_jobs('docs.yml')['deploy']
    condition = re.search(r'^    if: (.+)$', deploy, re.M).group(1)
    assert "github.event_name != 'pull_request'" in condition
    assert "github.repository == 'plone/plone-contributor-statistics'" in condition
    assert "github.ref == 'refs/heads/main'" in condition
