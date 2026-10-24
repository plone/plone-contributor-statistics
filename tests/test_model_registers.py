"""The registers: typed reading through the schema, and the lookups of the Registry."""

import datetime

import pytest

from scripts.lib import paths
from scripts.lib.model import (UNMAPPED, affiliation_id, append_person, append_proposals, load_registry,
                               load_rejections, read_rows)
from scripts.lib.model.registers import Identity, Person
from tests.conftest import record_source

SRC = 'https://example.org/record'
SID = '0123456789ab'  # a source id; the registers are read without following it

PEOPLE = """id,name
alan-runyan,Alan Runyan
kim-a,Kim A
kim-b,Kim B
philip-bauer,Philip Bauer
thomas-schorr,Thomas Schorr
"""

IDENTITIES = f"""person,kind,value,source,snippet,notes
alan-runyan,email,Alan@Example.org,{SID},,
alan-runyan,github,runyaga,{SID},,
alan-runyan,github-alias,bobdobbs666,{SID},,
kim-a,github,kima,{SID},,
kim-a,name,Kim,{SID},,
kim-b,github,kimb,{SID},,
kim-b,name,Kim,{SID},,
philip-bauer,github,pbauer,{SID},,
thomas-schorr,name,Thomas Schorr,{SID},,
thomas-schorr,name,Tom Schorr,{SID},,
"""

AFFILIATIONS = """id,person,organisation,from,to,status,checked,notes
a00000001,alan-runyan,enfold,2004,2008,stated,,
a00000002,kim-a,syslab,2019,,stated,,
a00000003,philip-bauer,starzel,2010,,stated,2026-01-01,
a00000004,thomas-schorr,thomas-schorr-independent,2015,,stated,,
"""

ORGANISATIONS = """id,name,kind,github,aliases,notes
starzel,Starzel,organisation,,Starzel GmbH;Starzel Gmbh,
syslab,Syslab,organisation,,,
enfold,Enfold,organisation,,,
thomas-schorr-independent,Thomas Schorr (independent),independent,,,
plone-foundation,Plone Foundation,foundation,,,
"""


@pytest.fixture
def registry(tmp_repo):
    paths.PEOPLE.write_text(PEOPLE, encoding='utf-8')
    paths.IDENTITIES.write_text(IDENTITIES, encoding='utf-8')
    paths.AFFILIATIONS.write_text(AFFILIATIONS, encoding='utf-8')
    paths.ORGANISATIONS.write_text(ORGANISATIONS, encoding='utf-8')
    return load_registry()


def test_person_for_login_ignores_case(registry):
    assert registry.person_for(login='PBauer').id == 'philip-bauer'


def test_person_for_second_account(registry):
    assert registry.person_for(login='bobdobbs666').id == 'alan-runyan'


def test_person_for_name_is_none_when_ambiguous(registry):
    assert registry.person_for(name='Kim') is None
    assert registry.person_for(name='tom schorr').id == 'thomas-schorr'
    assert registry.person_for(email='alan@example.ORG').id == 'alan-runyan'


def test_a_display_name_of_one_word_matches_no_name(tmp_repo):
    paths.PEOPLE.write_text('id,name\ncillian-de-roiste,goibhniu\ndanny,Danny\njens-klein,Jens Klein\n'
                            'rodrigo-ristow,Rodrigo\n', encoding='utf-8')
    paths.IDENTITIES.write_text(f'person,kind,value,source,snippet,notes\n'
                                f'cillian-de-roiste,github,cillianderoiste,{SID},,\n'
                                f'danny,name,Danny,{SID},,\n'
                                f'jens-klein,github,jensens,{SID},,\n'
                                f'jens-klein,name,yenzens,{SID},,\n'
                                f'rodrigo-ristow,github,rristow,{SID},,\n', encoding='utf-8')
    registry = load_registry()
    # The changelog names "goibhniu" and "rodrigo" are not evidence for these people
    assert registry.person_for(name='goibhniu') is None
    assert registry.person_for(name='rodrigo') is None
    # Nor is the name identity that records the one-word display name of a person without GitHub
    assert registry.person_for(name='danny') is None
    # A display name of several words, and a name identity of any length, still match
    assert registry.person_for(name='jens  klein').id == 'jens-klein'
    assert registry.person_for(name='Yenzens').id == 'jens-klein'


def test_organisation_of_without_affiliation_is_unmapped(registry):
    assert registry.organisation_of('philip-bauer', 2009) == UNMAPPED
    assert registry.organisation_of('alan-runyan', 2003) == UNMAPPED


