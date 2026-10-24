"""The work list of the sources the mapping files cite: offline, with registers in a temporary repository."""

import json

import pytest

from scripts.lib import paths
from scripts.tools import cited_sources
from scripts.tools.cited_sources import (Cited, kind_hint, parse_segment, resolve_searches, review, split_segments,
                                         work_list)

SPEAKER = 'https://2017.ploneconf.org/people/jane-doe.html'
ARCHIVED = 'https://web.archive.org/web/20171020000000/https://2017.ploneconf.org/people/jane-doe.html'
SEARCH = ('https://github.com/search?q=author%3Ajanedoe+org%3Aacme+committer-date%3A2014-01-01..2014-12-31'
          '&type=commits')


def test_split_segments_respects_quotes():
    cell = '"Works at Acme; before that at Beta", speaker page: https://a.org/p; Profile: https://github.com/x'
    assert split_segments(cell) == ['"Works at Acme; before that at Beta", speaker page: https://a.org/p',
                                    'Profile: https://github.com/x']


def test_split_segments_survives_a_quote_cut_short():
    # The migration cut long labels with "…:"; the quote it opened has no end
    cell = ('signature "Jane Doe | Owner at …: https://a.org/one ; https://a.org/two; '
            '"Jane works at Acme.", speaker page: https://a.org/three')
    assert split_segments(cell) == ['signature "Jane Doe | Owner at …: https://a.org/one', 'https://a.org/two',
                                    '"Jane works at Acme.", speaker page: https://a.org/three']


def test_parse_segment_quote_label_url():
    segment = '"He works at X.", Plone Conference 2017 speaker page: https://a.org/p'
    assert parse_segment(segment) == [Cited('https://a.org/p', ('He works at X.',),
                                            'Plone Conference 2017 speaker page')]


def test_quote_attaches_to_every_url_of_its_segment():
    segment = f'"Jane works at Acme.", Plone Conference 2017 speaker page: {SPEAKER} (archived: {ARCHIVED})'
    cited = parse_segment(segment)
    assert [c.url for c in cited] == [SPEAKER, ARCHIVED]
    assert {c.quotes for c in cited} == {('Jane works at Acme.',)}
    assert {c.label for c in cited} == {'Plone Conference 2017 speaker page'}


def test_segment_without_quote():
    assert parse_segment('example commit: https://github.com/plone/a/commit/abc.') == [
        Cited('https://github.com/plone/a/commit/abc', (), 'example commit')]
    assert parse_segment('confirmed in #90 (https://github.com/plone/x/pull/90): did no Plone projects') == [
        Cited('https://github.com/plone/x/pull/90', (), 'confirmed in #90')]
    assert parse_segment('no address here') == []


def test_every_quote_before_the_first_url_counts_and_quoted_urls_are_not_cited():
    segment = ('"Small business digital services", "Copyright 2002 Jane Doe", her own site: '
               'http://web.archive.org/web/20030919111622/http://jane.example/')
    assert parse_segment(segment) == [Cited('http://web.archive.org/web/20030919111622/http://jane.example/',
                                            ('Small business digital services', 'Copyright 2002 Jane Doe'),
                                            'her own site')]
    signature = 'signature "Acme Ltd, http://acme.example" in her messages: 2007: https://a.org/m/1'
    assert parse_segment(signature) == [Cited('https://a.org/m/1', ('Acme Ltd, http://acme.example',),
                                              'signature in her messages: 2007')]


def test_a_quote_cut_short_keeps_its_beginning():
    segment = 'signature "Jane Doe | Owner at …: https://a.org/one'
    assert parse_segment(segment) == [Cited('https://a.org/one', ('Jane Doe | Owner at',), 'signature')]
    assert parse_segment('lists "Jane Doe ... …: https://a.org/team')[0].quotes == ('Jane Doe',)


def test_kind_hint():
    assert kind_hint(SPEAKER, 'Plone Conference 2017 Speaker Page') == 'speaker-page'
    assert kind_hint('https://github.com/janedoe', 'GitHub profile, company: Acme') == 'profile'
    assert kind_hint('https://github.com/janedoe', 'github profile') == 'profile'
    assert kind_hint('https://a.org/p', 'team page') is None


def write(path, header, rows):
    path.write_text(header + '\n' + ''.join(row + '\n' for row in rows), encoding='utf-8')


