"""The committed derived data and reports are what the scripts make of the committed inputs (#52).

Runs the derive and report steps offline in a copy of the repository and
compares the results with the committed files. Fails when a script breaks on
the real data, or when an input changed without regenerating the outputs.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# The steps that need no network; the graphs are left out, because their pixels
# depend on the matplotlib version
TARGETS = ['run-organisation-stats', 'run-plip-organisations', 'three-year-summary', 'five-year-summary',
           'ten-year-summary', 'yearly-activity', 'generate-report', 'community-recognition', 'community-page']
COMPARED = ['derived', 'reports']
GENERATED = re.compile(r'^\*?Generated( on)?:.*$', re.M)


def committed_years():
    """The last year of the committed summaries and the year of the committed recognition report."""
    # The newest ones, if older years are still committed next to them
    summary = max((ROOT / 'derived' / 'summaries').glob('summary-past-three-years-*.csv'))
    recognition = max((ROOT / 'derived' / 'community-recognition').glob('*-community-recognition-report.csv'))
    return summary.stem[-4:], recognition.name[:4]


def outputs(root):
    return {p.relative_to(root): p for folder in COMPARED for p in (root / folder).rglob('*')
            if p.is_file() and p.suffix in ('.csv', '.md', '.txt', '.json') and p.name != 'README.md'}


@pytest.fixture(scope='module')
def regenerated(tmp_path_factory):
    copy = tmp_path_factory.mktemp('repository')
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '*_checkpoint.csv')
    for name in ['scripts', 'curated', 'collected', 'derived', 'reports']:
        shutil.copytree(ROOT / name, copy / name, ignore=ignore)
    shutil.copy2(ROOT / 'Makefile', copy / 'Makefile')
    summary_end, recognition_year = committed_years()
    # The Makefile calls `python`: use the interpreter of the tests
    env = {**os.environ, 'PATH': f'{Path(sys.executable).parent}{os.pathsep}{os.environ["PATH"]}',
           'MPLBACKEND': 'Agg'}
    result = subprocess.run(['make', '--no-print-directory', *TARGETS, f'SUMMARY_END={summary_end}',
                             f'RECOGNITION_YEAR={recognition_year}'],
                            cwd=copy, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    return copy


@pytest.mark.timeout(600)
def test_derived_data_and_reports_are_reproducible(regenerated):
    committed, fresh = outputs(ROOT), outputs(regenerated)
    assert sorted(fresh) == sorted(committed), 'the same files'
    stale = [str(path) for path in committed
             if GENERATED.sub('', committed[path].read_text(encoding='utf-8'))
             != GENERATED.sub('', fresh[path].read_text(encoding='utf-8'))]
    assert not stale, f'regenerate these files (see docs/how-to/regenerate-after-a-mapping-change.md): {stale}'