def test_organisation_of_open_range(registry):
    assert registry.organisation_of('kim-a', 2026) == 'Syslab'
    assert registry.organisation_of('alan-runyan', 2008) == 'Enfold'
    assert registry.organisation_of('alan-runyan', 2009) == UNMAPPED


def test_login_organisations_omits_logins_without_affiliation(registry):
    assert registry.login_organisations(2005) == {'bobdobbs666': 'Enfold', 'runyaga': 'Enfold'}
    assert registry.login_organisations(2020) == {'pbauer': 'Starzel', 'kima': 'Syslab'}


def test_organisation_for_username_person_prefix(registry):
    assert registry.organisation_for_username('person:alan-runyan', 2004) == 'Enfold'
    assert registry.organisation_for_username('PBauer', 2012) == 'Starzel'
    assert registry.organisation_for_username('stranger', 2012) == UNMAPPED


def test_is_counted_organisation(registry):
    assert registry.is_counted_organisation('Starzel')
    assert not registry.is_counted_organisation('Thomas Schorr (independent)')
    assert not registry.is_counted_organisation('Plone Foundation')
    assert not registry.is_counted_organisation(UNMAPPED)


def test_organisation_names_and_display_names(registry):
    assert registry.organisation_id('starzel gmbh') == 'starzel'
    assert registry.organisation_id('Nobody') is None
    assert registry.organisation_name('enfold') == 'Enfold'
    assert registry.display_name('person:thomas-schorr') == 'Thomas Schorr'
    assert registry.display_name('bobdobbs666') == 'Alan Runyan'
    assert registry.display_name('stranger') == 'stranger'


def test_read_rows_types(tmp_repo):
    paths.AFFILIATIONS.write_text(AFFILIATIONS, encoding='utf-8')
    rows = read_rows(paths.AFFILIATIONS)
    assert rows[2]['from'] == 2010 and isinstance(rows[2]['from'], int)
    assert rows[2]['to'] is None
    assert rows[2]['checked'] == datetime.date(2026, 1, 1)
    assert rows[2]['notes'] is None


def test_read_rows_does_not_guess_the_delimiter(tmp_repo):
    # A quotation between semicolons once made Frictionless read a comma separated file as semicolon separated
    path = paths.COMMUNITY / '2007-plone-conference-trainings.csv'
    path.write_text(f'title,trainers,source,notes\nPlone 3,joel-burton,{SRC},"paid; ""offered by vendors.""; guest"\n',
                    encoding='utf-8')
    assert [row['trainers'] for row in read_rows(path)] == ['joel-burton']


def test_read_rows_missing_file(tmp_repo):
    paths.PEOPLE.unlink()
    with pytest.raises(FileNotFoundError):
        read_rows(paths.PEOPLE)


def test_read_rows_raises_on_malformed_cell(tmp_repo):
    paths.AFFILIATIONS.write_text(AFFILIATIONS.replace('alan-runyan,enfold,2004,2008', 'alan-runyan,enfold,2004,20l5'),
                                  encoding='utf-8')
    with pytest.raises(ValueError) as error:
        read_rows(paths.AFFILIATIONS)
    message = str(error.value)
    assert 'affiliations.csv' in message and 'row 2' in message and 'field to' in message


def test_login_organisations_omits_ambiguous_login(tmp_repo):
    paths.PEOPLE.write_text('id,name\np1,P One\np2,P Two\n', encoding='utf-8')
    paths.IDENTITIES.write_text(f'person,kind,value,source,snippet,notes\np1,github,k1,{SID},,\n'
                                f'p2,github-alias,K1,{SID},,\n', encoding='utf-8')
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n'
                                  'a00000001,p1,starzel,2010,,stated,,\na00000002,p2,syslab,2010,,stated,,\n',
                                  encoding='utf-8')
    paths.ORGANISATIONS.write_text(ORGANISATIONS, encoding='utf-8')
    registry = load_registry()
    assert registry.person_for(login='k1') is None
    assert registry.login_organisations(2020) == {}


def test_github_and_further_accounts(registry):
    assert registry.github_of('alan-runyan') == 'runyaga'
    assert registry.logins_of('alan-runyan') == ['runyaga', 'bobdobbs666']
    assert registry.github_of('thomas-schorr') is None and registry.logins_of('thomas-schorr') == []
    assert registry.username_of(registry.people['alan-runyan']) == 'runyaga'
    assert registry.username_of(registry.people['thomas-schorr']) == 'person:thomas-schorr'


