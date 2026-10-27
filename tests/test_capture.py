import datetime
import json
import os
import pathlib
import subprocess

import pytest

from scripts.lib.addresses import mask_address
from scripts.lib.capture import CaptureError, CaptureResult, capture, capture_commit
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
    def __init__(self, status=200, body=b'', content_type='text/html; charset=utf-8', url=None):
        if url is not None:
            self.url = url
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
    assert result.added == ('Login: fredvd\nName: Fred van Dijk\nCompany: Zest Software\nBio: Plone developer',)


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
    commit = {'commit': {'author': {'name': 'Jane', 'email': 'jane@acme.test', 'date': '2012-05-06T07:08:09Z'},
                         'message': 'Fix the release process'}}
    session = FakeSession({api: FakeResponse(body=json.dumps(commit).encode())})
    result = capture('https://github.com/plone/Products.CMFPlone/commit/abc123', ['Fix the release'],
                     fetcher=fetcher, session=session, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.kind, row.date, row.title) == ('commit', datetime.date(2012, 5, 6),
                                               'https://github.com/plone/Products.CMFPlone/commit/abc123')
    masked = mask_address('jane@acme.test', keep_domain=True)
    assert result.added == (f'Author: Jane <{masked}>\nDate: 2012-05-06T07:08:09Z\n\nFix the release process',)


def test_capture_commit_cites_the_author_line(web):
    fetcher, _ = web(session=NoNetwork())
    api = 'https://api.github.com/repos/acme/site/commits/abc123'
    commit = {'commit': {'author': {'name': 'Jane', 'email': 'jane@acme.test', 'date': '2012-05-06T07:08:09Z'},
                         'message': 'Fix the release process'}}
    session = FakeSession({api: FakeResponse(body=json.dumps(commit).encode())})
    url = 'https://github.com/acme/site/commit/abc123'
    masked = mask_address('jane@acme.test', keep_domain=True)
    assert capture_commit(url, 'JANE@acme.test', fetcher=fetcher, session=session, run=no_run) == (
        source_id(url), f'Author: Jane <{masked}>')
    assert 'jane@acme.test' not in read_excerpt(source_id(url))
    # Captured once: the second call reads the register
    assert capture_commit(url, 'jane@acme.test', fetcher=fetcher, session=NoNetwork(), run=no_run) == (
        source_id(url), f'Author: Jane <{masked}>')
    # Without an address (the commit search found it in an organisation) the commit is stored whole, no snippet
    other = 'https://github.com/acme/site/commit/def456'
    session.pages['https://api.github.com/repos/acme/site/commits/def456'] = FakeResponse(body=json.dumps(
        {'commit': {**commit['commit'], 'message': 'Another'}}).encode())
    assert capture_commit(other, '', names=['Jane'], fetcher=fetcher, session=session, run=no_run) == (
        source_id(other), None)
    assert read_excerpt(source_id(other)).startswith(f'Author: Jane <{masked}>')


def test_capture_masks_page_addresses(web):
    page = b'<html><head><title>Contact</title></head><body><p>Email: jane@acme.test is the contact.</p></body></html>'
    fetcher, _ = web({URL: FakeResponse(body=page)})
    masked = mask_address('jane@acme.test', keep_domain=True)
    result = capture(URL, ['Email: jane@acme.test'], fetcher=fetcher, run=no_run)
    assert result.missing == ()
    assert masked.endswith('@acme.test')
    assert f'Email: {masked}' in read_excerpt(source_id(URL))
    assert 'jane@acme.test' not in read_excerpt(source_id(URL))
    # The raw quote is recognised as stored the second time
    assert capture(URL, ['Email: jane@acme.test'], fetcher=NoNetwork(), run=no_run).added == ()


def test_capture_masks_the_title_of_the_source_row(web):
    page = (b'<html><head><title>Contact jane@acme.test</title></head><body><p>Email: jane@acme.test is the '
            b'contact.</p></body></html>')
    fetcher, _ = web({URL: FakeResponse(body=page)})
    capture(URL, ['Email: jane@acme.test'], fetcher=fetcher, run=no_run)
    title = load_sources()[source_id(URL)].title
    assert title == f"Contact {mask_address('jane@acme.test')}"
    assert '@' not in title


