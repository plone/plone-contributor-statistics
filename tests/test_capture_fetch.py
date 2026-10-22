import datetime
import json

import pytest
import requests

from scripts.lib.capture import fetch
from scripts.lib.capture.fetch import FetchError, Fetcher, nearest_capture, raw_capture_url


class FakeResponse:
    def __init__(self, status=200, body=b'hello', content_type='text/html'):
        self.status_code = status
        self.content = body
        self.headers = {'Content-Type': content_type}


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.requests.append(url)
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return item


def make(tmp_path, *responses, **kwargs):
    sleeps = []
    session = FakeSession(*(responses or (FakeResponse(),)))
    fetcher = Fetcher(cache=str(tmp_path), session=session, sleep=sleeps.append, clock=lambda: 100.0, **kwargs)
    return fetcher, session, sleeps


def test_raw_capture_url_uses_id_flag():
    expected = 'https://web.archive.org/web/20100125023558id_/http://limi.net:80/about'
    assert raw_capture_url('https://web.archive.org/web/20100125023558/http://limi.net:80/about') == expected
    assert raw_capture_url('https://web.archive.org/web/20100125023558if_/http://limi.net:80/about') == expected
    assert raw_capture_url(expected) == expected


def test_get_uses_the_cache_and_never_refetches(tmp_path):
    fetcher, session, _ = make(tmp_path)
    first = fetcher.get('https://example.org/a')
    second = fetcher.get('https://example.org/a')
    assert len(session.requests) == 1
    assert first.body == second.body == b'hello'
    assert second.fetched == first.fetched
    fetcher2, session2, _ = make(tmp_path, refresh=True)
    fetcher2.get('https://example.org/a')
    assert len(session2.requests) == 1


def test_cache_hit_returns_original_fetch_time(tmp_path, monkeypatch):
    fixed = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(fetch, 'now', lambda: fixed)
    fetcher, _, _ = make(tmp_path)
    fetcher.get('https://example.org/a')
    monkeypatch.setattr(fetch, 'now', lambda: fixed.replace(year=2030))
    other, session, _ = make(tmp_path)
    assert other.get('https://example.org/a').fetched == fixed
    assert session.requests == []
    meta = [p for p in tmp_path.iterdir() if p.suffix == '.json'][0]
    assert json.loads(meta.read_text())['status'] == 200


def test_wayback_requests_are_paced(tmp_path):
    fetcher, _, sleeps = make(tmp_path)
    fetcher.get('https://web.archive.org/web/20100101000000id_/http://a.org/')
    fetcher.get('https://web.archive.org/web/20100101000000id_/http://b.org/')
    assert sleeps == [4.0]


def test_other_hosts_are_paced_one_second(tmp_path):
    fetcher, _, sleeps = make(tmp_path)
    fetcher.get('https://a.org/')
    fetcher.get('https://b.org/')
    assert sleeps == []
    fetcher.get('https://a.org/x')
    assert sleeps == [1.0]


def test_retries_then_fails(tmp_path):
    fetcher, session, sleeps = make(tmp_path, FakeResponse(503))
    with pytest.raises(FetchError):
        fetcher.get('https://example.org/a')
    assert sleeps == [2, 4, 8, 16]
    assert len(session.requests) == 5


def test_connection_error_is_retried(tmp_path):
    fetcher, session, sleeps = make(tmp_path, requests.exceptions.ConnectionError(), FakeResponse())
    assert fetcher.get('https://example.org/a').status == 200
    assert sleeps == [2]


def test_other_status_fails_at_once(tmp_path):
    fetcher, session, sleeps = make(tmp_path, FakeResponse(403))
    with pytest.raises(FetchError):
        fetcher.get('https://example.org/a')
    assert len(session.requests) == 1 and sleeps == []


def test_404_is_cached_and_returned(tmp_path):
    fetcher, session, _ = make(tmp_path, FakeResponse(404, b'gone'))
    assert fetcher.get('https://example.org/a').status == 404
    assert fetcher.get('https://example.org/a').status == 404
    assert len(session.requests) == 1


def test_sends_the_user_agent(monkeypatch, tmp_path):
    fetcher = Fetcher(cache=str(tmp_path), sleep=lambda s: None, clock=lambda: 0.0)
    assert fetcher.session.headers['User-Agent'] == fetch.USER_AGENT
    assert fetch.USER_AGENT == ('plone-contributor-statistics/1.0 '
                                '(+https://github.com/plone/plone-contributor-statistics)')


def test_nearest_capture(tmp_path):
    body = json.dumps({'archived_snapshots': {'closest': {
        'available': True, 'timestamp': '20091001000000',
        'url': 'http://web.archive.org/web/20091001000000/http://ploneconf2009.org/x'}}}).encode()
    fetcher, session, _ = make(tmp_path, FakeResponse(200, body, 'application/json'))
    assert nearest_capture(fetcher, 'http://ploneconf2009.org/x', '20091001') == \
        'https://web.archive.org/web/20091001000000/http://ploneconf2009.org/x'
    assert session.requests[0].startswith('https://archive.org/wayback/available?url=')
    assert 'timestamp=20091001' in session.requests[0]
    fetcher, _, _ = make(tmp_path / 'b', FakeResponse(200, b'{"archived_snapshots": {}}'))
    assert nearest_capture(fetcher, 'http://x.org/') is None


def test_wayback_retries_keep_the_pace(tmp_path):
    now = [100.0]
    times = []

    class TimedSession(FakeSession):
        def get(self, url, **kwargs):
            times.append(now[0])
            return super().get(url, **kwargs)

    def sleep(seconds):
        now[0] += seconds

    session = TimedSession(FakeResponse(429), FakeResponse(429), FakeResponse())
    fetcher = Fetcher(cache=str(tmp_path), session=session, sleep=sleep, clock=lambda: now[0])
    fetcher.get('https://web.archive.org/web/20100101000000id_/http://a.org/')
    assert len(times) == 3
    assert all(later - earlier >= 4.0 for earlier, later in zip(times, times[1:]))
