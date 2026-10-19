"""Checks that keep the archive and the docs honest (docs cleanup)."""

import re
import subprocess
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


# Dead and experimental material, archived with its code, data and output together:
# bundle -> {original path: name in the bundle}
NPM_ORGS = ['codesyntax', 'eeacms', 'kitconcept', 'mbarde', 'myriadicity', 'plone', 'plone-collective',
            'plonegovbr', 'portalbrasil', 'redturtle', 'rohberg', 'rondon-open', 'sphnl', 'starzel']
BUNDLES = {
    'legacy-collectors': ['plone_contributor_statistics.py', 'plone_companies.py'],
    'plip-levels': ['analyze_plip_contributor_levels.py', 'generate_plip_3tier_levels.py', 'plip_stats.py'],
    'package-statistics': ['npm_package_stats.py', 'volto_addon_discovery.py', 'pypi_package_statistics.py',
                           'npm_mapping.txt', 'npm-packages-summary.md']
                          + [f'npm-packages-{org}.{ext}' for org in NPM_ORGS for ext in ('csv', 'md')],
    'cmfplone-releases': ['fetch_cmfplone_releases.py', 'filter_releases.py', 'cmfplone-releases.csv'],
    'flourish': ['create_organization_flourish_csv.py', 'create_individual_contributors_flourish_csv.py',
                 'plone-individual-contributors-flourish.csv', 'plone-organizations-bar-chart-race-flourish.csv',
                 'plone-individual-contributors-bar-chart-race-flourish.csv', 'plone-organizations-bar-chart-race.csv',
                 'data/plone-individual-contributors-flourish.csv',
                 'data/plone-organizations-bar-chart-race-flourish.csv'],
    'orphan-outputs': ['reports/plips.md', 'graphs/commits_prs_trend.png'],
    'volto-statistics': ['scripts/collect/volto_stats.py', 'scripts/report/generate_volto_team_report.py',
                         'reports/volto.md', 'tests/test_volto_stats_api_errors.py']
                        + [f'collected/volto/{year}-volto-stats.csv' for year in range(2016, 2026)],
}
BUNDLED = [(bundle, original) for bundle, originals in BUNDLES.items() for original in originals]


def bundled_name(original):
    # data/ copies get a prefix, so they don't clash with the root copies of the same name
    return original.replace('data/', 'data-') if original.startswith('data/') else Path(original).name


@pytest.mark.parametrize('bundle, original', BUNDLED)
def test_bundled_file_moved(bundle, original):
    assert (ARCHIVE / bundle / bundled_name(original)).exists()
    assert not (ROOT / original).exists()


@pytest.mark.parametrize('bundle', BUNDLES)
def test_bundle_listed_in_archive_readme(bundle):
    assert f'| `{bundle}/` |' in (ARCHIVE / 'README.md').read_text()


@pytest.mark.parametrize('bundle, original', [(b, o) for b, o in BUNDLED
                                             if not o.startswith(('npm-packages-', 'collected/volto/'))])
def test_bundle_row_names_original_path(bundle, original):
    # The npm-packages-* and yearly Volto files are named by their pattern
    row = next(line for line in (ARCHIVE / 'README.md').read_text().splitlines() if line.startswith(f'| `{bundle}/` |'))
    assert f'`{original}`' in row


@pytest.mark.parametrize('name', sorted({Path(o).name for o in sum(BUNDLES.values(), []) if o.endswith('.py')}))
def test_archived_scripts_not_referenced(name):
    pattern = re.compile(r'''(?<![\w./-])''' + re.escape(name) + r'''(?![\w-])''')
    for path in _code_files():
        assert not pattern.search(path.read_text(encoding='utf-8')), path.name


def test_clean_keeps_committed_files():
    makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
    recipe = makefile.split('\nclean:\n', 1)[1].split('\n\n', 1)[0]
    for committed in ['.csv', '.txt', '.md', 'graphs', 'reports']:
        assert committed not in recipe.replace('_checkpoint.csv', ''), committed


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
    yield from ROOT.glob('scripts/**/*.py')
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
KNOWN_MISSING = set()


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


def test_docs_shell_examples_reference_existing_files():
    # Commands in code blocks must work from the repository root
    block = re.compile(r'```shell\n(.*?)```', re.S)
    for page in docs_pages():
        for code in block.findall(page.read_text(encoding='utf-8')):
            for path in re.findall(r'(?<![\w./-])([\w./*-]+\.(?:csv|txt|md)|[\w.-]+/(?:[\w.-]+/)*)(?=\s|$)', code):
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


def test_docs_workflow_publishes_the_site():
    # The community page at the root, the docs below docs/
    build = _workflow_jobs('docs.yml')['build']
    assert 'make site' in build
    assert re.search(r'^\s+path: _site$', build, re.M)


def test_absolute_docs_urls_point_below_docs():
    site = 'plone.github.io/plone-contributor-statistics/'
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    for name in tracked:
        if name.startswith('archive/') or not name.endswith(('.md', '.py', '.yml', '.html', '.txt')):
            continue
        text = (ROOT / name).read_text(encoding='utf-8')
        for match in re.finditer(re.escape(site) + r'(\S*)', text):
            path = match.group(1).rstrip('.,;:)*>`\'"')
            assert path == '' or path.startswith('docs/'), f'{name}: {match.group(0)}'


def test_curated_files_reference_is_current():
    # docs/reference/curated-files.md is generated from the schemas: python -m scripts.tools.schema_docs
    from scripts.tools import schema_docs

    page = (ROOT / 'docs' / 'reference' / 'curated-files.md').read_text(encoding='utf-8')
    assert page == schema_docs.render()


def test_every_schema_kind_is_in_the_curated_files_reference():
    from scripts.tools import schema_docs

    listed = {kind for _, _, kinds in schema_docs.GROUPS for kind, _ in kinds}
    assert listed == {p.stem for p in (ROOT / 'curated' / 'schemas').glob('*.json')}