def test_capture_masks_the_title_given_by_the_user(web):
    page = b'<html><head><title>Contact</title></head><body><p>Email: jane@acme.test is the contact.</p></body></html>'
    fetcher, _ = web({URL: FakeResponse(body=page)})
    capture(URL, ['Email: jane@acme.test'], title='Mail from jane@acme.test', fetcher=fetcher, run=no_run)
    assert load_sources()[source_id(URL)].title == f"Mail from {mask_address('jane@acme.test')}"


def test_capture_masks_a_general_service_address_completely(web):
    page = b'<html><head><title>Contact</title></head><body><p>Email: jane@gmx.test is the contact.</p></body></html>'
    fetcher, _ = web({URL: FakeResponse(body=page)})
    masked = mask_address('jane@gmx.test', keep_domain=True)
    assert '@' not in masked
    result = capture(URL, ['Email: jane@gmx.test'], fetcher=fetcher, run=no_run)
    assert result.missing == ()
    assert f'Email: {masked}' in read_excerpt(source_id(URL))
    assert 'gmx' not in read_excerpt(source_id(URL))


def test_capture_commit_fails_for_an_unreachable_commit(web):
    url = 'https://github.com/plone/gone/commit/abc123'
    availability = 'https://archive.org/wayback/available?url=https%3A%2F%2Fgithub.com%2Fplone%2Fgone%2Fcommit%2Fabc123'
    fetcher, _ = web({availability: FakeResponse(body=b'{"archived_snapshots": {}}')})
    session = FakeSession({'https://api.github.com/repos/plone/gone/commits/abc123':
                           FakeResponse(404, b'{"message": "Not Found"}')})
    with pytest.raises(CaptureError, match='could not be fetched'):
        capture_commit(url, 'jane@acme.test', fetcher=fetcher, session=session, run=no_run)


def test_video_tracks_are_kept_per_video(web, monkeypatch):
    """The tracks are kept in one folder per video, by its YouTube id; another address of the video reads them
    without asking YouTube, and --refresh asks again."""
    fetcher, _ = web(session=NoNetwork())
    url = 'https://www.youtube.com/watch?v=abcdefghijk'
    sid = source_id(url)
    workdirs = []

    class Done:
        def __init__(self, stdout=b''):
            self.stdout = stdout

    def run(cmd, **kwargs):
        if '--print' in cmd:
            return Done(b'A talk\n')
        download = os.path.dirname(cmd[cmd.index('-o') + 1])
        workdirs.append(os.path.dirname(download))
        with open(os.path.join(download, 'abc.en-orig.vtt'), 'w', encoding='utf-8') as handle:
            handle.write('WEBVTT\n\n00:01:02.000 --> 00:01:04.000\nI work for Zest Software\n'
                         '\n00:01:04.000 --> 00:01:06.000\nand Plone\n')
        return Done()

    def no_run(cmd, **kwargs):
        raise AssertionError(f'yt-dlp was called: {cmd}')

    result = capture(url, ['work for Zest'], fetcher=fetcher, run=run)
    assert workdirs == [os.path.join(os.environ['PLONE_STATS_CACHE'], 'sources', 'video', 'abcdefghijk')]
    row = load_sources()[sid]
    assert (row.kind, row.title, row.date) == ('video', 'A talk', NOW.date())
    assert result.added == ('[01:02] I work for Zest Software\n[01:04] and Plone',)

    # a read from the kept tracks is as old as their download, as a page read from the cache
    monkeypatch.setattr(fetch_module, 'now', lambda: NOW + datetime.timedelta(days=3))
    other = capture('https://youtu.be/abcdefghijk', ['and Plone'], fetcher=fetcher, run=no_run)
    assert other.source_id != sid and other.added == ('[01:02] I work for Zest Software\n[01:04] and Plone',)
    row = load_sources()[other.source_id]
    assert (row.title, row.fetched, row.date) == ('A talk', NOW, NOW.date())

    capture(url, ['work for Zest'], refresh=True, fetcher=fetcher, run=run)
    assert len(workdirs) == 2


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


def test_video_quote_in_another_track_is_cut_from_that_track(web):
    fetcher, _ = web(session=NoNetwork())
    url = 'https://www.youtube.com/watch?v=abcdefghijk'
    tracks = {'abc.en-orig.vtt': 'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nI work for Zest Software\n',
              'abc.de.vtt': 'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nIch arbeite bei Zest Software\n'}

    class Done:
        stdout = b'A talk\n'

    def run(cmd, **kwargs):
        if '--print' not in cmd:
            workdir = os.path.dirname(cmd[cmd.index('-o') + 1])
            for name, text in tracks.items():
                with open(os.path.join(workdir, name), 'w', encoding='utf-8') as handle:
                    handle.write(text)
        return Done()

    result = capture(url, ['arbeite bei Zest'], fetcher=fetcher, run=run)
    assert result.added == ('[00:01] Ich arbeite bei Zest Software',)


