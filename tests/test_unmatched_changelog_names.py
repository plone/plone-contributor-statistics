"""Proposals for identities.csv from commits that repeat the entries (#71)."""

from scripts.lib import changelogs, paths
from scripts.lib.addresses import mask_address
from scripts.lib.changelogs import NameMapper, Occurrence
from scripts.lib.model import Identity, Registry, source_id
from tests.conftest import registry_of
from scripts.tools import unmatched_changelog_names as tool


def entry(text, release_date='2005-03-01', repository='Products.CMFPlone'):
    names, variant = changelogs.extract_names(text)
    return Occurrence(repository=repository, path='HISTORY.txt', branch='2.5', default=False, commit='tip', line=7,
                      text=text, release_date=release_date, date_source='header', names=names, variant=variant)


def commit(sha, email, name, message, date='2005-02-01T12:00:00Z'):
    return {'sha': sha, 'author_email': email, 'author_name': name, 'date': date, 'message': message}


REGISTRY = registry_of(
    [('alec-mitchell', 'Alec Mitchell', 'alecpm', 'https://example.org/a'),
     ('hanno-schlichting', 'Hanno Schlichting', None, 'https://example.org/h')],
    [Identity('hanno-schlichting', 'email', mask_address('hanno@widgets.test'), 'https://example.org/h')], [], [])
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
    commit('c1', 'amitch@acme.test', 'Alec Mitchell', 'Fixed the broken calendar portlet in the right column\n\n'),
    # A later cherry-pick of the same change
    commit('c1b', 'other@example.org', 'Someone', 'Fixed the broken calendar portlet in the right column',
           date='2006-01-01T12:00:00Z'),
    commit('c2', 'AMITCH@Acme.test', 'Alec Mitchell', 'Made the navigation tree work with very deep folder '
           'structures. Refs #123'),
    commit('c3', 'hanno@widgets.test', 'Hanno Schlichting', 'Fixed the sharing tab for groups with special characters'),
    commit('c4', 'limi@plone.org', 'Alexander Limi', 'Added a test for the login form and the logout view'),
]}


def test_unmatched_entries_in_the_years():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))

    assert {name: len(entries) for name, entries in unmatched.items()} == {'alecm': 4, 'wald': 1}


def test_evidence_from_the_first_commit_of_single_name_entries():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))

    found = tool.evidence(unmatched, COMMITS.get)

    # The entry of two people and the short entry are no evidence
    assert found['alecm']['authors'] == {('amitch@acme.test', 'Alec Mitchell'): 2}
    assert found['alecm']['examples']['amitch@acme.test'][1]['sha'] == 'c1'
    assert found['wald']['authors'] == {('hanno@widgets.test', 'Hanno Schlichting'): 1}


ALEC = f'Author: Alec Mitchell <{mask_address("amitch@acme.test", True)}>'
C1 = 'https://github.com/plone/Products.CMFPlone/commit/c1'


def test_proposals_cite_the_commit_to_capture_and_link_the_entry():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    logins = {'amitch@acme.test': 'alecpm'}

    found = tool.proposals(unmatched, tool.evidence(unmatched, COMMITS.get),
                           lambda email, entry, commit: logins.get(email), REGISTRY)

    command, row = found[0]
    assert command == f'python -m scripts.tools.capture {C1} --name amitch@acme.test'
    assert row == (
        'alec-mitchell', 'name', 'alecm', source_id(C1), ALEC,
        'Changelog entry: https://github.com/plone/Products.CMFPlone/blob/tip/HISTORY.txt#L7; the commit by '
        f'Alec Mitchell that repeats it: {C1}',
        4, 2, 1.0)
    # Without a login, the person comes from the email address of the commit
    assert found[1][1][:3] == ('hanno-schlichting', 'name', 'wald')
    assert tool.HEADER == ['person', 'kind', 'value', 'source', 'snippet', 'notes', 'entries', 'commits', 'share']


def test_the_capture_command_is_quoted_for_the_shell():
    assert tool.capture_command(C1, "o'brien@example.com") == (
        f"python -m scripts.tools.capture {C1} --name 'o'\"'\"'brien@example.com'")


def test_listing_writes_nothing(tmp_repo, capsys):
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    before = paths.SOURCES.read_text(encoding='utf-8')
    logins = {'amitch@acme.test': 'alecpm'}
    tool.print_proposals(tool.proposals(unmatched, tool.evidence(unmatched, COMMITS.get),
                                        lambda email, entry, commit: logins.get(email), REGISTRY))
    assert paths.SOURCES.read_text(encoding='utf-8') == before
    out = capsys.readouterr().out
    assert f'# capture first: python -m scripts.tools.capture {C1} --name amitch@acme.test\n' in out
    assert f'alec-mitchell,name,alecm,{source_id(C1)},{ALEC},' in out


def test_a_login_without_a_person_is_a_note():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    found = tool.evidence(unmatched, COMMITS.get)
    empty = Registry([], [], [], [])

    rows = tool.proposals(unmatched, found, lambda email, entry, commit: 'unknown-login', empty)

    assert rows[0][1][:3] == ('?no person for the login unknown-login', 'name', 'alecm')
    rows = tool.proposals(unmatched, found, lambda email, entry, commit: None, empty)
    assert rows[1][1][0] == f'?no person for Hanno Schlichting <{mask_address("hanno@widgets.test")}>'


def test_authors_below_the_share_are_not_proposed():
    unmatched = {'ender': [entry('Fixed the broken calendar portlet in the right column [ender]'),
                           entry('Fixed the sharing tab for groups with special characters [ender]')]}

    found = tool.evidence(unmatched, COMMITS.get)

    assert tool.proposals(unmatched, found, lambda *args: None, REGISTRY) == []
    assert len(tool.proposals(unmatched, found, lambda *args: None, REGISTRY, min_share=0.5)) == 1


def test_the_snippet_keeps_the_domain_and_the_note_does_not():
    unmatched = tool.unmatched_entries(ENTRIES, MAPPER, range(2004, 2013))
    found = tool.evidence(unmatched, COMMITS.get)
    rows = tool.proposals(unmatched, found, lambda *args: None, Registry([], [], [], []))

    bare = mask_address('amitch@acme.test')
    assert rows[0][1][0] == f'?no person for Alec Mitchell <{bare}>'
    assert rows[0][1][4] == f'Author: Alec Mitchell <{bare}@acme.test>'
    assert 'amitch' not in ''.join(str(cell) for cell in rows[0][1])
