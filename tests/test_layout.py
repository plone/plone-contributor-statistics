"""The repository layout: scripts by stage in scripts/, run as modules from the root."""

import os
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