def test_new_source_without_any_quote_found_stores_nothing(web, tmp_repo):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['not on the page', 'nor this'], fetcher=fetcher, run=no_run)
    assert result == CaptureResult(source_id(URL), False, (), ('not on the page', 'nor this'), False)
    assert load_sources() == {}
    assert not any((tmp_repo / 'curated' / 'sources' / 'excerpts').glob('*.md'))


def test_known_source_with_a_missing_quote_stays_as_it_is(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['Zest Software'], fetcher=fetcher, run=no_run)
    before = load_sources()
    result = capture(URL, ['not on the page'], fetcher=fetcher, run=no_run)
    assert result == CaptureResult(source_id(URL), False, (), ('not on the page',), False)
    assert load_sources() == before
    assert passages(source_id(URL)) == [PARAGRAPH]


def test_commit_quote_in_the_message_keeps_author_and_date(web):
    """A commit is short: the passage is the whole text, so the author and the date stay with the message."""
    fetcher, _ = web(session=NoNetwork())
    api = 'https://api.github.com/repos/plone/plone.api/commits/abc123'
    message = 'Fix the release process\n\nJane works for Acme on this.'
    commit = {'commit': {'author': {'name': 'Jane', 'email': 'jane@acme.test', 'date': '2012-05-06T07:08:09Z'},
                         'message': message}}
    session = FakeSession({api: FakeResponse(body=json.dumps(commit).encode())})
    result = capture('https://github.com/plone/plone.api/commit/abc123', ['works for Acme'],
                     fetcher=fetcher, session=session, run=no_run)
    masked = mask_address('jane@acme.test', keep_domain=True)
    assert result.added == (f'Author: Jane <{masked}>\nDate: 2012-05-06T07:08:09Z\n\n{message}',)


def test_profile_passage_is_the_whole_profile(web):
    fetcher, _ = web(session=NoNetwork())
    profile = {'name': 'Fred van Dijk', 'bio': 'Plone developer\n\nWorks for Zest'}
    session = FakeSession({PROFILE_API: FakeResponse(body=json.dumps(profile).encode())})
    result = capture('https://github.com/fredvd', ['Works for Zest'], fetcher=fetcher, session=session, run=no_run)
    assert result.added == ('Login: fredvd\nName: Fred van Dijk\nBio: Plone developer\n\nWorks for Zest',)


@pytest.mark.parametrize('url', [
    'https://web.archive.org/web/2015/https://plone.org/foundation',
    'https://web.archive.org/web/20150312/https://plone.org/foundation',
    'http://web.archive.org/web/2015*/https://plone.org/foundation',
])
def test_wayback_address_without_a_full_timestamp_is_refused(web, url):
    fetcher, session = web({})
    with pytest.raises(CaptureError, match='full 14-digit capture'):
        capture(url, ['Plone'], fetcher=fetcher, run=no_run)
    assert session.requests == []
    assert load_sources() == {}


