import datetime

import pytest

from scripts.lib.addresses import mask_address
from scripts.lib.model import (Citation, Identity, Source, affiliation_id, load_citations, load_identities,
                               replace_excerpt, source_id, write_citations, write_identities, write_source)
from scripts.tools import cite_snippets

CAPTURED = 'https://example.org/speaker'
UNCAPTURED = 'https://example.org/video'
NOTE = 'not captured on 2026-10-22: rate limited (HTTP 429)'
WORKS = 'Jane Doe works at Example Company'
LEADS = 'She leads the Plone team'
EXCERPT = f'{WORKS} since 2015.\n\n---\n\n{LEADS} at Example Company.'
JANE = affiliation_id('jane', 'example-company', 2015, 2019)
ZOE_MAIL = mask_address('zoe@example.com')
ZOE = affiliation_id('zoe', 'example-company', 2016, 2020)


def source(url, notes):
    sid = source_id(url)
    write_source(Source(sid, 'speaker-page', url, datetime.date(2026, 10, 22), url, None,
                        datetime.datetime(2026, 10, 22, 10, tzinfo=datetime.UTC), notes))
    return sid


@pytest.fixture
def registers(write_registers):
    write_registers(people=[('jane', 'janedoe'), ('zoe', 'zoe')],
                    affiliations=[('jane', 'example-company', 2015, 2019), ('zoe', 'example-company', 2016, 2020)],
                    organisations=[('example-company', 'Example Company')])
    captured, uncaptured = source(CAPTURED, None), source(UNCAPTURED, NOTE)
    replace_excerpt(captured, EXCERPT)
    replace_excerpt(uncaptured, NOTE)
    citations = [
        # two quotes on the page and one too short to count
        Citation(JANE, captured, None, None, f'cited as: "{WORKS}", speaker page; "{LEADS}"; "Jane"'),
        # a source that was never read: its excerpt is its note, which is no record
        Citation(JANE, uncaptured, None, None, f'cited as: "{NOTE}"'),
        # a quote not on the page
        Citation(ZOE, captured, None, None, 'cited as: "Zoe works at Example Company"'),
        # cited with a snippet already
        Citation(ZOE, captured, LEADS, None, f'cited as: "{WORKS}"'),
    ]
    identities = [
        Identity('jane', 'name', 'Jane Doe', captured, None, f'cited as: "{LEADS}" and "{WORKS}"'),
        Identity('jane', 'github', 'janedoe', uncaptured, None, f'"{NOTE}"'),
        Identity('zoe', 'email', ZOE_MAIL, None, None, 'a commit address'),
    ]
    write_citations(citations)
    write_identities(identities)
    return captured, uncaptured


def test_quotes_in_notes():
    assert cite_snippets.quotes_in('cited as: "one quote here", a page; "short" and "another quote"') == [
        'one quote here', 'another quote']
    assert cite_snippets.quotes_in(None) == []
    assert cite_snippets.quotes_in('an "unpaired quote here') == []


def test_dry_run_counts_and_writes_nothing(registers, capsys):
    before = (load_citations(), load_identities())
    assert cite_snippets.main([]) == 0
    out = capsys.readouterr().out
    assert 'citations filled: 1' in out
    assert 'citation rows added: 1' in out
    assert 'identities filled: 1' in out
    assert WORKS in out
    assert 'dry run' in out
    assert (load_citations(), load_identities()) == before


def test_write_fills_the_snippets_and_adds_rows(registers):
    from scripts.tools import check, datapackage

    captured, uncaptured = registers
    assert cite_snippets.main(['--write']) == 0
    notes = f'cited as: "{WORKS}", speaker page; "{LEADS}"; "Jane"'
    assert [c for c in load_citations() if c.affiliation == JANE] == sorted([
        Citation(JANE, captured, WORKS, None, notes),
        Citation(JANE, captured, LEADS, None, notes),
        Citation(JANE, uncaptured, None, None, f'cited as: "{NOTE}"'),
    ], key=lambda c: (c.affiliation, c.source, c.snippet or ''))
    zoe = [c for c in load_citations() if c.affiliation == ZOE]
    assert [(c.snippet, c.notes) for c in zoe] == [
        (None, 'cited as: "Zoe works at Example Company"'), (LEADS, f'cited as: "{WORKS}"')]
    identities = {(i.kind, i.value): i.snippet for i in load_identities()}
    assert identities == {('name', 'Jane Doe'): LEADS, ('github', 'janedoe'): None,
                          ('email', ZOE_MAIL): None}
    datapackage.main([])
    assert check.validate() == []


