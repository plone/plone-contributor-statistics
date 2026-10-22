import pytest

from scripts.lib.model import affiliation_id, load_registry
from scripts.tools import affiliation


@pytest.fixture
def registry(write_registers):
    write_registers(people=[('jane-doe', 'janedoe'), ('other', '')],
                    affiliations=[('jane-doe', 'old-co', 2010, 2014), ('jane-doe', 'example-company', 2015, 2019),
                                  ('jane-doe', 'new-co', 2020, None)],
                    organisations=[('old-co', 'Old Co'), ('example-company', 'Example Company'),
                                   ('new-co', 'New Co')])
    return load_registry()


def test_explain_names_the_row(registry):
    assert affiliation.explain(registry, 'jane-doe', 2017) == (
        'Example Company (affiliations.csv line 3: 2015–2019, stated, '
        f'{affiliation_id("jane-doe", "example-company", 2015, 2019)})')
    assert affiliation.explain(registry, 'jane-doe', 2024) == (
        f'New Co (affiliations.csv line 4: 2020–present, stated, {affiliation_id("jane-doe", "new-co", 2020, None)})')


def test_explain_takes_a_login_or_a_username(registry):
    expected = affiliation.explain(registry, 'jane-doe', 2017)
    assert affiliation.explain(registry, 'JaneDoe', 2017) == expected
    assert affiliation.explain(registry, 'person:jane-doe', 2017) == expected
    assert affiliation.explain(registry, 'person:other', 2017) == 'Unmapped (no row covers 2017)'
    with pytest.raises(ValueError, match='person:nobody'):
        affiliation.explain(registry, 'person:nobody', 2017)


def test_explain_unmapped_when_no_row_covers(registry):
    assert affiliation.explain(registry, 'jane-doe', 2005) == 'Unmapped (no row covers 2005)'
    assert affiliation.explain(registry, 'other', 2017) == 'Unmapped (no row covers 2017)'


def test_unknown_person_is_an_error(registry):
    with pytest.raises(ValueError, match='nobody'):
        affiliation.explain(registry, 'nobody', 2017)
    with pytest.raises(SystemExit) as exit_info:
        affiliation.main(['nobody', '2017'])
    assert exit_info.value.code == 2


def test_main_prints_the_explanation(registry, capsys):
    assert affiliation.main(['jane-doe', '2017']) == 0
    assert capsys.readouterr().out.startswith('Example Company (')
    assert affiliation.main(['other', '2017']) == 0
    assert capsys.readouterr().out.strip() == 'Unmapped (no row covers 2017)'