def test_redirected_capture_is_recorded_under_its_own_timestamp(web):
    asked = 'https://web.archive.org/web/20100101000000id_/http://a.org/x'
    served = 'https://web.archive.org/web/20100125023558id_/http://a.org/x'
    fetcher, _ = web({asked: FakeResponse(body=ARTICLE, url=served)})
    result = capture('https://web.archive.org/web/20100101000000/http://a.org/x',
                     ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    sid = source_id('http://a.org/x', '20100125023558')
    assert result.source_id == sid
    row = load_sources()[sid]
    assert row.archive_url == 'https://web.archive.org/web/20100125023558/http://a.org/x'
    assert row.date == datetime.date(2010, 1, 25)
    assert source_id('http://a.org/x', '20100101000000') not in load_sources()


def test_capture_of_another_page_is_noted(web):
    asked = 'https://web.archive.org/web/20100101000000id_/http://a.org/x'
    served = 'https://web.archive.org/web/20100125023558id_/http://www.a.org/start'
    fetcher, _ = web({asked: FakeResponse(body=UNDATED, url=served)})
    result = capture('https://web.archive.org/web/20100101000000/http://a.org/x',
                     ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert result.source_id == source_id('http://a.org/x', '20100125023558')
    row = load_sources()[result.source_id]
    assert row.url == 'http://a.org/x'  # the page that was asked for
    assert row.notes == 'served https://web.archive.org/web/20100125023558/http://www.a.org/start'


def test_capture_of_the_same_page_in_another_spelling_is_not_noted(web):
    asked = 'https://web.archive.org/web/20100101000000id_/http://a.org/x'
    served = 'https://web.archive.org/web/20100125023558id_/https://a.org/x/'
    fetcher, _ = web({asked: FakeResponse(body=UNDATED, url=served)})
    result = capture('https://web.archive.org/web/20100101000000/http://a.org/x',
                     ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert load_sources()[result.source_id].notes is None


def issue_pages(owner_repo, number=5):
    api = f'https://api.github.com/repos/{owner_repo}'
    issue = {'title': 'Map Fred', 'user': {'login': 'jane'}, 'created_at': '2026-10-01T00:00:00Z',
             'body': 'Please map Fred.\n\nHe works for Zest Software.'}
    comments = [{'user': {'login': 'bob'}, 'created_at': '2026-10-02T00:00:00Z', 'body': 'Unrelated remark.'},
                {'user': {'login': 'amy'}, 'created_at': '2026-10-03T00:00:00Z',
                 'body': 'Confirmed: Fred is at kitconcept.'}]
    return {f'{api}/issues/{number}': FakeResponse(body=json.dumps(issue).encode()),
            f'{api}/issues/{number}/comments': FakeResponse(body=json.dumps(comments).encode())}


def test_own_repository_issue_is_stored_whole(web):
    fetcher, _ = web(session=NoNetwork())
    session = FakeSession(issue_pages('Plone/Plone-Contributor-Statistics'))
    result = capture('https://github.com/Plone/Plone-Contributor-Statistics/issues/5', ['Confirmed: Fred is at'],
                     fetcher=fetcher, session=session, run=no_run)
    row = load_sources()[result.source_id]
    assert (row.kind, row.title, row.date) == ('issue-comment', 'Map Fred', datetime.date(2026, 10, 1))
    assert len(result.added) == 1
    assert result.added[0].startswith('Title: Map Fred\nAuthor: jane') and 'Unrelated remark.' in result.added[0]


def test_other_repository_issue_stores_the_block(web):
    fetcher, _ = web(session=NoNetwork())
    session = FakeSession(issue_pages('plone/Products.CMFPlone'))
    result = capture('https://github.com/plone/Products.CMFPlone/issues/5', ['Fred is at kitconcept'],
                     fetcher=fetcher, session=session, run=no_run)
    # the comment's paragraph with its author and date, not the issue or the other comments
    assert result.added == ('Author: amy\nDate: 2026-10-03T00:00:00Z\n\nConfirmed: Fred is at kitconcept.',)


def test_other_repository_issue_keeps_the_author_with_a_name(web):
    fetcher, _ = web(session=NoNetwork())
    session = FakeSession(issue_pages('plone/Products.CMFPlone'))
    result = capture('https://github.com/plone/Products.CMFPlone/issues/5', names=['zest software'],
                     fetcher=fetcher, session=session, run=no_run)
    assert result.added == ('Author: jane\nDate: 2026-10-01T00:00:00Z\n\nHe works for Zest Software.',)


def test_other_repository_comment_by_fragment_keeps_its_author(web):
    fetcher, _ = web(session=NoNetwork())
    api = 'https://api.github.com/repos/plone/volto/issues/comments/12'
    body = 'Thanks.\n\nI work for kitconcept now.'
    comment = {'user': {'login': 'fredvd'}, 'created_at': '2020-05-01T08:00:00Z', 'body': body}
    session = FakeSession({api: FakeResponse(body=json.dumps(comment).encode())})
    result = capture('https://github.com/plone/volto/pull/7#issuecomment-12', ['I work for kitconcept'],
                     fetcher=fetcher, session=session, run=no_run)
    assert result.added == ('Author: fredvd\nDate: 2020-05-01T08:00:00Z\n\nI work for kitconcept now.',)


def test_own_repository_comment_by_fragment(web):
    fetcher, _ = web(session=NoNetwork())
    api = 'https://api.github.com/repos/plone/plone-contributor-statistics/issues/comments/6297324385'
    comment = {'user': {'login': 'jensens'}, 'created_at': '2026-10-20T08:00:00Z', 'body': 'Decided: leave unmapped.'}
    session = FakeSession({api: FakeResponse(body=json.dumps(comment).encode())})
    url = 'https://github.com/plone/plone-contributor-statistics/pull/153#issuecomment-6297324385'
    result = capture(url, ['leave unmapped'], fetcher=fetcher, session=session, run=no_run)
    assert result.source_id == source_id(url) != source_id(url.split('#')[0])
    assert result.added == ('Author: jensens\nDate: 2026-10-20T08:00:00Z\n\nDecided: leave unmapped.',)


def test_deleted_issue_without_capture_is_unreachable(web):
    availability = ('https://archive.org/wayback/available?url='
                    'https%3A%2F%2Fgithub.com%2Fplone%2Fgone%2Fissues%2F5')
    fetcher, _ = web({availability: FakeResponse(body=b'{"archived_snapshots": {}}')})
    api = 'https://api.github.com/repos/plone/gone/issues/5'
    session = FakeSession({api: FakeResponse(404, b'{"message": "Not Found"}')})
    result = capture('https://github.com/plone/gone/issues/5', ['x'], fetcher=fetcher, session=session, run=no_run)
    assert result.unreachable
    assert load_sources()[result.source_id].kind == 'issue-comment'


def test_names_cut_the_passage_when_no_quote_is_given(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, names=['maurits van rees', 'Nobody Known'], fetcher=fetcher, run=no_run)
    assert result.added == (PARAGRAPH,)
    assert result.missing == ('Nobody Known',)
    assert passages(result.source_id) == [PARAGRAPH]


def test_new_source_without_a_found_name_stores_nothing(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, names=['Nobody Known'], fetcher=fetcher, run=no_run)
    assert result.missing == ('Nobody Known',)
    assert load_sources() == {}


def test_names_are_ignored_when_a_quote_is_found(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['Zest Software', 'Not on the page'], names=['Nobody Known'], fetcher=fetcher,
                     run=no_run)
    assert result.added == (PARAGRAPH,)
    assert result.missing == ('Not on the page',)


def test_names_decide_when_no_quote_is_found(web):
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['Not on the page'], names=['maurits van rees', 'Nobody Known'], fetcher=fetcher,
                     run=no_run)
    assert result.added == (PARAGRAPH,)
    assert result.missing == ('Not on the page', 'Nobody Known')
    assert passages(result.source_id) == [PARAGRAPH]


def test_whole_text_when_no_quote_is_found_and_names_are_given(web):
    fetcher, _ = web(session=NoNetwork())
    profile = {'name': None, 'login': 'fredvd', 'bio': 'Plone developer'}
    session = FakeSession({PROFILE_API: FakeResponse(body=json.dumps(profile).encode())})
    result = capture('https://github.com/fredvd', ['Not in the profile'], names=['Fred van Dijk'],
                     fetcher=fetcher, session=session, run=no_run)
    assert len(result.added) == 1 and 'Plone developer' in result.added[0]
    assert result.missing == ('Not in the profile',)


def test_profile_with_name_stores_whole_text(web):
    fetcher, _ = web(session=NoNetwork())
    profile = {'name': None, 'login': 'fredvd', 'bio': 'Plone developer'}
    session = FakeSession({PROFILE_API: FakeResponse(body=json.dumps(profile).encode())})
    result = capture('https://github.com/fredvd', names=['Fred van Dijk'], fetcher=fetcher, session=session,
                     run=no_run)
    assert len(result.added) == 1 and 'Plone developer' in result.added[0]
    assert result.missing == ()


def uncaptured_source(url, notes, timestamp=None, kind='video'):
    """A source that the capture did not read: the address as its title, the note as its only passage."""
    from scripts.lib.model import Source, archive_url_of, write_source
    from scripts.lib.model.sources import replace_excerpt, split_archive_url

    split = split_archive_url(url)
    original = split[0] if split else url
    sid = source_id(original, timestamp)
    write_source(Source(sid, kind, url, datetime.date(2026, 10, 22), original,
                        archive_url_of(original, timestamp) if timestamp else None,
                        datetime.datetime(2026, 10, 22, 22, 29, tzinfo=datetime.UTC), notes))
    replace_excerpt(sid, notes)
    return sid


def test_capturing_an_uncaptured_source_renews_it(web):
    sid = uncaptured_source(URL, 'not captured on 2026-10-22: rate limited (HTTP 429)', kind='page')
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert result == CaptureResult(sid, False, (PARAGRAPH,), (), False)
    row = load_sources()[sid]
    assert (row.kind, row.title, row.date, row.url, row.fetched, row.notes) == (
        'page', 'Plone sprint report', datetime.date(2015, 3, 12), URL, NOW, None)
    assert read_excerpt(sid) == PARAGRAPH + '\n'


def test_renewing_keeps_a_curated_kind_over_a_generic_page(web):
    sid = uncaptured_source(URL, 'not captured on 2026-10-22: nothing found', kind='speaker-page')
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    row = load_sources()[sid]
    assert (row.kind, row.title, row.notes) == ('speaker-page', 'Plone sprint report', None)


def test_renewing_takes_a_given_kind(web):
    sid = uncaptured_source(URL, 'not captured on 2026-10-22: nothing found', kind='speaker-page')
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    capture(URL, ['He works for Zest Software'], kind='register', fetcher=fetcher, run=no_run)
    assert load_sources()[sid].kind == 'register'


def test_renewing_takes_a_specific_kind_of_the_read(web):
    url = 'https://www.youtube.com/watch?v=abcdefghijk'
    sid = uncaptured_source(url, 'not captured on 2026-10-22: rate limited (HTTP 429)', kind='speaker-page')
    fetcher, _ = web(session=NoNetwork())

    class Done:
        stdout = b'A talk\n'

    def run(cmd, **kwargs):
        if '--print' not in cmd:
            workdir = os.path.dirname(cmd[cmd.index('-o') + 1])
            with open(os.path.join(workdir, 'abc.en-orig.vtt'), 'w', encoding='utf-8') as handle:
                handle.write('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nI work for Zest Software\n')
        return Done()

    capture(url, ['work for Zest'], fetcher=fetcher, run=run)
    assert load_sources()[sid].kind == 'video'


def test_capturing_an_unfetched_archived_copy_renews_it_with_the_notes_of_the_read(web):
    archived = 'https://web.archive.org/web/20100125023558/http://limi.net/about'
    sid = uncaptured_source(archived, 'could not be fetched on 2026-10-01', timestamp='20100125023558', kind='page')
    raw_url = 'https://web.archive.org/web/20100125023558id_/http://limi.net/about'
    fetcher, _ = web({raw_url: FakeResponse(body=ARTICLE)})
    result = capture(archived, ['He works for Zest Software'], fetcher=fetcher, run=no_run)
    assert result == CaptureResult(sid, False, (PARAGRAPH,), (), False)
    row = load_sources()[sid]
    assert (row.title, row.date, row.archive_url, row.notes) == (
        'Plone sprint report', datetime.date(2010, 1, 25), archived, 'page shows date 2015-03-12')
    assert passages(sid) == [PARAGRAPH]


def test_an_uncaptured_source_is_read_again_for_names(web):
    # The capture does not skip a known source whose excerpt holds only the note
    sid = uncaptured_source(URL, 'not captured on 2026-10-22: nothing found', kind='page')
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, names=['Maurits van Rees'], fetcher=fetcher, run=no_run)
    assert result.added == (PARAGRAPH,)
    assert load_sources()[sid].notes is None


def test_an_uncaptured_source_without_a_found_quote_stays_uncaptured(web):
    sid = uncaptured_source(URL, 'not captured on 2026-10-22: nothing found', kind='page')
    before = load_sources()[sid]
    fetcher, _ = web({URL: FakeResponse(body=ARTICLE)})
    result = capture(URL, ['not on the page'], fetcher=fetcher, run=no_run)
    assert result == CaptureResult(sid, False, (), ('not on the page',), False)
    assert load_sources()[sid] == before
    assert read_excerpt(sid) == 'not captured on 2026-10-22: nothing found\n'


def test_a_video_is_dated_by_its_upload_date(web):
    fetcher, _ = web(session=NoNetwork())
    url = 'https://www.youtube.com/watch?v=abcdefghijk'

    def run(cmd, **kwargs):
        if '--print' in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=b'A talk\nen\n20191023\n', stderr=b'')
        with open(os.path.join(os.path.dirname(cmd[cmd.index('-o') + 1]), 'abc.en-orig.vtt'), 'w',
                  encoding='utf-8') as handle:
            handle.write('WEBVTT\n\n00:01:02.000 --> 00:01:04.000\nI work for Zest Software\n')
        return subprocess.CompletedProcess(cmd, 0, stdout=b'', stderr=b'')
    capture(url, ['work for Zest'], fetcher=fetcher, run=run)
    row = load_sources()[source_id(url)]
    assert (row.date, row.fetched) == (datetime.date(2019, 10, 23), NOW)
