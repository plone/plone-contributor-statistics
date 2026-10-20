import json
import shutil
from pathlib import Path

import pytest

from scripts.tools import datapackage

REPO = Path(__file__).resolve().parent.parent


def test_kind_of():
    assert datapackage.kind_of(Path('curated/community-contributions/2023-sprints.csv')) == 'sprints'
    assert datapackage.kind_of(Path('curated/mappings/affiliation_proposals.csv')) == 'affiliation-proposals'
    assert datapackage.kind_of(Path('curated/plips/plone-plips-before-github.csv')) == 'plips-before-github'


def test_kind_of_unknown_raises():
    with pytest.raises(ValueError, match='nonsense'):
        datapackage.kind_of(Path('curated/mappings/nonsense.csv'))


def test_build_package_lists_every_curated_csv(tmp_repo):
    shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
    (tmp_repo / 'curated/mappings/people.csv').write_text('id,name,github,source\n')
    (tmp_repo / 'curated/community-contributions/2023-sprints.csv').write_text('sprint\n')
    (tmp_repo / 'curated/mappings/no_schema_yet.csv').write_text('a\n')
    descriptor = datapackage.build_package(tmp_repo)
    names = {r['name']: r for r in descriptor['resources']}
    assert names['people']['schema'] == 'schemas/people.json'
    assert names['2023-sprints']['path'] == 'community-contributions/2023-sprints.csv'
    assert names['2023-sprints']['schema'] == 'schemas/sprints.json'
    assert 'no-schema-yet' not in names
    assert [r['path'] for r in descriptor['resources']] == sorted(r['path'] for r in descriptor['resources'])


def test_committed_datapackage_is_current(monkeypatch):
    monkeypatch.chdir(REPO)
    committed = json.loads(Path('curated/datapackage.json').read_text())
    assert committed == datapackage.build_package()
