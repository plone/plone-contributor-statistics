"""Dating, deduplication, name mapping and credit of changelog entries (#71)."""

import pytest

from scripts.collect import plone_changelogs
from scripts.lib import changelogs
from scripts.lib.changelogs import NameMapper, Occurrence, deduplicate
from scripts.lib.model import Identity
from tests.conftest import registry_of


def occurrence(text, release_date='2010-05-04', repository='plone.app.x', branch='master', default=True,
               path='CHANGES.rst', line=1):
    names, variant = changelogs.extract_names(text)
    return Occurrence(repository=repository, path=path, branch=branch, default=default, commit='abc', line=line,
                      text=text, release_date=release_date, date_source='header', names=names, variant=variant)


# Dating


def entries_of(text, tags=None):
    return changelogs.occurrences_in_file('plone.app.x', 'CHANGES.rst', 'master', True, 'abc', text, tags or {})


def test_an_entry_is_dated_by_its_release_header():
    found = entries_of('1.0 (2009-12-01)\n----------------\n\n- Initial release [hannosch]\n', {'1.0': '2009-11-30'})

    assert [(o.release_date, o.date_source, o.year) for o in found] == [('2009-12-01', 'header', '2009')]


def test_the_tag_dates_a_header_without_date():
    found = entries_of('1.0\n---\n\n- Initial release [hannosch]\n', {'1.0': '2009-11-30'})

    assert [(o.release_date, o.date_source) for o in found] == [('2009-11-30', 'tag')]


def test_unreleased_and_undated_entries_have_no_date():
    text = '1.1 (unreleased)\n----------------\n\n- Fix [a]\n\n1.0\n---\n\n- Initial release [a]\n'

    found = entries_of(text, {'1.1': '2011-01-01'})

    assert [(o.release_date, o.date_source) for o in found] == [('', 'unreleased'), ('', 'missing')]


def test_placeholders_are_no_entries():
    text = '1.1 (2011-01-01)\n----------------\n\n- Nothing changed yet.\n\n- *add item here*\n\n- Fix [a]\n'

    assert [o.text for o in entries_of(text)] == ['Fix [a]']


def test_the_occurrence_links_the_entry_at_the_tip_commit():
    found = entries_of('1.0 (2009-12-01)\n----------------\n\n- Initial release [hannosch]\n')

    assert found[0].url == 'https://github.com/plone/plone.app.x/blob/abc/CHANGES.rst#L4'


# Deduplication


def test_the_same_entry_on_two_branches_counts_once_for_the_earliest_release():
    backport = occurrence('Fixed the portlet [a]', '2010-06-01', branch='4.0', default=False)
    original = occurrence('Fixed the portlet [a]', '2010-05-04')
    moved = occurrence('Fixed the portlet [a]', '2010-05-04', path='docs/HISTORY.txt')

    assert deduplicate([backport, moved, original]) == [original]


def test_a_dated_occurrence_wins_over_an_undated_one():
    undated = occurrence('Fixed the portlet [a]', '')
    released = occurrence('Fixed the portlet [a]', '2012-01-01', branch='4.1', default=False)

    assert deduplicate([undated, released]) == [released]


def test_an_edited_backport_counts_twice():
    assert len(deduplicate([occurrence('Fixed the portlet [a]'), occurrence('Fixed the portlet again [a]')])) == 2


def test_a_short_text_in_two_repositories_counts_twice():
    one = occurrence('Initial release [hannosch]', '2008-01-01', repository='plone.app.one')
    two = occurrence('Initial release [hannosch]', '2008-03-01', repository='plone.app.two')

    assert deduplicate([one, two]) == [one, two]


def test_a_short_text_in_two_repositories_with_the_same_date_counts_once():
    one = occurrence('Initial release [hannosch]', '2008-01-01', repository='plone.app.one')
    two = occurrence('Initial release [hannosch]', '2008-01-01', repository='plone.app.two')

    assert deduplicate([two, one]) == [one]


def test_a_long_text_copied_to_another_repository_counts_once():
    text = 'Fixed the portlet that showed the wrong title when the folder was empty [a]'
    original = occurrence(text, '2008-01-01', repository='Products.CMFPlone')
    copy = occurrence(text, '2008-05-01', repository='Plone', branch='3.1', default=False)

    assert len(changelogs.normalise(text)) >= changelogs.CROSS_REPOSITORY_LENGTH
    assert deduplicate([copy, original]) == [original]


# Name mapping


