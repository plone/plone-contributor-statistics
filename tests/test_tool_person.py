import pytest

from scripts.lib import paths
from scripts.lib.addresses import mask_address
from scripts.lib.model import Identity, load_registry, source_id, split_archive_url
from scripts.lib.model.names import unique_slug
from scripts.tools import check, datapackage, person
from tests.conftest import record_source

SRC = 'https://example.org/record'


@pytest.fixture
def registers(tmp_repo):
    sid = record_source(SRC)
    paths.PEOPLE.write_text('id,name\nalan-runyan,Alan Runyan\njane-doe,Jane Doe\nzed,Zed Zeta\n', encoding='utf-8')
    paths.IDENTITIES.write_text(
        'person,kind,value,source,snippet,notes\n'
        f'alan-runyan,github,runyaga,{sid},,\n'
        f'alan-runyan,github-alias,bobdobbs666,{sid},,\n'
        f'jane-doe,github,JaneDoe,{sid},,\n'
        f'zed,email,Zed@Example.org,{sid},,\n'
        f'zed,name,Zed Zeta,{sid},,\n'
        f'zed,name,Zédd Zeta,{sid},,\n', encoding='utf-8')
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
    added, identity = person.add(paths.MAPPINGS_DIR, 'Jane Doe', 'jdoe2', SRC)
    assert added.id == 'jane-doe-2' and (identity.kind, identity.value) == ('github', 'jdoe2')
    assert person.add(paths.MAPPINGS_DIR, 'Abe Able', None, SRC)[0].id == 'abe-able'
    registry = load_registry()
    assert list(registry.people) == ['abe-able', 'alan-runyan', 'jane-doe', 'jane-doe-2', 'zed']
    assert registry.github_of('abe-able') is None
    assert [(i.kind, i.value) for i in registry.identities if i.person == 'abe-able'] == [('name', 'Abe Able')]
    assert registry.github_of('jane-doe-2') == 'jdoe2'
    datapackage.main([])
    assert check.validate() == []


def test_add_refuses_a_login_of_another_person(registers):
    with pytest.raises(ValueError, match='belongs to alan-runyan'):
        person.add(paths.MAPPINGS_DIR, 'Other Alan', 'RUNYAGA', SRC)
    with pytest.raises(ValueError, match='belongs to alan-runyan'):
        person.add(paths.MAPPINGS_DIR, 'Other Alan', 'bobdobbs666', SRC)
    with pytest.raises(ValueError, match='capture it first'):
        person.add(paths.MAPPINGS_DIR, 'New Person', None, 'https://example.org/unknown')
    with pytest.raises(ValueError, match='name'):
        person.add(paths.MAPPINGS_DIR, ' ', None, SRC)
    with pytest.raises(ValueError, match=r'the id or the address of a source in the source register.*'
                                         r'python -m scripts\.tools\.capture'):
        person.add(paths.MAPPINGS_DIR, 'New Person', None, ' ')
    assert 'other-alan' not in load_registry().people


def test_add_finds_the_source_by_its_archived_address(registers):
    archived = 'https://web.archive.org/web/20100125023558/http://example.org/old'
    sid = source_id(*split_archive_url(archived))
    rows = paths.SOURCES.read_text(encoding='utf-8')
    paths.SOURCES.write_text(rows + f'{sid},page,Old,2010-01-25,http://example.org/old,{archived},'
                             '2026-10-22T10:00:00Z,\n', encoding='utf-8')
    (paths.EXCERPTS_DIR / f'{sid}.md').write_text('Old.\n', encoding='utf-8')
    _, identity = person.add(paths.MAPPINGS_DIR, 'Old Timer', None, archived)
    assert identity == Identity('old-timer', 'name', 'Old Timer', sid)
    # The live address is another source than its archived copy
    with pytest.raises(ValueError, match='capture it first'):
        person.add(paths.MAPPINGS_DIR, 'Ann Other', None, 'http://example.org/old')


def test_main_add_prints_the_rows(registers, capsys):
    sid = record_source(SRC)
    assert person.main(['--add', 'Ann Lee', '--github', 'annlee', '--source', sid]) == 0
    assert capsys.readouterr().out == f'ann-lee,Ann Lee\nann-lee,github,annlee,{sid},,\n'


def test_main_find_prints_rows_and_fails_without_match(registers, capsys):
    sid = record_source(SRC)
    assert person.main(['Jane Doe']) == 0
    assert capsys.readouterr().out == (
        '# curated/mappings/people.csv\nid,name\njane-doe,Jane Doe\n'
        f'# curated/mappings/identities.csv\nperson,kind,value,source,snippet,notes\njane-doe,github,JaneDoe,{sid},,\n')
    assert person.main(['nobody']) == 1
    assert capsys.readouterr().out == ''


def test_main_prints_identities_and_affiliations_of_the_match(registers, capsys):
    sid = record_source(SRC)
    paths.AFFILIATIONS.write_text(
        'id,person,organisation,from,to,status,checked,notes\n'
        'a12345678,zed,zeta,2015,,stated,2024-05-01,"one, two"\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text('id,name,kind,github,aliases,notes\nzeta,Zeta,organisation,,,\n', encoding='utf-8')
    assert person.main(['  zed ']) == 0
    assert capsys.readouterr().out == (
        '# curated/mappings/people.csv\n'
        'id,name\n'
        'zed,Zed Zeta\n'
        '# curated/mappings/identities.csv\n'
        'person,kind,value,source,snippet,notes\n'
        f'zed,email,Zed@Example.org,{sid},,\n'
        f'zed,name,Zed Zeta,{sid},,\n'
        f'zed,name,Zédd Zeta,{sid},,\n'
        '# curated/mappings/affiliations.csv\n'
        'id,person,organisation,from,to,status,checked,notes\n'
        'a12345678,zed,zeta,2015,,stated,2024-05-01,"one, two"\n')


@pytest.mark.parametrize('extra', [[], ['--source', '']])
def test_main_add_without_a_source_says_how_to_give_one(registers, capsys, extra):
    with pytest.raises(SystemExit) as exit_info:
        person.main(['--add', 'New Person', *extra])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert 'the id or the address of a source in the source register' in err
    assert 'python -m scripts.tools.capture' in err
    assert 'new-person' not in load_registry().people


def test_find_by_address_matches_the_hash(registers):
    sid = record_source(SRC)
    with paths.IDENTITIES.open('a', encoding='utf-8') as handle:
        handle.write(f'jane-doe,email,{mask_address("jane@acme.test")},{sid},,\n')

    registry = load_registry()

    assert ids(person.find(registry, 'Jane@acme.test')) == ['jane-doe']
    assert ids(person.find(registry, mask_address('jane@acme.test'))) == ['jane-doe']
