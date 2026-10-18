"""The repository layout: scripts by stage in scripts/, run as modules from the root."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted(p for p in (ROOT / 'scripts').glob('*/*.py') if p.parent.name != 'lib')


def module(script):
    return '.'.join(script.relative_to(ROOT).with_suffix('').parts)


def test_stage_folders():
    assert {p.parent.name for p in SCRIPTS} == {'collect', 'derive', 'report', 'tools'}


@pytest.mark.parametrize('script', SCRIPTS, ids=module)
def test_scripts_run_as_modules(script, tmp_path):
    # Run from an empty directory: a script that ignored --help would fail there
    # instead of writing into the repository
    env = {**os.environ, 'PYTHONPATH': str(ROOT), 'MPLBACKEND': 'Agg'}
    result = subprocess.run([sys.executable, '-m', module(script), '--help'], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr[-1000:]
    assert 'usage:' in result.stdout
    assert not list(tmp_path.iterdir())


def test_no_python_files_in_root():
    assert not list(ROOT.glob('*.py'))


def test_no_per_year_targets():
    # One target per year meant editing the Makefile every year; YEAR=... replaces them
    makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
    assert not re.findall(r'^[\w-]+-(?:19|20)\d\d:', makefile, re.M)


def test_year_runs_the_pipeline_in_order():
    result = subprocess.run(['make', '-n', '--no-print-directory', 'year', 'YEAR=2024'], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    steps = [line.split()[2] for line in result.stdout.splitlines() if line.startswith('python -m scripts.')]
    assert steps == [
        'scripts.collect.plone_contributors',
        'scripts.collect.plone_pr_interactions',
        'scripts.collect.volto_stats',
        'scripts.collect.plone_plips',
        'scripts.derive.organisation_stats',
        'scripts.derive.plip_organisation_stats',
        'scripts.derive.multi_year_summary',
        'scripts.derive.multi_year_summary',
        'scripts.derive.multi_year_summary',
        'scripts.derive.yearly_activity_analysis',
        'scripts.report.generate_yearly_graphs',
        'scripts.report.generate_contributor_report',
        'scripts.report.generate_volto_team_report',
        'scripts.report.generate_community_recognition_report',
    ]
    assert 'python -m scripts.collect.plone_contributors --year 2024' in result.stdout
    assert 'python -m scripts.derive.multi_year_summary --years 2020 2021 2022 2023 2024' in result.stdout
    assert 'python -m scripts.report.generate_community_recognition_report --year 2024' in result.stdout


@pytest.mark.parametrize('script', SCRIPTS, ids=module)
def test_scripts_suggest_commands_that_work(script):
    # Help texts and hints must not send people to `python name.py` or to removed Make targets
    source = script.read_text(encoding='utf-8')
    assert not re.findall(r'python [\w/]+\.py', source)
    makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
    targets = set(re.findall(r'^([\w-]+):', makefile, re.M))
    # A command, not prose: quoted, or after 'Run:'
    for target in re.findall(r"(?:['\"`]|Run:\s+)make ([a-z][\w-]*)", source):
        assert target in targets, target


def test_paths_follow_layout():
    from scripts.lib import paths
    for name, value in vars(paths).items():
        if isinstance(value, Path) and name.isupper():
            assert value.parts[0] in {'curated', 'collected', 'derived', 'reports'}, f'{name}: {value}'


def test_tmp_repo_has_layout(tmp_repo):
    from scripts.lib import paths
    for name, value in vars(paths).items():
        if isinstance(value, Path) and name.isupper():
            folder = value if not value.suffix else value.parent
            assert (tmp_repo / folder).is_dir(), f'{name}: {folder}'


ALLOWED_ROOT = {'README.md', 'AGENTS.md', 'CLAUDE.md', 'Makefile', 'requirements.txt', 'requirements-docs.txt',
                'pytest.ini', '.env.example', '.gitignore', '.github', 'scripts', 'curated', 'collected',
                'derived', 'reports', 'docs', 'tests', 'archive'}


def test_root_contains_only_allowed_entries():
    # New files go into the folder of their role, not into the root
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert {p.split('/')[0] for p in tracked} <= ALLOWED_ROOT


@pytest.mark.parametrize('folder', ['scripts', 'curated', 'collected', 'derived', 'reports'])
def test_folder_has_readme(folder):
    assert (ROOT / folder / 'README.md').exists()
