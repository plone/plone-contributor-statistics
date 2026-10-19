"""The registers: typed reading through the schema, and the lookups of the Registry."""

import datetime
import shutil
from pathlib import Path

import pytest

from scripts.lib import paths
from scripts.lib.model import UNMAPPED, load_registry, read_rows

REPO = Path(__file__).resolve().parent.parent
SRC = 'https://example.org/record'

PEOPLE = f"""id,name,github,source
philip-bauer,Philip Bauer,pbauer,{SRC}
alan-runyan,Alan Runyan,runyaga,{SRC}
thomas-schorr,Thomas Schorr,,{SRC}
kim-a,Kim A,kima,{SRC}
kim-b,Kim B,kimb,{SRC}
"""

IDENTITIES = f"""person,kind,value,source
alan-runyan,login,bobdobbs666,{SRC}
alan-runyan,email,Alan@Example.org,{SRC}
kim-a,name,Kim,{SRC}
kim-b,name,Kim,{SRC}
thomas-schorr,name,Tom Schorr,{SRC}
"""

AFFILIATIONS = f"""person,organisation,from,to,source,checked,notes
philip-bauer,starzel,2010,,{SRC},2026-01-01,
alan-runyan,enfold,2004,2008,{SRC},,
kim-a,syslab,2019,,{SRC},,
thomas-schorr,thomas-schorr-independent,2015,,{SRC},,
"""

ORGANISATIONS = """id,name,kind,aliases,notes
starzel,Starzel,organisation,Starzel GmbH;Starzel Gmbh,
syslab,Syslab,organisation,,
enfold,Enfold,organisation,,
thomas-schorr-independent,Thomas Schorr (independent),independent,,
plone-foundation,Plone Foundation,foundation,,
"""


@pytest.fixture
def schemas(tmp_repo):
    shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
    return tmp_repo


@pytest.fixture
def registry(schemas):
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


def test_read_rows_types(schemas):
    paths.AFFILIATIONS.write_text(AFFILIATIONS, encoding='utf-8')
    rows = read_rows(paths.AFFILIATIONS)
    assert rows[0]['from'] == 2010 and isinstance(rows[0]['from'], int)
    assert rows[0]['to'] is None
    assert rows[0]['checked'] == datetime.date(2026, 1, 1)
    assert rows[0]['notes'] is None


def test_read_rows_missing_file(schemas):
    with pytest.raises(FileNotFoundError):
        read_rows(paths.PEOPLE)