def test_a_second_run_changes_nothing(registers, capsys):
    cite_snippets.main(['--write'])
    after = (load_citations(), load_identities())
    capsys.readouterr()
    cite_snippets.main(['--write'])
    assert (load_citations(), load_identities()) == after
    out = capsys.readouterr().out
    assert 'citations filled: 0' in out and 'citation rows added: 0' in out and 'identities filled: 0' in out


def test_a_quote_cited_already_is_not_cited_again(registers):
    captured, _ = registers
    write_citations([*load_citations(), Citation(ZOE, captured, None, None, f'cited as: "{LEADS}"; "{WORKS}"')])
    cite_snippets.main(['--write'])
    zoe = [c for c in load_citations() if c.affiliation == ZOE]
    assert sorted(c.snippet or '' for c in zoe) == sorted(['', LEADS, WORKS])


def test_an_added_row_supersedes_nothing(registers):
    from scripts.lib.model import load_sources

    captured, _ = registers
    decision = Citation(ZOE, captured, None, 'abcdefabcdef', f'"{WORKS}" and "{LEADS}"')
    result = cite_snippets.fill([decision], [], load_sources())
    assert [(c.snippet, c.supersedes) for c in result.citations] == [(WORKS, 'abcdefabcdef'), (LEADS, None)]


@pytest.mark.parametrize('notes', [
    'cited as: his talk "AbFab! Come back to easy frontend development"',
    'a talk titled "Jane Doe works at Example Company"',
    'its Title: "Jane Doe works at Example Company"',
    'a project CALLED "Jane Doe works at Example Company"',
])
def test_a_quoted_title_is_no_quote(notes):
    assert cite_snippets.quotes_in(notes) == []


def test_a_title_word_further_before_the_quote_does_not_count():
    assert cite_snippets.quotes_in('the talk page, cited as: "Jane Doe works at Example Company"') == [WORKS]


def test_a_quoted_title_fills_no_snippet(registers):
    from scripts.lib.model import load_sources

    captured, _ = registers
    row = Citation(ZOE, captured, None, None, f'his talk "{WORKS}"')
    assert cite_snippets.fill([row], [], load_sources()).citations == [row]


def test_a_quote_overlapping_a_cited_snippet_is_not_cited_again(registers):
    from scripts.lib.model import load_sources

    captured, _ = registers
    cited = Citation(ZOE, captured, 'Jane Doe works at  Example Company', None, None)
    longer = Citation(ZOE, captured, None, None, f'"{WORKS} since 2015"; "{LEADS}"')
    prefix = Citation(JANE, captured, None, None, f'"{WORKS}"; "Jane Doe works at Example"')
    result = cite_snippets.fill([cited, longer, prefix], [], load_sources())
    assert [(c.affiliation, c.snippet) for c in result.citations] == [
        (ZOE, cited.snippet), (ZOE, LEADS), (JANE, WORKS)]


def test_the_dry_run_lists_every_change(registers, capsys):
    captured, _ = registers
    extra = [Citation(f'a0000000{n}', captured, None, None, f'cited as: "{WORKS}"') for n in range(7)]
    write_citations([*load_citations(), *extra])
    cite_snippets.main([])
    lines = capsys.readouterr().out.splitlines()
    filled = [line for line in lines if line.startswith('citation filled: ')]
    assert len(filled) == 8  # jane's row and the seven rows of unknown affiliations
    assert f'citation filled: jane, {JANE}, source {captured}: "{WORKS}" (after: cited as:)' in filled
    assert f'citation filled: ?, a00000006, source {captured}: "{WORKS}" (after: cited as:)' in filled
    added = [line for line in lines if line.startswith('citation row added: ')]
    assert len(added) == 1
    assert added[0].startswith(f'citation row added: jane, {JANE}, source {captured}: "{LEADS}" (after: …')
    assert added[0].endswith('Example Company", speaker page;)')
    assert f'identity filled: jane, name Jane Doe, source {captured}: "{LEADS}" (after: cited as:)' in lines


def test_a_raw_address_in_a_note_is_found_in_the_masked_excerpt(registers):
    captured, _ = registers
    masked = mask_address('jane@acme.test', keep_domain=True)
    line = f'Author: Jane <{masked}>'
    replace_excerpt(captured, f'{EXCERPT}\n\n---\n\n{line}')
    note = 'cited as: "Author: Jane <jane@acme.test>"'
    write_citations([*load_citations(), Citation(ZOE, captured, None, None, note)])
    cite_snippets.main(['--write'])
    snippets = [c.snippet for c in load_citations() if c.affiliation == ZOE]
    assert line in snippets
    assert all('jane@acme.test' not in (s or '') for s in snippets)