@pytest.fixture
def mapper():
    src = 'https://example.org/record'
    people = [
        ('alecpm', 'Alec Mitchell', 'alecpm', src), ('wichert', 'Wichert Akkerman', 'wichert', src),
        ('andy-mckay', 'Andy McKay', 'andym', src), ('whitmo', 'Whit Morriss', 'whitmo', src),
        ('tiran', 'Christian Heimes', 'tiran', src), ('runyaga', 'Alan Runyan', 'runyaga', src),
        ('ebrehault', 'Eric Bréhault', 'ebrehault', src),
    ]
    identities = [
        Identity('alecpm', 'name', 'alecm', src), Identity('wichert', 'name', 'Wiggy', src),
        Identity('andy-mckay', 'email', 'jdoe@localhost', src), Identity('whitmo', 'email', 'wsmith@localhost', src),
        Identity('tiran', 'email', 'tess@example.org', src), Identity('runyaga', 'github-alias', 'bobdobbs666', src),
    ]
    return NameMapper(registry_of(people, identities), ['hannosch', 'Limi', 'bobdobbs666', 'whitmo'],
                      {'mister-roboto': 'bot'})


@pytest.mark.parametrize('name, person, layer', [
    ('alecm', 'alecpm', 'identity'),
    ('ALECM', 'alecpm', 'identity'),
    ('wiggy', 'wichert', 'identity'),
    ('jdoe', 'andym', 'identity'),
    ('wsmith', 'whitmo', 'identity'),
    ('Whit Morriss', 'whitmo', 'identity'),
    ('tess@example.org', 'tiran', 'identity'),
    ('wsmith@localhost', 'whitmo', 'identity'),
    ('mister-roboto', None, 'bot'),
    ('pre-commit-ci[bot]', None, 'bot'),
    ('limi', 'Limi', 'login'),
    # A login of code work that is a second account counts for the main account
    ('bobdobbs666', 'runyaga', 'identity'),
    ('Eric Brehault', 'ebrehault', 'identity'),
    ('Andy', 'Andy', 'unmatched'),
    ('timo', 'timo', 'unmatched'),
    ('someone@example.org', 'someone@example.org', 'unmatched'),
])
def test_name_mapping_order(mapper, name, person, layer):
    assert mapper.map(name) == (person, layer)


def test_every_named_person_gets_full_credit(mapper):
    entry = occurrence('Fixed the portlet [alecm, limi and timo]')

    assert changelogs.credited(entry, mapper) == [
        ('alecpm', 'alecm', 'identity'), ('Limi', 'limi', 'login'), ('timo', 'timo', 'unmatched')]


def test_a_person_named_twice_gets_one_credit(mapper):
    assert len(changelogs.credited(occurrence('Fixed it [alecm] [ALECM]'), mapper)) == 1


def test_weak_forms_count_only_when_every_name_maps(mapper):
    assert changelogs.credited(occurrence('Fixed the portlet (hopefully)'), mapper) == []
    assert changelogs.credited(occurrence('Fixed the portlet (limi)'), mapper) == [('Limi', 'limi', 'login')]


def test_bots_get_no_credit(mapper):
    assert changelogs.credited(occurrence('Update the configuration [mister-roboto]'), mapper) == []


# Counting per year and the output


def test_count_per_person_and_year(mapper):
    entries = [
        occurrence('Fixed the portlet [alecm, timo]', '2010-05-04'),
        occurrence('Fixed the login [Timo]', '2010-06-01', repository='plone.app.two'),
        occurrence('Fixed the calendar [timo]', '2011-01-01'),
        occurrence('Undated fix [alecm]', ''),
        occurrence('Fixed without a name', '2010-07-01'),
    ]

    per_year, coverage = plone_changelogs.count(entries, mapper)

    assert set(per_year) == {'2010', '2011'}
    timo = per_year['2010']['timo']
    # Unmatched names count under their most frequent spelling, ignoring case
    assert timo['entries'] == 2 and timo['names'] == {'timo', 'Timo'}
    assert timo['repositories'] == {'plone.app.x', 'plone.app.two'}
    assert per_year['2010']['alecpm']['entries'] == 1
    assert coverage['2010'] == {'entries': 3, 'named': 2, 'mapped': 1}


def test_output_format(mapper):
    entries = [occurrence('Fix one [alecm, timo]'), occurrence('Fix two [timo]'), occurrence('Fix three [limi]')]
    per_year, _ = plone_changelogs.count(entries, mapper)

    table = plone_changelogs.year_table(per_year['2010'])

    assert list(table.columns) == plone_changelogs.COLUMNS
    assert table.to_dict('records') == [
        {'username': 'timo', 'changelog_entries': 2, 'repositories_count': 1, 'repositories': 'plone.app.x',
         'changelog_names': 'timo', 'matched_by': 'unmatched'},
        {'username': 'alecpm', 'changelog_entries': 1, 'repositories_count': 1, 'repositories': 'plone.app.x',
         'changelog_names': 'alecm', 'matched_by': 'identity'},
        {'username': 'Limi', 'changelog_entries': 1, 'repositories_count': 1, 'repositories': 'plone.app.x',
         'changelog_names': 'limi', 'matched_by': 'login'},
    ]


def test_empty_year_has_the_columns():
    assert list(plone_changelogs.year_table({}).columns) == plone_changelogs.COLUMNS
