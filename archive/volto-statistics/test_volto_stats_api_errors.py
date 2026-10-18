"""volto_stats.py must not record API errors as "no activity" (#41)."""

import pytest

from scripts.collect import volto_stats
from scripts.lib.github_api import GitHubAPIError


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data
        self.headers = {}
        self.text = ''

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)

    def get(self, url, params=None, timeout=None):
        return self.responses.pop(0)


def test_pull_requests_are_counted():
    session = FakeSession(FakeResponse(200, {'total_count': 7}))

    assert volto_stats.get_pull_requests(session, 'alice', '2024-01-01', '2024-12-31') == 7


def test_pull_request_search_error_raises():
    session = FakeSession(FakeResponse(422))

    with pytest.raises(GitHubAPIError):
        volto_stats.get_pull_requests(session, 'alice', '2024-01-01', '2024-12-31')


def test_commit_error_raises(monkeypatch):
    monkeypatch.setattr(volto_stats.time, 'sleep', lambda seconds: None)
    session = FakeSession(FakeResponse(500))

    with pytest.raises(GitHubAPIError):
        volto_stats.get_commits(session, 'alice', '2024-01-01', '2024-12-31')
