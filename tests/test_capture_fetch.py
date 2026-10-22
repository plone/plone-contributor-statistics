import datetime
import json
import os
import subprocess
import tempfile

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


class Timeline:
    """A clock that only moves when the code sleeps; records when each request was sent."""

    def __init__(self, start=1000.0):
        self.now = start
        self.sent = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def fetcher(self, cache, *responses):
        timeline = self

        class Session(FakeSession):
            def get(self, url, **kwargs):
                timeline.sent.append((timeline.now, url))
                return super().get(url, **kwargs)

        return Fetcher(cache=str(cache), session=Session(*(responses or (FakeResponse(),))),
                       sleep=self.sleep, clock=self.clock)


def test_pace_holds_across_fetcher_instances(tmp_path):
    timeline = Timeline()
    timeline.fetcher(tmp_path).get('https://web.archive.org/web/20100101000000id_/http://a.org/')
    timeline.fetcher(tmp_path).get('https://web.archive.org/web/20100101000000id_/http://b.org/')
    (first, _), (second, _) = timeline.sent
    assert second - first >= 4.0


def test_pace_holds_across_processes_through_the_cache(tmp_path):
    """Another process sees the time of the last request in the pace file."""
    first, _, sleeps = make(tmp_path)
    first.get('https://example.org/a')
    assert (tmp_path / 'pace' / 'example.org').is_file()
    second = Fetcher(cache=str(tmp_path), session=FakeSession(FakeResponse()), sleep=sleeps.append,
                     clock=lambda: 100.25)
    second.get('https://example.org/b')
    assert sleeps == [0.75]


def test_internet_archive_hosts_share_one_pace(tmp_path):
    timeline = Timeline()
    body = b'{"archived_snapshots": {}}'
    fetcher = timeline.fetcher(tmp_path, FakeResponse(200, body, 'application/json'), FakeResponse())
    assert nearest_capture(fetcher, 'http://a.org/') is None
    fetcher.get('https://web.archive.org/web/20100101000000id_/http://a.org/')
    (first, availability), (second, capture) = timeline.sent
    assert availability.startswith('https://archive.org/') and capture.startswith('https://web.archive.org/')
    assert second - first >= 4.0


def test_garbled_pace_file_is_ignored(tmp_path):
    (tmp_path / 'pace').mkdir()
    (tmp_path / 'pace' / 'example.org').write_text('not a time')
    fetcher, session, sleeps = make(tmp_path)
    fetcher.get('https://example.org/a')
    assert sleeps == [] and len(session.requests) == 1


def test_pace_from_the_future_waits_at_most_the_pace(tmp_path):
    """A clock that was set back must not block the fetcher for longer than one pace."""
    (tmp_path / 'pace').mkdir()
    (tmp_path / 'pace' / 'archive.org').write_text('99999999.0')
    fetcher, _, sleeps = make(tmp_path)
    fetcher.get('https://web.archive.org/web/20100101000000id_/http://a.org/')
    assert sleeps == [4.0]


def test_retry_after_is_honoured(tmp_path):
    timeline = Timeline()
    limited = FakeResponse(429)
    limited.headers['Retry-After'] = '30'
    fetcher = timeline.fetcher(tmp_path, limited, FakeResponse())
    assert fetcher.get('https://example.org/a').status == 200
    (first, _), (second, _) = timeline.sent
    assert second - first >= 30


def test_retry_after_not_numeric_falls_back_to_backoff(tmp_path):
    limited = FakeResponse(429)
    limited.headers['Retry-After'] = 'Wed, 21 Oct 2026 07:28:00 GMT'
    fetcher, _, sleeps = make(tmp_path, limited, FakeResponse())
    assert fetcher.get('https://example.org/a').status == 200
    assert sleeps == [2]


@pytest.mark.parametrize('error', [
    requests.exceptions.MissingSchema('no scheme'),
    requests.exceptions.InvalidURL('bad'),
    requests.exceptions.TooManyRedirects('loop'),
])
def test_request_errors_that_are_not_retried_become_fetch_errors(tmp_path, error):
    fetcher, session, sleeps = make(tmp_path, error)
    with pytest.raises(FetchError, match=type(error).__name__):
        fetcher.get('https://example.org/a')
    assert len(session.requests) == 1 and sleeps == []


