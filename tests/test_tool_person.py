import pytest

from scripts.lib import paths
from scripts.lib.model import Person, append_person, load_registry
from scripts.lib.model.names import unique_slug
from scripts.tools import check, datapackage, person

SRC = 'https://example.org/record'


@pytest.fixture
def registers(tmp_repo):
    paths.PEOPLE.write_text(
        'id,name,github,source\n'
        f'alan-runyan,Alan Runyan,runyaga,{SRC}\n'
        f'jane-doe,Jane Doe,JaneDoe,{SRC}\n'
        f'zed,Zed Zeta,,{SRC}\n', encoding='utf-8')
    paths.IDENTITIES.write_text(
        'person,kind,value,source\n'
        f'alan-runyan,login,bobdobbs666,{SRC}\n'
        f'zed,email,Zed@Example.org,{SRC}\n'
        f'zed,name,Zédd Zeta,{SRC}\n', encoding='utf-8')
    return tmp_repo


def ids(people):
    return [p.id for p in people]


def test_unique_slug_numbers_collisions():
    assert unique_slug('Jane Doe', set()) == 'jane-doe'
    assert unique_slug('Jane Doe', {'jane-doe', 'jane-doe-2'}) == 'jane-doe-3'
    with pytest.raises(ValueError):
        unique_slug('???', set())


def test_find_by_identity_name(registers):
    registry = load_registry()
    assert ids(person.find(registry, 'zedd zeta')) == ['zed']
    assert ids(person.find(registry, 'Jane  DOE')) == ['jane-doe']
    assert ids(person.find(registry, 'zed')) == ['zed']  # the id
    assert ids(person.find(registry, 'ZED@example.org')) == ['zed']
    assert ids(person.find(registry, 'bobdobbs666')) == ['alan-runyan']
    assert person.find(registry, 'nobody') == []


def test_find_by_login_ignores_case(registers):
    assert ids(person.find(load_registry(), 'janedoe')) == ['jane-doe']


def test_add_generates_unique_id_and_keeps_sort(registers):
    added = person.add(paths.MAPPINGS_DIR, 'Jane Doe', 'jdoe2', SRC)
    assert added.id == 'jane-doe-2'
    assert person.add(paths.MAPPINGS_DIR, 'Abe Able', None, SRC).id == 'abe-able'
    registry = load_registry()
    assert list(registry.people) == ['abe-able', 'alan-runyan', 'jane-doe', 'jane-doe-2', 'zed']
    assert registry.people['abe-able'].github is None
    assert registry.people['jane-doe-2'].github == 'jdoe2'
    datapackage.main([])
    assert check.validate() == []


def test_add_refuses_a_login_of_another_person(registers):
    with pytest.raises(ValueError, match='belongs to alan-runyan'):
        person.add(paths.MAPPINGS_DIR, 'Other Alan', 'RUNYAGA', SRC)
    with pytest.raises(ValueError, match='belongs to alan-runyan'):
        person.add(paths.MAPPINGS_DIR, 'Other Alan', 'bobdobbs666', SRC)
    with pytest.raises(ValueError, match='link'):
        person.add(paths.MAPPINGS_DIR, 'New Person', None, 'memory')
    with pytest.raises(ValueError, match='name'):
        person.add(paths.MAPPINGS_DIR, ' ', None, SRC)
    assert 'other-alan' not in load_registry().people


def test_main_add_prints_the_row(registers, capsys):
    assert person.main(['--add', 'Ann Lee', '--github', 'annlee', '--source', SRC]) == 0
    assert capsys.readouterr().out.strip() == f'ann-lee,Ann Lee,annlee,{SRC}'


def test_main_find_prints_rows_and_fails_without_match(registers, capsys):
    assert person.main(['Jane Doe']) == 0
    assert capsys.readouterr().out == (
        f'# curated/mappings/people.csv\nid,name,github,source\njane-doe,Jane Doe,JaneDoe,{SRC}\n')
    assert person.main(['nobody']) == 1
    assert capsys.readouterr().out == ''


def test_main_prints_identities_and_affiliations_of_the_match(registers, capsys):
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'zed,zeta,2015,,{SRC},2024-05-01,"one, two"\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text('id,name,kind,aliases,notes\nzeta,Zeta,organisation,,\n', encoding='utf-8')
    assert person.main(['  zed ']) == 0
    assert capsys.readouterr().out == (
        '# curated/mappings/people.csv\n'
        'id,name,github,source\n'
        f'zed,Zed Zeta,,{SRC}\n'
        '# curated/mappings/identities.csv\n'
        'person,kind,value,source\n'
        f'zed,email,Zed@Example.org,{SRC}\n'
        f'zed,name,Zédd Zeta,{SRC}\n'
        '# curated/mappings/affiliations.csv\n'
        'person,organisation,from,to,source,checked,notes\n'
        f'zed,zeta,2015,,{SRC},2024-05-01,"one, two"\n')


def test_append_person_refuses_an_existing_id_or_login(registers):
    with pytest.raises(ValueError, match='id zed'):
        append_person(paths.MAPPINGS_DIR, Person('zed', 'Another', None, SRC))
    with pytest.raises(ValueError, match='login JANEDOE'):
        append_person(paths.MAPPINGS_DIR, Person('new', 'New', 'JANEDOE', SRC))
    assert 'new' not in load_registry().people
