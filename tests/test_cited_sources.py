"""The work list of the sources the mapping files cite: offline, with registers in a temporary repository."""

import json

import pytest

from scripts.lib import paths
from scripts.lib.model import load_registry, load_rejection_rows
from scripts.tools import cited_sources
from scripts.tools.cited_sources import Cited, kind_hint, parse_segment, resolve_searches, split_segments, work_list

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
    write(paths.REJECTED_PROPOSALS, 'person,organisation,from,to,reason,source', [
        'john-roe,acme,2010,2010,"a client, see https://a.org/client",https://github.com/plone/x/pull/1'])
    return load_registry(), load_rejection_rows()


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
    assert found['https://github.com/janedoe'] == {
        'url': 'https://github.com/janedoe', 'quotes': [],
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
    assert '7 items' in err and '3 with quotes' in err