@pytest.fixture
def registers(tmp_repo):
    write(paths.PEOPLE, 'id,name,github,source', [
        'jane-doe,Jane Doe,janedoe,https://github.com/janedoe',
        'john-roe,John Roe,,"""John Roe works at Beta."", speaker page: https://a.org/roe"'])
    write(paths.IDENTITIES, 'person,kind,value,source', [
        'jane-doe,name,Jane M. Doe,example commit: https://github.com/plone/a/commit/abc',
        'jane-doe,login,jdoe,https://github.com/janedoe'])
    write(paths.ORGANISATIONS, 'id,name,kind,github,aliases,notes', [
        'acme,Acme,organisation,acme,Acme GmbH;ACME Inc.,', 'beta,Beta,organisation,,,'])
    write(paths.AFFILIATIONS, 'person,organisation,from,to,source,checked,notes', [
        f'jane-doe,acme,2014,2016,"""Jane works at Acme; she leads it."", speaker page: {SPEAKER} '
        f'(archived: {ARCHIVED}); GitHub profile, company: Acme: https://github.com/janedoe",,'
        f'"Commits in 2014 (search: {SEARCH})"',
        f'john-roe,beta,2015,2015,"""Roe is at Beta."", speaker page: {SPEAKER}",,'])
    write(paths.MAPPINGS_DIR / 'rejected_proposals.csv', 'person,organisation,from,to,reason,source', [
        'john-roe,acme,2010,2010,"a client, see https://a.org/client",https://github.com/plone/x/pull/1'])
    return cited_sources.load_old_registers()


def by_url(items):
    return {item['url']: item for item in items}


def test_work_list_merges_urls_across_files(registers):
    registry, rejections = registers
    items = work_list(registry, rejections)
    assert [item['url'] for item in items] == sorted(item['url'] for item in items)
    found = by_url(items)
    assert set(found) == {'https://a.org/client', 'https://a.org/roe', ARCHIVED, SPEAKER,
                          'https://github.com/janedoe', 'https://github.com/plone/a/commit/abc',
                          'https://github.com/plone/x/pull/1'}  # the search is no item
    assert found[SPEAKER] == {
        'url': SPEAKER, 'quotes': ['Jane works at Acme; she leads it.', 'Roe is at Beta.'],
        'names': ['Jane Doe', 'Jane M. Doe', 'Acme', 'Acme GmbH', 'ACME Inc.', 'John Roe', 'Beta'],
        'kind': 'speaker-page'}
    assert found[ARCHIVED]['quotes'] == ['Jane works at Acme; she leads it.']
    assert found['https://github.com/janedoe'] == {  # the quote of the cell's other segment comes along
        'url': 'https://github.com/janedoe', 'quotes': ['Jane works at Acme; she leads it.'],
        'names': ['Jane Doe', 'Jane M. Doe', 'Acme', 'Acme GmbH', 'ACME Inc.'], 'kind': 'profile'}
    assert found['https://github.com/plone/a/commit/abc']['names'] == ['Jane Doe', 'Jane M. Doe']
    assert found['https://a.org/roe'] == {'url': 'https://a.org/roe', 'quotes': ['John Roe works at Beta.'],
                                          'names': ['John Roe'], 'kind': 'speaker-page'}
    assert found['https://a.org/client']['names'] == ['John Roe', 'Acme', 'Acme GmbH', 'ACME Inc.']


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload, self.text = payload, json.dumps(payload)

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return Response(self.answers.get(params['q'], {'total_count': 0, 'items': []}))


def commit_item(sha):
    return {'html_url': f'https://github.com/acme/tool/commit/{sha}'}


def test_search_urls_resolve_to_commits(registers, capsys):
    empty = 'https://github.com/search?q=author%3Anobody&type=commits'
    session = FakeSession({'author:janedoe org:acme committer-date:2014-01-01..2014-12-31': {
        'total_count': 4, 'items': [commit_item(sha) for sha in ('a1', 'b2', 'c3', 'd4')]}})
    sleeps = []
    resolved = resolve_searches([SEARCH, empty], session, sleep=sleeps.append)
    assert resolved == {SEARCH: [f'https://github.com/acme/tool/commit/{sha}' for sha in ('a1', 'b2', 'c3')],
                        empty: []}
    assert session.calls[0] == ('https://api.github.com/search/commits',
                                {'q': 'author:janedoe org:acme committer-date:2014-01-01..2014-12-31',
                                 'per_page': 3})
    assert sleeps == [cited_sources.PACE, cited_sources.PACE]
    assert empty in capsys.readouterr().err
    # cached: a second run asks nothing
    assert resolve_searches([SEARCH, empty], FakeSession({}), sleep=sleeps.append) == resolved
    assert len(sleeps) == 2

    registry, rejections = registers
    found = by_url(work_list(registry, rejections, resolved))
    assert found['https://github.com/acme/tool/commit/a1'] == {
        'url': 'https://github.com/acme/tool/commit/a1', 'quotes': [], 'names': ['Jane Doe', 'Jane M. Doe'],
        'kind': None}
    assert 'https://github.com/acme/tool/commit/d4' not in found


def test_main_writes_the_work_list_and_the_searches(registers, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cited_sources, 'github_session', lambda: FakeSession({}))
    monkeypatch.setattr(cited_sources.time, 'sleep', lambda seconds: None)
    worklist, searches = tmp_path / 'worklist.jsonl', tmp_path / 'searches.json'
    assert cited_sources.main(['--worklist', str(worklist), '--searches', str(searches)]) == 0
    lines = [json.loads(line) for line in worklist.read_text(encoding='utf-8').splitlines()]
    assert [line['url'] for line in lines] == sorted(line['url'] for line in lines)
    assert json.loads(searches.read_text(encoding='utf-8')) == {SEARCH: []}
    err = capsys.readouterr().err
    assert '7 items' in err and '4 with quotes' in err


