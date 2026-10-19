"""Proposals for identities.csv from commits that repeat the entries (#71)."""

from scripts.lib import changelogs
from scripts.lib.changelogs import NameMapper, Occurrence
from scripts.lib.model import Identity, Person, Registry
from scripts.tools import unmatched_changelog_names as tool


def entry(text, release_date='2005-03-01', repository='Products.CMFPlone'):
    names, variant = changelogs.extract_names(text)
    return Occurrence(repository=repository, path='HISTORY.txt', branch='2.5', default=False, commit='tip', line=7,
                      text=text, release_date=release_date, date_source='header', names=names, variant=variant)


def commit(sha, email, name, message, date='2005-02-01T12:00:00Z'):
    return {'sha': sha, 'author_email': email, 'author_name': name, 'date': date, 'message': message}


REGISTRY = Registry(
    [Person('alec-mitchell', 'Alec Mitchell', 'alecpm', 'https://example.org/a'),
     Person('hanno-schlichting', 'Hanno Schlichting', None, 'https://example.org/h')],
    [Identity('hanno-schlichting', 'email', 'hanno@hannosch.eu', 'https://example.org/h')], [], [])
MAPPER = NameMapper(REGISTRY, ['limi'], {})
ENTRIES = [
    entry('Fixed the broken calendar portlet in the right column [alecm]'),
    entry('Made the navigation tree work with very deep folder structures [alecm]'),
    entry('Fixed the sharing tab for groups with special characters [wald]'),
    entry('Added a test for the login form and the logout view [alecm, limi]'),
    entry('Fixed [alecm]'),
    entry('Fixed the search form for anonymous users of the site [timo]', release_date='2014-01-01'),
]
COMMITS = {'Products.CMFPlone': [
    commit('c1', 'apm13@columbia.edu', 'Alec Mitchell', 'Fixed the broken calendar portlet in the right column\n\n'),
    # A later cherry-pick of the same change
    commit('c1b', 'other@example.org', 'Someone', 'Fixed the broken calendar portlet in the right column',
           date='2006-01-01T12:00:00Z'),
    commit('c2', 'APM13@columbia.edu', 'Alec Mitchell', 'Made the navigation tree work with very deep folder '
           'structures. Refs #123'),
    commit('c3', 'hanno@hannosch.eu', 'Hanno Schlichting', 'Fixed the sharing tab for groups with special characters'),
    commit('c4', 'limi@plone.org', 'Alexander Limi', 'Added a test for the login form and the logout view'),
]}


def test_unmatched_entries_in_the_years():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))

    assert {name: len(entries) for name, entries in unmatched.items()} == {'alecm': 4, 'wald': 1}


def test_evidence_from_the_first_commit_of_single_name_entries():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))

    found = tool.evidence(unmatched, COMMITS.get)

    # The entry of two people and the short entry are no evidence
    assert found['alecm']['authors'] == {('apm13@columbia.edu', 'Alec Mitchell'): 2}
    assert found['alecm']['examples']['apm13@columbia.edu'][1]['sha'] == 'c1'
    assert found['wald']['authors'] == {('hanno@hannosch.eu', 'Hanno Schlichting'): 1}


def test_proposals_link_the_entry_and_the_commit():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    logins = {'apm13@columbia.edu': 'alecpm'}

    rows = tool.proposals(unmatched, tool.evidence(unmatched, COMMITS.get),
                          lambda email, entry, commit: logins.get(email), REGISTRY)

    assert rows[0] == (
        'alec-mitchell', 'name', 'alecm',
        'Changelog entry: https://github.com/plone/Products.CMFPlone/blob/tip/HISTORY.txt#L7; the commit by '
        'Alec Mitchell that repeats it: https://github.com/plone/Products.CMFPlone/commit/c1',
        4, 2, 1.0)
    # Without a login, the person comes from the email address of the commit
    assert rows[1][:3] == ('hanno-schlichting', 'name', 'wald')


def test_a_login_without_a_person_is_a_note():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    found = tool.evidence(unmatched, COMMITS.get)
    empty = Registry([], [], [], [])

    rows = tool.proposals(unmatched, found, lambda email, entry, commit: 'unknown-login', empty)

    assert rows[0][:3] == ('?no person for the login unknown-login', 'name', 'alecm')
    rows = tool.proposals(unmatched, found, lambda email, entry, commit: None, empty)
    assert rows[1][0] == '?no person for Hanno Schlichting <hanno@hannosch.eu>'


def test_authors_below_the_share_are_not_proposed():
    unmatched = {'ender': [entry('Fixed the broken calendar portlet in the right column [ender]'),
                           entry('Fixed the sharing tab for groups with special characters [ender]')]}

    found = tool.evidence(unmatched, COMMITS.get)

    assert tool.proposals(unmatched, found, lambda *args: None, REGISTRY) == []
    assert len(tool.proposals(unmatched, found, lambda *args: None, REGISTRY, min_share=0.5)) == 1
