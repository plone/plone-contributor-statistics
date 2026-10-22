import pytest

from scripts.lib import paths
from scripts.lib.model import affiliation_id, load_registry
from scripts.tools import affiliation
from tests.conftest import record_source

OLD = affiliation_id('jane-doe', 'old-co', 2010, 2014)
EXAMPLE = affiliation_id('jane-doe', 'example-company', 2015, 2019)
NEW = affiliation_id('jane-doe', 'new-co', 2020, None)


@pytest.fixture
def registry(write_registers):
    write_registers(people=[('jane-doe', 'janedoe'), ('other', '')],
                    affiliations=[('jane-doe', 'old-co', 2010, 2014), ('jane-doe', 'example-company', 2015, 2019),
                                  ('jane-doe', 'new-co', 2020, None)],
                    organisations=[('old-co', 'Old Co'), ('example-company', 'Example Company'),
                                   ('new-co', 'New Co')])
    return load_registry()


def test_the_organisation_of_each_year(registry):
    assert affiliation.organisations(registry, 'jane-doe', [2009, 2014, 2015, 2024]) == [
        '2009: Unmapped', '2014: Old Co', '2015: Example Company', '2024: New Co']


def test_the_years_default_to_those_of_the_rows(registry):
    lines = affiliation.organisations(registry, 'jane-doe', affiliation.years_of(registry, 'jane-doe', until=2021))
    assert lines[0] == '2010: Old Co' and lines[-1] == '2021: New Co' and len(lines) == 12
    assert affiliation.years_of(registry, 'other', until=2021) == []


def test_a_conflict_names_the_organisations(write_registers):
    write_registers(people=[('jane-doe', 'janedoe')],
                    affiliations=[('jane-doe', 'old-co', 2010, 2014), ('jane-doe', 'new-co', 2012, 2013)],
                    organisations=[('old-co', 'Old Co'), ('new-co', 'New Co')])
    assert affiliation.organisations(load_registry(), 'jane-doe', [2011, 2012]) == [
        '2011: Old Co', '2012: Unmapped (no rule decides between New Co, Old Co)']


def test_each_affiliation_with_its_citations(registry):
    sid = record_source()
    other = record_source('https://example.org/other')
    (paths.EXCERPTS_DIR / f'{other}.md').write_text('Jane Doe works at Example Company.\n', encoding='utf-8')
    rows = paths.CITATIONS.read_text(encoding='utf-8').splitlines(keepends=True)
    rows.append(f'{EXAMPLE},{other},Jane Doe works at Example Company,,"cited as: the team page"\n')
    paths.CITATIONS.write_text(rows[0] + ''.join(sorted(rows[1:])), encoding='utf-8')
    lines = affiliation.citations(load_registry(), 'jane-doe')
    assert lines[:3] == [f'{OLD}: Old Co, 2010–2014, stated',
                         f'  {sid} A record, 2026-01-01, https://example.org/record',
                         '    no snippet']
    example = lines[lines.index(f'{EXAMPLE}: Example Company, 2015–2019, stated') + 1:]
    assert example[:5] == [f'  {sid} A record, 2026-01-01, https://example.org/record',
                           '    no snippet',
                           f'  {other} A record, 2026-01-01, https://example.org/other',
                           '    "Jane Doe works at Example Company"',
                           '    notes: cited as: the team page']
    assert f'{NEW}: New Co, 2020–present, stated' in lines


def test_an_affiliation_without_citation_says_so(registry):
    paths.CITATIONS.write_text('affiliation,source,snippet,supersedes,notes\n', encoding='utf-8')
    assert affiliation.citations(load_registry(), 'jane-doe')[:2] == [f'{OLD}: Old Co, 2010–2014, stated',
                                                                      '  no citation']


def test_the_person_by_login_or_username(registry):
    assert affiliation.person_id(registry, 'JaneDoe') == 'jane-doe'
    assert affiliation.person_id(registry, 'person:other') == 'other'
    assert affiliation.person_id(registry, 'jane-doe') == 'jane-doe'
    for unknown in ('nobody', 'person:nobody'):
        with pytest.raises(ValueError, match=unknown):
            affiliation.person_id(registry, unknown)


def test_main_prints_years_and_citations(registry, capsys):
    assert affiliation.main(['janedoe', '2017']) == 0
    out = capsys.readouterr().out
    assert out.startswith('jane-doe (jane-doe)\n\n2017: Example Company\n\n')
    assert f'{EXAMPLE}: Example Company, 2015–2019, stated' in out
    assert affiliation.main(['other', '2017']) == 0
    assert capsys.readouterr().out == 'other (other)\n\n2017: Unmapped\n\nNo affiliations.\n'
    with pytest.raises(SystemExit) as exit_info:
        affiliation.main(['nobody'])
    assert exit_info.value.code == 2
