"""The mapping files are read in one place and must exist (repository layout)."""

from pathlib import Path

import pytest

from scripts.lib import mappings
from scripts.lib import paths

LOADERS = [
    mappings.load_excluded_repositories,
    mappings.load_bot_accounts,
    mappings.load_commit_authors,
    mappings.load_account_aliases,
    mappings.read_organisations,
    mappings.organisation_names,
    mappings.read_overrides,
]


@pytest.mark.parametrize('loader', LOADERS, ids=lambda f: f.__name__)
def test_loader_raises_on_missing_file(loader, tmp_path):
    # A missed path after a move must stop the run, not produce wrong statistics
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        loader(tmp_path / 'missing.csv')


def test_mapping_raises_on_missing_overrides_for_a_year(tmp_path):
    (tmp_path / 'o.csv').write_text('Organisation,Team\nA,x\n', encoding='utf-8')
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        mappings.load_organisation_mapping(tmp_path / 'o.csv', tmp_path / 'missing.csv', year=2024)


def test_read_organisations_splits_teams(tmp_path):
    (tmp_path / 'o.csv').write_text('Organisation,Team\nA,x; y\nB,z\n', encoding='utf-8')
    assert mappings.read_organisations(tmp_path / 'o.csv') == {'x': 'A', 'y': 'A', 'z': 'B'}


def test_read_overrides_keeps_file_order(tmp_path):
    (tmp_path / 'ov.csv').write_text('github_username,organisation,from_year,to_year,source\n'
                                     'x,A,2020,,s\nx,B,2018,2019,s\n', encoding='utf-8')
    assert mappings.read_overrides(tmp_path / 'ov.csv') == [
        {'github_username': 'x', 'organisation': 'A', 'from_year': 2020, 'to_year': None},
        {'github_username': 'x', 'organisation': 'B', 'from_year': 2018, 'to_year': 2019},
    ]


def test_organisation_names_by_lower_case(tmp_path):
    (tmp_path / 'o.csv').write_text('Organisation,Team\nkitconcept GmbH,x\n', encoding='utf-8')
    assert mappings.organisation_names(tmp_path / 'o.csv') == {'kitconcept gmbh': 'kitconcept GmbH'}


def test_paths_are_relative():
    # Scripts run from the repository root; tests chdir into tmp_path and write fixtures there
    for name, value in vars(paths).items():
        if isinstance(value, Path):
            assert not value.is_absolute(), name


def test_paths_point_at_existing_files():
    root = Path(__file__).resolve().parent.parent
    for name, value in vars(paths).items():
        if isinstance(value, Path) and name.isupper():
            assert (root / value).exists(), f'{name}: {value}'