@pytest.mark.parametrize('garbled', ['{"url": ', '{}', '[1, 2]'])
def test_garbled_cache_entry_is_a_miss(tmp_path, garbled):
    fetcher, _, _ = make(tmp_path)
    fetcher.get('https://example.org/a')
    meta = next(p for p in tmp_path.iterdir() if p.suffix == '.json')
    meta.write_text(garbled)
    again, session, _ = make(tmp_path, FakeResponse(body=b'fresh'))
    assert again.get('https://example.org/a').body == b'fresh'
    assert len(session.requests) == 1
    assert json.loads(meta.read_text())['status'] == 200


def test_cache_entry_is_written_atomically(tmp_path, monkeypatch):
    """The metadata goes in last, by renaming a complete file: a crash leaves no half entry behind."""
    fetcher, _, _ = make(tmp_path)
    replaced = []
    real_replace = fetch.os.replace
    monkeypatch.setattr(fetch.os, 'replace', lambda src, dst: (replaced.append(dst), real_replace(src, dst)))
    fetcher.get('https://example.org/a')
    entries = [name for name in replaced if not name.startswith(str(tmp_path / 'pace'))]
    assert [os.path.splitext(name)[1] for name in entries] == ['.body', '.json']
    assert sorted(p.suffix for p in tmp_path.iterdir() if p.is_file()) == ['.body', '.json']


@pytest.mark.parametrize('body', [
    b'<html>Service unavailable</html>',
    b'\xff\xfe not utf-8',
    b'[]',
    b'{"archived_snapshots": []}',
    b'{"archived_snapshots": {"closest": {"available": true, "timestamp": "2009", "url": "http://example.org/x"}}}',
])
def test_nearest_capture_on_a_malformed_answer_is_none(tmp_path, body):
    fetcher, _, _ = make(tmp_path, FakeResponse(200, body, 'application/json'))
    assert nearest_capture(fetcher, 'http://example.org/x') is None


def test_nearest_capture_on_an_error_answer_is_none(tmp_path):
    fetcher, _, _ = make(tmp_path, FakeResponse(404, b'{}'))
    assert nearest_capture(fetcher, 'http://example.org/x') is None


# --- where the cache lives ---


class FakeGit:
    def __init__(self, stdout=None, error=None):
        self.stdout, self.error, self.calls = stdout, error, []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.error is not None:
            raise self.error
        return subprocess.CompletedProcess(command, 0, stdout=self.stdout, stderr='')


def test_cache_root_is_in_the_main_checkout(monkeypatch, tmp_path):
    monkeypatch.delenv(fetch.CACHE_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    git = FakeGit(stdout='/home/me/checkout/.git\n')
    assert fetch.cache_root(run=git) == os.path.join('/home/me/checkout', '.cache')
    assert git.calls[0][0] == ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir']


@pytest.mark.parametrize('error', [subprocess.CalledProcessError(128, 'git'), FileNotFoundError('git')])
def test_cache_root_outside_a_repository_is_the_current_directory(monkeypatch, tmp_path, error):
    monkeypatch.delenv(fetch.CACHE_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    assert fetch.cache_root(run=FakeGit(error=error)) == str(tmp_path / '.cache')


def test_cache_root_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(fetch.CACHE_ENV, str(tmp_path / 'elsewhere'))
    assert fetch.cache_root(run=FakeGit(error=AssertionError('git must not run'))) == str(tmp_path / 'elsewhere')
    assert fetch.cache_dir('sources') == str(tmp_path / 'elsewhere' / 'sources')


def test_default_cache_is_resolved_when_the_fetcher_is_built(monkeypatch, tmp_path):
    monkeypatch.setenv(fetch.CACHE_ENV, str(tmp_path / 'one'))
    assert Fetcher().cache == str(tmp_path / 'one' / 'sources')
    monkeypatch.setenv(fetch.CACHE_ENV, str(tmp_path / 'two'))
    assert Fetcher().cache == str(tmp_path / 'two' / 'sources')


def test_tests_never_use_the_real_cache():
    """conftest points the cache to a temporary directory for every test."""
    assert fetch.cache_root().startswith(tempfile.gettempdir())