def cell_registers(source):
    """Registers with one affiliation of Jane Doe at Acme, cited by the given cell."""
    write(paths.PEOPLE, 'id,name,github,source', ['jane-doe,Jane Doe,,https://github.com/janedoe'])
    write(paths.ORGANISATIONS, 'id,name,kind,github,aliases,notes', ['acme,Acme,organisation,,,'])
    quoted = source.replace('"', '""')
    write(paths.AFFILIATIONS, 'person,organisation,from,to,source,checked,notes',
          [f'jane-doe,acme,2016,2017,"{quoted}",,'])
    return cited_sources.load_old_registers()


def test_quotes_carry_to_the_continuation_urls_of_the_cell(tmp_repo):
    # the 2016/2017 shape: the second year in its own segment, labelled only with the year
    registry, rejections = cell_registers(
        '"Jane works at Acme.", speaker page 2016: https://a.org/2016; 2017: https://a.org/2017; '
        '"Jane leads Acme.", team page (Jan 2011): https://web.archive.org/web/20090101000000/https://acme.example/ '
        '; (archived 2011) https://web.archive.org/web/20110101000000/https://acme.example/')
    found = by_url(work_list(registry, rejections))
    both = ['Jane works at Acme.', 'Jane leads Acme.']
    assert found['https://a.org/2016']['quotes'] == both
    assert found['https://a.org/2017']['quotes'] == both
    assert found['https://web.archive.org/web/20090101000000/https://acme.example/']['quotes'] == both[::-1]
    assert found['https://web.archive.org/web/20110101000000/https://acme.example/']['quotes'] == both
    entries = review(registry, rejections)
    assert [entry['url'] for entry in entries] == [
        'https://a.org/2017', 'https://web.archive.org/web/20110101000000/https://acme.example/']
    assert entries[0] == {'problem': 'quotes from elsewhere in the cell', 'file': 'affiliations.csv',
                          'column': 'source', 'person': 'jane-doe', 'organisation': 'acme',
                          'url': 'https://a.org/2017', 'segment': '2017: https://a.org/2017', 'quotes': both}


def test_a_quote_without_url_goes_to_the_urls_of_its_cell(tmp_repo):
    registry, rejections = cell_registers(
        'team page lists "Jane Doe, Acme"; signature "Jane Doe | Acme …: https://a.org/team ; https://a.org/list')
    found = by_url(work_list(registry, rejections))
    assert found['https://a.org/team']['quotes'] == ['Jane Doe | Acme', 'Jane Doe, Acme']
    assert found['https://a.org/list']['quotes'] == ['Jane Doe, Acme', 'Jane Doe | Acme']
    entries = review(registry, rejections)
    assert entries[0] == {'problem': 'quotes without address', 'file': 'affiliations.csv', 'column': 'source',
                          'person': 'jane-doe', 'organisation': 'acme', 'segment': 'team page lists "Jane Doe, Acme"',
                          'quotes': ['Jane Doe, Acme']}
    assert [entry.get('url') for entry in entries] == [None, 'https://a.org/list']


def test_main_writes_the_review_file(tmp_repo, monkeypatch, tmp_path, capsys):
    cell_registers('team page lists "Jane Doe, Acme"; profile: https://a.org/team')
    monkeypatch.setattr(cited_sources, 'github_session', lambda: FakeSession({}))
    paths_ = {name: tmp_path / name for name in ('worklist.jsonl', 'searches.json', 'review.jsonl')}
    assert cited_sources.main(['--worklist', str(paths_['worklist.jsonl']), '--searches',
                               str(paths_['searches.json']), '--review', str(paths_['review.jsonl'])]) == 0
    lines = [json.loads(line) for line in paths_['review.jsonl'].read_text(encoding='utf-8').splitlines()]
    assert [line['problem'] for line in lines] == ['quotes without address', 'quotes from elsewhere in the cell']
    assert '1 segments with quotes but no address, 1 addresses with quotes from elsewhere' in capsys.readouterr().err


def test_a_name_with_a_trailing_bracket_is_also_looked_for_without_it(tmp_repo):
    write(paths.PEOPLE, 'id,name,github,source', ['rocky,Rocky Burt (sprint leaders),,https://a.org/sprint'])
    write(paths.ORGANISATIONS, 'id,name,kind,github,aliases,notes',
          ['leo,Leonardo Caballero (independent),independent,,,'])
    write(paths.AFFILIATIONS, 'person,organisation,from,to,source,checked,notes',
          ['rocky,leo,2007,2007,https://a.org/team,,'])
    found = by_url(work_list(*cited_sources.load_old_registers()))
    assert found['https://a.org/sprint']['names'] == ['Rocky Burt (sprint leaders)', 'Rocky Burt']
    assert found['https://a.org/team']['names'] == ['Rocky Burt (sprint leaders)', 'Rocky Burt',
                                                     'Leonardo Caballero (independent)', 'Leonardo Caballero']
