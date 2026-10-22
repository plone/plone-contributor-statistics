import datetime
import json
import os
import pathlib

import pytest

from scripts.lib.capture import CaptureError, CaptureResult, capture
from scripts.lib.capture import fetch as fetch_module
from scripts.lib.capture.fetch import Fetcher
from scripts.lib.model import load_sources, passages, read_excerpt, source_id

FIXTURES = pathlib.Path(__file__).parent / 'fixtures' / 'capture'
ARTICLE = (FIXTURES / 'article.html').read_bytes()
UNDATED = ARTICLE.replace(b'<meta name="date" content="2015-03-12">\n', b'')
NOW = datetime.datetime(2026, 10, 22, 9, 30, tzinfo=datetime.timezone.utc)
URL = 'https://example.org/sprint'
PARAGRAPH = ('Maurits van Rees is a long time contributor. He works for Zest Software and has fixed many bugs in the '
             'release process during this sprint, which made the final release possible.')


class FakeResponse:
    def __init__(self, status=200, body=b'', content_type='text/html; charset=utf-8'):
        self.status_code = status
        self.content = body
        self.headers = {'Content-Type': content_type}
        self.text = body.decode('utf-8', 'replace')

    def json(self):
        return json.loads(self.content)


class FakeSession:
    """Answers by exact address; any other address is a test failure."""

    def __init__(self, pages=None):
        self.pages = dict(pages or {})
        self.requests = []
        self.headers = {}

    def get(self, url, params=None, **kwargs):
        self.requests.append(url)
        assert url in self.pages, f'unexpected request: {url}'
        return self.pages[url]


class NoNetwork:
    headers = {}

    def get(self, url, **kwargs):
        raise AssertionError(f'no request expected, got {url}')


def no_run(cmd, **kwargs):
    raise AssertionError(f'no command expected, got {cmd}')


@pytest.fixture
def web(tmp_repo, monkeypatch):
    """A fetcher over a fake web; returns (fetcher, session)."""
    monkeypatch.setattr(fetch_module, 'now', lambda: NOW)

    def make(pages=None, session=None):
        session = session or FakeSession(pages)
        fetcher = Fetcher(cache=str(tmp_repo / '.cache' / 'sources'), session=session,
                          sleep=lambda seconds: None, clock=lambda: 0.0)
        return fetcher, session

    return make


