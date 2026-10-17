"""Tests for github_api.py: rate limits are waited out, other errors raise (#41)."""

import pytest
import requests

from github_api import GitHubAPIError, github_get, rate_limit_wait


class FakeResponse:
    def __init__(self, status_code, headers=None, text=''):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class FakeSession:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_returns_successful_response():
    session = FakeSession(FakeResponse(200))

    assert github_get(session, 'https://api.github.com/x').status_code == 200


@pytest.mark.parametrize('status', [204, 409])
def test_empty_repositories_are_not_errors(status):
    session = FakeSession(FakeResponse(status))

    assert github_get(session, 'https://api.github.com/x').status_code == status


def test_waits_for_primary_rate_limit_and_retries():
    waits = []
    limited = FakeResponse(403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '9999999999'})
    session = FakeSession(limited, FakeResponse(200))

    response = github_get(session, 'https://api.github.com/x', sleep=waits.append)

    assert response.status_code == 200
    assert session.calls == 2
    assert len(waits) == 1 and waits[0] > 0


def test_waits_for_retry_after_header():
    waits = []
    session = FakeSession(FakeResponse(429, {'Retry-After': '60'}), FakeResponse(200))

    github_get(session, 'https://api.github.com/x', sleep=waits.append)

    assert waits == [60]


def test_raises_when_still_rate_limited():
    limited = FakeResponse(429, {'Retry-After': '1'})
    session = FakeSession(*[limited] * 3)

    with pytest.raises(GitHubAPIError):
        github_get(session, 'https://api.github.com/x', max_retries=3, sleep=lambda s: None)


@pytest.mark.parametrize('status', [401, 403, 404, 500])
def test_other_errors_raise_instead_of_returning_nothing(status):
    # A 403 without rate limit headers is a permission problem, not a rate limit.
    session = FakeSession(FakeResponse(status, text='nope'))

    with pytest.raises(GitHubAPIError, match=str(status)):
        github_get(session, 'https://api.github.com/x', sleep=lambda s: None)
    assert session.calls == 1


def test_retries_connection_errors_then_raises():
    session = FakeSession(*[requests.exceptions.ConnectionError()] * 3)

    with pytest.raises(GitHubAPIError):
        github_get(session, 'https://api.github.com/x', max_retries=3, sleep=lambda s: None)
    assert session.calls == 3


def test_rate_limit_wait_uses_reset_time():
    response = FakeResponse(403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1100'})

    assert rate_limit_wait(response, now=1000) == 101
    assert rate_limit_wait(FakeResponse(200)) is None