def test_a_person_with_only_a_further_account_counts_under_the_person_id(tmp_repo):
    paths.PEOPLE.write_text('id,name\np1,P One\n', encoding='utf-8')
    paths.IDENTITIES.write_text(f'person,kind,value,source,snippet,notes\np1,github-alias,p1-old,{SID},,\n',
                                encoding='utf-8')
    registry = load_registry()
    assert registry.username_of(registry.people['p1']) == 'person:p1'
    assert registry.person_for(login='P1-OLD').id == 'p1'


def test_organisation_of_follows_the_attribution_rules(tmp_repo):
    sid = record_source()
    paths.PEOPLE.write_text('id,name\np1,P One\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text('id,name,kind,github,aliases,notes\nacme,Acme,organisation,,,\n'
                                   'zeta,Zeta,organisation,,,\n', encoding='utf-8')
    # Overlapping rows: the stated one wins over the assumed one; a denial removes its organisation
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n'
                                  'a00000001,p1,acme,2010,2015,assumed,,\n'
                                  'a00000002,p1,zeta,2012,2013,stated,,\n'
                                  'a00000003,p1,acme,2015,2015,denied,,an old mailbox\n'
                                  'a00000004,p1,zeta,2016,2016,proposed,,\n', encoding='utf-8')
    paths.CITATIONS.write_text('affiliation,source,snippet,supersedes,notes\n' + ''.join(
        f'a0000000{n},{sid},,,\n' for n in range(1, 5)), encoding='utf-8')
    registry = load_registry()
    assert [registry.organisation_of('p1', year) for year in range(2010, 2017)] == [
        'Acme', 'Acme', 'Zeta', 'Zeta', 'Acme', UNMAPPED, UNMAPPED]


def test_citations_and_sources_are_read_on_the_first_organisation(tmp_repo):
    paths.PEOPLE.write_text('id,name\np1,P One\n', encoding='utf-8')
    paths.CITATIONS.unlink()  # a collector that asks for no organisation never needs it
    registry = load_registry()
    assert registry.person_for(name='p one').id == 'p1'
    with pytest.raises(FileNotFoundError):
        registry.organisation_of('p1', 2020)


def test_load_rejections_are_the_denied_rows(tmp_repo):
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n'
                                  'a00000001,p1,acme,2010,2011,denied,,a client\n'
                                  'a00000002,p1,zeta,2010,2011,stated,,\n', encoding='utf-8')
    assert load_rejections() == {('p1', 'acme', 2010), ('p1', 'acme', 2011)}


def test_append_proposals_adds_proposed_rows_with_their_citations(write_registers):
    from scripts.tools import check, datapackage

    write_registers(people=[('jane', 'jane'), ('zoe', 'zoe')], affiliations=[('zoe', 'acme', 2010, 2012)],
                    organisations=[('acme', 'Acme'), ('beta', 'Beta')])
    sid = record_source()
    other = record_source('https://example.org/other')
    (paths.EXCERPTS_DIR / f'{other}.md').write_text('Jane works at Beta.\n', encoding='utf-8')
    rows = [{'person': 'zoe', 'organisation': 'acme', 'from': 2010, 'to': 2012, 'sources': [(sid, '')]},
            {'person': 'jane', 'organisation': 'beta', 'from': 2019, 'to': 2020,
             'sources': [(other, 'Jane works at Beta.'), (sid, None)]}]
    assert append_proposals(rows) == rows[1:]  # zoe's row is in the register already
    assert append_proposals(rows) == []
    aid = affiliation_id('jane', 'beta', 2019, 2020)
    assert [(r['id'], r['person'], r['status']) for r in read_rows(paths.AFFILIATIONS)] == [
        (aid, 'jane', 'proposed'), (affiliation_id('zoe', 'acme', 2010, 2012), 'zoe', 'stated')]
    assert [(r['affiliation'], r['source'], r['snippet']) for r in read_rows(paths.CITATIONS)
            if r['affiliation'] == aid] == sorted([(aid, other, 'Jane works at Beta.'), (aid, sid, None)],
                                                  key=lambda c: (c[0], c[1], c[2] or ''))
    # A proposal never counts
    assert load_registry().organisation_of('jane', 2019) == UNMAPPED
    datapackage.main([])
    assert check.validate() == []


def test_append_person_adds_the_person_and_the_identity(tmp_repo):
    sid = record_source()
    append_person(paths.MAPPINGS_DIR, Person('zed', 'Zed Zeta'), Identity('zed', 'github', 'ZedZ', sid))
    append_person(paths.MAPPINGS_DIR, Person('abe', 'Abe Able'), Identity('abe', 'name', 'Abe Able', sid))
    registry = load_registry()
    assert list(registry.people) == ['abe', 'zed']
    assert registry.github_of('zed') == 'ZedZ' and registry.github_of('abe') is None
    with pytest.raises(ValueError, match='id zed'):
        append_person(paths.MAPPINGS_DIR, Person('zed', 'Another'), Identity('zed', 'name', 'Another', sid))
    with pytest.raises(ValueError, match='login zedz'):
        append_person(paths.MAPPINGS_DIR, Person('new', 'New'), Identity('new', 'github', 'zedz', sid))
    assert 'new' not in load_registry().people