def test_capture_creates_row_and_passage(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    sid = source_id(URL)
    assert result == CaptureResult(source_id=sid, created=True, added=(PARAGRAPH,), missing=(), unreachable=False)
    row = load_sources()[sid]
    assert row.kind == 'page'
    assert row.title == 'Plone sprint report'
    assert row.date == datetime.date(2015, 3, 12)
    assert row.url == URL
    assert row.archive_url is None
    assert row.fetched == NOW
    assert read_excerpt(sid) == PARAGRAPH + '\n'


def test_given_kind_title_and_date_win(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['Zest Software'], kind='speaker-page', title='Sprint', date=datetime.date(2015, 3, 1),
            fetcher=fetcher, run=no_run)
    row = load_sources()[source_id(URL)]
    assert (row.kind, row.title, row.date) == ('speaker-page', 'Sprint', datetime.date(2015, 3, 1))


def test_capture_known_source_without_new_quotes_does_not_fetch(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    other, _ = web(session=NoNetwork())
    other.refresh = True  # a fetch would go to the network
    result = capture(URL, ['Maurits van Rees'], fetcher=other, run=no_run)
    assert result == CaptureResult(source_id(URL), False, (), (), False)
    assert capture(URL, fetcher=other, run=no_run) == CaptureResult(source_id(URL), False, (), (), False)


def test_second_quote_in_same_paragraph(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    result = capture(URL, ['fixed many bugs in the release process', 'presented the results'],
                     fetcher=fetcher, run=no_run)
    assert result.created is False
    assert result.missing == ()
    assert len(result.added) == 1 and result.added[0].startswith('At the end of the week')
    assert len(passages(source_id(URL))) == 2
    again = capture(URL, ['long time contributor'], fetcher=fetcher, run=no_run)
    assert again.added == ()
    assert len(passages(source_id(URL))) == 2


def test_two_quotes_of_one_paragraph_in_one_call(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['long time contributor', 'Zest Software'], fetcher=fetcher, run=no_run)
    assert result.added == (PARAGRAPH,)
    assert passages(source_id(URL)) == [PARAGRAPH]


def test_capture_after_interruption_uses_cache(web, tmp_repo):
    fetcher, session = web({URL: FakeResponse(body=ARTICLE)})
    fetcher.get(URL)  # the raw copy was cached, then the run stopped before the row was written
    assert session.requests == [URL]
    other, _ = web(session=NoNetwork())
    result = capture(URL, ['He works for Zest Software'], fetcher=other, run=no_run)
    assert result.created is True
    assert result.added == (PARAGRAPH,)
    assert source_id(URL) in load_sources()


def test_missing_quote_is_reported_not_stored(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['He works for Zest Software', 'works for Plone Inc'], fetcher=fetcher, run=no_run)
    assert result.missing == ('works for Plone Inc',)
    assert result.added == (PARAGRAPH,)
    assert passages(source_id(URL)) == [PARAGRAPH]


def test_quote_only_in_sidebar_is_cut_from_full_text(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['leads the Plone team at Acme Corporation'], fetcher=fetcher, run=no_run)
    assert result.missing == ()
    assert result.added == ('About the author: Jane Doe leads the Plone team at Acme Corporation.',)
    assert 'Zest Software' not in read_excerpt(source_id(URL))


def test_wayback_url_is_stored_readable_and_fetched_raw(web):
    raw_url = 'https://web.archive.org/web/20100125023558id_/http://limi.net:80/about'
    fetcher, session = web({raw_url: FakeResponse(body=UNDATED)})
    result = capture('https://web.archive.org/web/20100125023558if_/http://limi.net:80/about',
                     ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert result.source_id == source_id('http://limi.net:80/about', '20100125023558')
    row = load_sources()[result.source_id]
    assert row.archive_url == 'https://web.archive.org/web/20100125023558/http://limi.net:80/about'
    assert row.url == 'http://limi.net:80/about'
    assert row.date == datetime.date(2010, 1, 25)
    assert session.requests == [raw_url]
    assert '20100125023558id_/' in session.requests[0]


def test_archived_page_dates_by_capture_and_notes_the_page_date(web):
    raw_url = 'https://web.archive.org/web/20100125023558id_/http://limi.net:80/about'
    fetcher, _ = web({raw_url: FakeResponse(body=ARTICLE)})
    result = capture('https://web.archive.org/web/20100125023558/http://limi.net:80/about',
                     ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    row = load_sources()[result.source_id]
    assert row.date == datetime.date(2010, 1, 25)
    assert row.notes == 'page shows date 2015-03-12'


def test_archived_page_with_given_date(web):
    raw_url = 'https://web.archive.org/web/20100125023558id_/http://limi.net:80/about'
    fetcher, _ = web({raw_url: FakeResponse(body=UNDATED)})
    result = capture('https://web.archive.org/web/20100125023558/http://limi.net:80/about',
                     ['He works for Zest Software'], date=datetime.date(2009, 5, 1), fetcher=fetcher, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.date, row.notes) == (datetime.date(2009, 5, 1), None)


def test_dead_live_url_falls_back_to_nearest_capture(web):
    dead = 'https://ploneconf2009.org/x'
    availability = 'https://archive.org/wayback/available?url=https%3A%2F%2Fploneconf2009.org%2Fx'
    closest = {'archived_snapshots': {'closest': {
        'available': True, 'timestamp': '20091001000000',
        'url': 'http://web.archive.org/web/20091001000000/http://ploneconf2009.org/x'}}}
    raw_url = 'https://web.archive.org/web/20091001000000id_/http://ploneconf2009.org/x'
    fetcher, session = web({dead: FakeResponse(404, b'gone'),
                            availability: FakeResponse(body=json.dumps(closest).encode(),
                                                       content_type='application/json'),
                            raw_url: FakeResponse(body=UNDATED)})
    result = capture(dead, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert session.requests == [dead, availability, raw_url]
    assert result.unreachable is False
    assert result.source_id == source_id('http://ploneconf2009.org/x', '20091001000000')
    row = load_sources()[result.source_id]
    assert row.archive_url == 'https://web.archive.org/web/20091001000000/http://ploneconf2009.org/x'
    assert row.date == datetime.date(2009, 10, 1)
    assert passages(result.source_id) == [PARAGRAPH]


def test_dead_url_without_capture_is_unreachable(web):
    dead = 'https://ploneconf2009.org/x'
    availability = 'https://archive.org/wayback/available?url=https%3A%2F%2Fploneconf2009.org%2Fx'
    fetcher, _ = web({dead: FakeResponse(410, b'gone'),
                      availability: FakeResponse(body=b'{"archived_snapshots": {}}',
                                                 content_type='application/json')})
    result = capture(dead, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    sid = source_id(dead)
    assert result == CaptureResult(sid, True, (), ('He works for Zest Software',), True)
    row = load_sources()[sid]
    assert row.notes == 'could not be fetched on 2026-10-22'
    assert row.title == dead
    assert row.date == datetime.date(2026, 10, 22)
    assert read_excerpt(sid) == 'could not be fetched on 2026-10-22\n'


def test_fetch_error_becomes_capture_error(web):
    fetcher, _ = web({URL: FakeResponse(403, b'forbidden')})
    with pytest.raises(CaptureError, match='example.org/sprint'):
        capture(URL, ['Zest'], fetcher=fetcher, run=no_run)
    assert load_sources() == {}


def test_pdf_is_kind_pdf(web):
    url = 'https://example.org/report.pdf'
    fetcher, _ = web({url: FakeResponse(body=b'%PDF-1.4', content_type='application/pdf')})

    class Done:
        stdout = 'First paragraph.\n\nJane works for Acme.\n'.encode()

    result = capture(url, ['works for Acme'], fetcher=fetcher, run=lambda cmd, **kwargs: Done())
    row = load_sources()[result.source_id]
    assert row.kind == 'pdf'
    assert row.title == url
    assert row.date == datetime.date(2026, 10, 22)
    assert result.added == ('Jane works for Acme.',)


def test_extract_error_becomes_capture_error(web):
    url = 'https://example.org/report.pdf'
    fetcher, _ = web({url: FakeResponse(body=b'%PDF-1.4', content_type='application/pdf')})

    def run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with pytest.raises(CaptureError, match='pdftotext'):
        capture(url, ['x'], fetcher=fetcher, run=run)
    assert load_sources() == {}


PROFILE_API = 'https://api.github.com/users/fredvd'


def test_github_profile(web):
    fetcher, _ = web(session=NoNetwork())
    profile = {'name': 'Fred van Dijk', 'company': 'Zest Software', 'bio': 'Plone developer'}
    session = FakeSession({PROFILE_API: FakeResponse(body=json.dumps(profile).encode())})
    result = capture('https://github.com/fredvd', ['Zest Software'], fetcher=fetcher, session=session, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.kind, row.title, row.date, row.fetched) == ('profile', 'Fred van Dijk', NOW.date(), NOW)
    assert result.added == ('Name: Fred van Dijk\nCompany: Zest Software\nBio: Plone developer',)


def test_github_profile_needs_a_token(web, monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    fetcher, _ = web(session=NoNetwork())
    with pytest.raises(CaptureError, match='GITHUB_TOKEN'):
        capture('https://github.com/fredvd', ['Zest'], fetcher=fetcher, run=no_run)


def test_github_session_is_built_from_the_environment(web, monkeypatch):
    from scripts.lib import capture as capture_module
    monkeypatch.setenv('GITHUB_TOKEN', 'secret')
    session = capture_module.github_session()
    built = session.session
    assert built.headers['Authorization'] == 'token secret'
    assert built.headers['Accept'] == 'application/vnd.github+json'
    assert built.headers['User-Agent'] == fetch_module.USER_AGENT


def test_deleted_github_user_falls_back_to_nearest_capture(web):
    availability = 'https://archive.org/wayback/available?url=https%3A%2F%2Fgithub.com%2Fgone'
    closest = {'archived_snapshots': {'closest': {
        'available': True, 'timestamp': '20150101000000',
        'url': 'http://web.archive.org/web/20150101000000/https://github.com/gone'}}}
    raw_url = 'https://web.archive.org/web/20150101000000id_/https://github.com/gone'
    fetcher, requests = web({availability: FakeResponse(body=json.dumps(closest).encode()),
                             raw_url: FakeResponse(body=UNDATED)})
    session = FakeSession({'https://api.github.com/users/gone': FakeResponse(404, b'{"message": "Not Found"}')})
    result = capture('https://github.com/gone', ['Zest Software'], fetcher=fetcher, session=session, run=no_run)
    assert result.source_id == source_id('https://github.com/gone', '20150101000000')
    row = load_sources()[result.source_id]
    assert row.kind == 'profile'
    assert row.archive_url == 'https://web.archive.org/web/20150101000000/https://github.com/gone'
    assert result.added == (PARAGRAPH,)


def test_github_server_error_is_not_unreachable(web):
    fetcher, _ = web(session=NoNetwork())
    session = FakeSession({PROFILE_API: FakeResponse(401, b'{"message": "Bad credentials"}')})
    with pytest.raises(CaptureError, match='401'):
        capture('https://github.com/fredvd', ['Zest'], fetcher=fetcher, session=session, run=no_run)
    assert load_sources() == {}


def test_commit_from_api(web):
    fetcher, _ = web(session=NoNetwork())
    api = 'https://api.github.com/repos/plone/Products.CMFPlone/commits/abc123'
    commit = {'commit': {'author': {'name': 'Jane', 'email': 'jane@example.org', 'date': '2012-05-06T07:08:09Z'},
                         'message': 'Fix the release process'}}
    session = FakeSession({api: FakeResponse(body=json.dumps(commit).encode())})
    result = capture('https://github.com/plone/Products.CMFPlone/commit/abc123', ['Fix the release'],
                     fetcher=fetcher, session=session, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.kind, row.date, row.title) == ('commit', datetime.date(2012, 5, 6),
                                               'https://github.com/plone/Products.CMFPlone/commit/abc123')
    assert result.added == ('Fix the release process',)


def test_video_uses_one_workdir_per_source(web):
    fetcher, _ = web(session=NoNetwork())
    url = 'https://www.youtube.com/watch?v=abc'
    sid = source_id(url)
    workdirs = []

    class Done:
        def __init__(self, stdout=b''):
            self.stdout = stdout

    def run(cmd, **kwargs):
        if '--print' in cmd:
            return Done(b'A talk\n')
        workdir = os.path.dirname(cmd[cmd.index('-o') + 1])
        workdirs.append(workdir)
        with open(os.path.join(workdir, 'abc.en.vtt'), 'w', encoding='utf-8') as handle:
            handle.write('WEBVTT\n\n00:01:02.000 --> 00:01:04.000\nI work for Zest Software\n')
        return Done()

    result = capture(url, ['work for Zest'], fetcher=fetcher, run=run)
    assert workdirs == [os.path.join(fetch_module.CACHE_DIR, 'video', sid)]
    row = load_sources()[sid]
    assert (row.kind, row.title, row.date) == ('video', 'A talk', NOW.date())
    assert result.added == ('[01:02] I work for Zest Software',)


def test_refresh_keeps_the_row_but_its_fetch_time(web, monkeypatch):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['Zest Software'], title='Mine', fetcher=fetcher, run=no_run)
    later = NOW.replace(year=2027)
    monkeypatch.setattr(fetch_module, 'now', lambda: later)
    again, session = web({URL: FakeResponse(body=ARTICLE.replace(b'Plone sprint report', b'Other'))})
    again.refresh = True
    result = capture(URL, ['Zest Software'], refresh=True, fetcher=again, run=no_run)
    assert session.requests == [URL]
    assert result.created is False
    row = load_sources()[source_id(URL)]
    assert (row.title, row.fetched) == ('Mine', later)


def test_deleted_commit_without_capture_is_unreachable(web):
    url = 'https://github.com/plone/gone/commit/abc123'
    availability = 'https://archive.org/wayback/available?url=https%3A%2F%2Fgithub.com%2Fplone%2Fgone%2Fcommit%2Fabc123'
    fetcher, _ = web({availability: FakeResponse(body=b'{"archived_snapshots": {}}')})
    session = FakeSession({'https://api.github.com/repos/plone/gone/commits/abc123':
                           FakeResponse(404, b'{"message": "Not Found"}')})
    result = capture(url, ['Fix'], fetcher=fetcher, session=session, run=no_run)
    assert result == CaptureResult(source_id(url), True, (), ('Fix',), True)
    row = load_sources()[result.source_id]
    assert (row.kind, row.notes) == ('commit', 'could not be fetched on 2026-10-22')


def test_volto_page_is_read_from_its_api(web):
    url = 'https://plone.org/foundation/members/jane'
    paragraph = {'type': 'p', 'children': [{'text': 'Jane works for Acme.'}]}
    page = {'title': 'Jane Doe', 'effective': '2021-04-05T00:00:00',
            'blocks': {'a': {'@type': 'slate', 'value': [paragraph]}}, 'blocks_layout': {'items': ['a']}}
    fetcher, session = web({url: FakeResponse(body=b'<html><body>loading</body></html>'),
                            'https://plone.org/++api++/foundation/members/jane':
                            FakeResponse(body=json.dumps(page).encode(), content_type='application/json')})
    result = capture(url, ['works for Acme'], fetcher=fetcher, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.kind, row.title, row.date) == ('page', 'Jane Doe', datetime.date(2021, 4, 5))
    assert result.added == ('Jane works for Acme.',)


def test_archived_copy_that_is_gone_is_unreachable(web):
    raw_url = 'https://web.archive.org/web/20100125023558id_/http://limi.net/about'
    fetcher, session = web({raw_url: FakeResponse(404, b'')})
    result = capture('https://web.archive.org/web/20100125023558/http://limi.net/about', ['x'],
                     fetcher=fetcher, run=no_run)
    assert session.requests == [raw_url]  # no search for another capture
    assert result.unreachable is True
    row = load_sources()[result.source_id]
    assert row.archive_url == 'https://web.archive.org/web/20100125023558/http://limi.net/about'
    assert row.date == datetime.date(2010, 1, 25)


def test_new_source_without_quotes_is_refused(web):
    fetcher, session = web({URL: FakeResponse(body=ARTICLE)})
    with pytest.raises(CaptureError, match='at least one quote'):
        capture(URL, [], fetcher=fetcher, run=no_run)
    assert session.requests == []
    assert load_sources() == {}
