import shutil
from pathlib import Path

import pytest

from scripts.lib.model.names import fold, slugify
from scripts.tools import check, datapackage

REPO = Path(__file__).resolve().parent.parent
TRAININGS = 'community-contributions/2023-plone-conference-trainings.csv'
PEOPLE = (
    'id,name,github,source\n'
    'pbauer,Philip Bauer,pbauer,https://github.com/pbauer\n'
    'tschorr,Timo Stollenwerk,tschorr,https://github.com/tschorr\n'
)


@pytest.fixture
def tmp_package(tmp_repo):
    """Write the given register files under curated/ and the data package that describes them."""

    def build(files):
        shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
        for relative, text in files.items():
            target = tmp_repo / 'curated' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        datapackage.main([])
        return tmp_repo

    return build


def trainings(trainers):
    return {
        'mappings/people.csv': PEOPLE,
        TRAININGS: f'title,trainers,source,notes\nPlone 6,{trainers},https://example.org/t,\n',
    }


def test_fold_and_slugify():
    assert fold('Ecréall ') == fold('ecreall')
    assert slugify('Víctor Fernández de Alba') == 'victor-fernandez-de-alba'


def test_set_keys_rejects_empty_element(tmp_package):
    root = tmp_package(trainings('pbauer;;tschorr'))
    errors = check.validate(root)
    assert len(errors) == 1
    file, row, field, message = errors[0]
    assert (file, row, field) == ('curated/' + TRAININGS, 2, 'trainers')


def test_set_keys_rejects_unknown_key(tmp_package):
    errors = check.validate(tmp_package(trainings('pbauer;nobody')))
    assert len(errors) == 1
    assert 'nobody' in errors[0][3]


def test_affiliation_overlap_names_both_rows(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': PEOPLE,
            'mappings/organisations.csv': 'id,name,kind,aliases,notes\nacme,Acme,organisation,,\n',
            'mappings/affiliations.csv': (
                'person,organisation,from,to,source,checked,notes\n'
                'pbauer,acme,2010,2016,https://example.org/a,,\n'
                'pbauer,acme,2016,,https://example.org/b,,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert '2' in errors[0][3] and '3' in errors[0][3]


def test_name_fold_rejects_near_duplicate(tmp_package):
    root = tmp_package(
        {
            'mappings/organisations.csv': (
                'id,name,kind,aliases,notes\necreall,Ecréall,organisation,,\necreall-2,Ecreall,organisation,,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert 'Ecreall' in errors[0][3]
    assert errors[0][1] == 3


def test_check_main_prints_file_row_field(tmp_package, capsys):
    tmp_package(trainings('pbauer;;tschorr'))
    with pytest.raises(SystemExit) as exit_info:
        check.main([])
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert out.startswith('curated/community-contributions/2023-plone-conference-trainings.csv:2:trainers:')


def test_check_hints_nearest_ids(tmp_package, capsys):
    tmp_package(trainings('pbauer;pbaur'))
    with pytest.raises(SystemExit):
        check.main([])
    out = capsys.readouterr().out
    assert 'nearest:' in out and 'pbauer' in out.split('nearest:')[1]


def test_foreign_key_error_hints_nearest_ids(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': PEOPLE,
            'mappings/organisations.csv': 'id,name,kind,aliases,notes\nacme,Acme,organisation,,\n',
            'mappings/affiliations.csv': (
                'person,organisation,from,to,source,checked,notes\npbaur,acme,2010,2016,https://example.org/a,,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert errors[0][1] == 2
    assert errors[0][3].endswith('nearest: pbauer')


def test_sorted_unique_github_and_identity_link(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': (
                'id,name,github,source\nb,B,Same,https://example.org/b\na,A,same,https://example.org/a\n'
            ),
            'mappings/identities.csv': (
                'person,kind,value,source\na,email,a@example.org,\na,website,https://a.example.org,not a link\n'
            ),
        }
    )
    found = [(file.rsplit('/', 1)[1], row) for file, row, _, _ in check.validate(root)]
    assert found.count(('people.csv', 3)) == 2  # not sorted, and the login repeats
    assert found.count(('identities.csv', 3)) >= 1
    assert ('identities.csv', 2) not in found  # an email needs no link


def test_identity_link_may_follow_text(tmp_package):
    # As in every other source column, the link may come after the words that say what it shows
    root = tmp_package(
        {
            'mappings/people.csv': 'id,name,github,source\na,A,a,https://example.org/a\n',
            'mappings/identities.csv': 'person,kind,value,source\na,name,A B,example commit: https://example.org/c\n',
        }
    )
    assert check.validate(root) == []


def test_check_clean_prints_nothing(tmp_package, capsys):
    tmp_package(trainings('pbauer;tschorr'))
    check.main([])
    assert capsys.readouterr().out == ''
