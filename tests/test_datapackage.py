import json
import shutil
from pathlib import Path

import pytest

from scripts.tools import datapackage

REPO = Path(__file__).resolve().parent.parent


def test_kind_of():
    assert datapackage.kind_of(Path('curated/community/events.csv')) == 'events'
    assert datapackage.kind_of(Path('curated/community/board-of-directors.csv')) == 'board-of-directors'
    assert datapackage.kind_of(Path('curated/mappings/excluded_repositories.csv')) == 'excluded-repositories'
    assert datapackage.kind_of(Path('curated/plips/plone-plips-before-github.csv')) == 'plips-before-github'


def test_kind_of_unknown_raises():
    with pytest.raises(ValueError, match='nonsense'):
        datapackage.kind_of(Path('curated/mappings/nonsense.csv'))


def test_build_package_lists_every_curated_csv(tmp_repo):
    shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
    (tmp_repo / 'curated/mappings/people.csv').write_text('id,name\n')
    (tmp_repo / 'curated/community/events.csv').write_text('id\n')
    (tmp_repo / 'curated/mappings/no_schema_yet.csv').write_text('a\n')
    descriptor = datapackage.build_package(tmp_repo)
    names = {r['name']: r for r in descriptor['resources']}
    assert names['people']['schema'] == 'schemas/people.json'
    assert names['events']['path'] == 'community/events.csv'
    assert names['events']['schema'] == 'schemas/events.json'
    assert 'no-schema-yet' not in names
    assert [r['path'] for r in descriptor['resources']] == sorted(r['path'] for r in descriptor['resources'])


def test_committed_datapackage_is_current(monkeypatch):
    monkeypatch.chdir(REPO)
    committed = json.loads(Path('curated/datapackage.json').read_text())
    assert committed == datapackage.build_package()