@pytest.mark.parametrize('kind,value', [('github', 'ZEDZ'), ('github-alias', 'zedz'), ('email', 'ZED@example.org')])
def test_append_person_refuses_a_login_or_an_address_of_another_person(tmp_repo, kind, value):
    sid = record_source()
    paths.IDENTITIES.write_text('person,kind,value,source,snippet,notes\n'
                                f'zed,email,zed@example.org,{sid},,\nzed,github,ZedZ,{sid},,\n', encoding='utf-8')
    paths.PEOPLE.write_text('id,name\nzed,Zed Zeta\n', encoding='utf-8')
    with pytest.raises(ValueError, match='exists already'):
        append_person(paths.MAPPINGS_DIR, Person('new', 'New'), Identity('new', kind, value, sid))
    assert list(load_registry().people) == ['zed']


def test_append_person_allows_a_homonym(tmp_repo):
    sid = record_source()
    append_person(paths.MAPPINGS_DIR, Person('kim-a', 'Kim Lee'), Identity('kim-a', 'name', 'Kim Lee', sid))
    append_person(paths.MAPPINGS_DIR, Person('kim-b', 'Kim Lee'), Identity('kim-b', 'name', 'Kim Lee', sid))
    registry = load_registry()
    assert [(i.person, i.value) for i in registry.identities] == [('kim-a', 'Kim Lee'), ('kim-b', 'Kim Lee')]
    assert registry.person_for(name='Kim Lee') is None  # ambiguous


def test_append_proposals_refuses_an_existing_id(write_registers):
    write_registers(people=[('jane', 'jane')], affiliations=[('jane', 'acme', 2010, 2012)],
                    organisations=[('acme', 'Acme')])
    sid = record_source()
    # The row of 2010-2012 was changed to end in 2013 later: its id stays, and the proposal would reuse it
    rows = paths.AFFILIATIONS.read_text(encoding='utf-8')
    paths.AFFILIATIONS.write_text(rows.replace(',2012,stated', ',2013,stated'), encoding='utf-8')
    before = paths.AFFILIATIONS.read_text(encoding='utf-8')
    with pytest.raises(ValueError, match=affiliation_id('jane', 'acme', 2010, 2012)):
        append_proposals([{'person': 'jane', 'organisation': 'acme', 'from': 2010, 'to': 2012,
                           'sources': [(sid, None)]}])
    assert paths.AFFILIATIONS.read_text(encoding='utf-8') == before


def test_write_citations_sorts_the_rows(tmp_repo):
    from scripts.lib.model import Citation, load_citations, write_citations

    rows = [Citation('a00000002', SID, 'b snippet', None, 'notes, with a comma'),
            Citation('a00000001', SID, 'z snippet', None, None),
            Citation('a00000002', SID, None, None, 'cited as: "a quote"'),
            Citation('a00000001', SID, 'a snippet', 'abcdefabcdef', None)]
    write_citations(rows)
    assert load_citations() == [rows[3], rows[1], rows[2], rows[0]]
    assert paths.CITATIONS.read_text(encoding='utf-8').splitlines()[0] == 'affiliation,source,snippet,supersedes,notes'


def test_write_identities_sorts_the_rows(tmp_repo):
    from scripts.lib.model import load_identities, write_identities

    rows = [Identity('zoe', 'name', 'Zoe', SID, 'Zoe works', None),
            Identity('alan', 'github', 'runyaga', SID, None, 'https://github.com/runyaga'),
            Identity('alan', 'email', 'alan@example.org', None, None, None)]
    write_identities(rows)
    assert load_identities() == [rows[2], rows[1], rows[0]]


def test_the_writers_replace_the_file_atomically(tmp_repo, monkeypatch):
    from scripts.lib.model import Citation, load_citations, write_citations
    from scripts.lib.model import registers

    before = [Citation('a00000001', SID, None, None, None)]
    write_citations(before)

    def broken(path, text):
        raise OSError('disk full')
    monkeypatch.setattr(registers, 'write_atomic', broken)
    with pytest.raises(OSError):
        write_citations([Citation('a00000002', SID, None, None, None)])
    assert load_citations() == before
