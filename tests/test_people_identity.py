"""One identity per person across code and community work (community page, #117)."""

from collections import namedtuple

from scripts.lib import people

Row = namedtuple('Row', 'person handle source')


def index(rows, tmp_path, authors='email,github_username,name,source\n', fullnames='github username,fullname\n'):
    (tmp_path / 'authors.csv').write_text(authors, encoding='utf-8')
    (tmp_path / 'fullnames.csv').write_text(fullnames, encoding='utf-8')
    return people.build_person_index(rows, tmp_path / 'authors.csv', tmp_path / 'fullnames.csv')


def test_normalise_ignores_case_and_accents():
    assert people.normalise('  Víctor   Fernández ') == 'victor fernandez'


def test_groups_are_not_people():
    organisations = {'RedTurtle'}
    for name in ['PloneGov-BR team', 'Klein & Partner KG;BlueDynamics Alliance', 'RedTurtle']:
        assert people.is_group(name, organisations), name
    assert not people.is_group('Mauro Amico', organisations)


def test_handle_and_source_link_resolve_to_the_same_login(tmp_path):
    # Review focus: one login counts once, wherever it comes from
    rows = [Row('David Glick', 'davisagli', ''),
            Row('David Glick', '', 'https://community.plone.org/t/1; organisation from the organisation mapping: '
                                  'https://github.com/davisagli')]
    found = index(rows, tmp_path)
    assert found.key('David Glick') == found.key('', 'davisagli') == 'davisagli'


def test_links_to_commits_are_not_logins(tmp_path):
    found = index([Row('Jane Doe', '', 'https://github.com/plone/plone.testing/commit/1234')], tmp_path)
    assert found.key('Jane Doe') == 'name:jane doe'


def test_commit_authors_and_fullnames_give_logins(tmp_path):
    found = index([], tmp_path, authors='email,github_username,name,source\na@b,alecm,Alec Mitchell,x\n',
                  fullnames='github username,fullname\npbauer,Philip Bauer\n')
    assert found.key('Alec Mitchell') == 'alecm'
    assert found.key('philip bauer') == 'pbauer'


def test_ambiguous_name_maps_to_no_login(tmp_path):
    found = index([Row('Jane Doe', 'jane1', ''), Row('Jane Doe', 'jane2', '')], tmp_path)
    assert found.key('Jane Doe') == 'name:jane doe'


def test_unknown_and_empty_names(tmp_path):
    found = index([], tmp_path)
    assert found.key('Jane  Doe') == 'name:jane doe'
    assert found.key('') is None


def test_logins_ignore_case(tmp_path):
    found = index([Row('David Glick', 'DavisAgli', ''), Row('David Glick', 'davisagli', '')], tmp_path)
    assert found.key('David Glick') == found.key('', 'davisagli') == 'davisagli'
