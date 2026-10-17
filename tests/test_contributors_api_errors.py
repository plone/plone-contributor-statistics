"""plone_contributors.py must not record API errors as "no activity" (#41)."""

import sys
from datetime import datetime

import pytest

import plone_contributors
from github_api import GitHubAPIError


class FakeResponse:
    def __init__(self, status_code, data=None, headers=None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}
        self.text = ''

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)

    def get(self, url, params=None, timeout=None):
        return self.responses.pop(0)


@pytest.fixture
def extractor(monkeypatch):
    monkeypatch.setattr(plone_contributors.time, 'sleep', lambda seconds: None)
    return plone_contributors.PloneStatsExtractor(
        token='test-token', start_date=datetime(2015, 1, 1), end_date=datetime(2015, 12, 31, 23, 59, 59)
    )


def commit(date):
    return {'commit': {'author': {'date': f'{date}T12:00:00Z'}}}


def test_counts_commits(extractor):
    extractor.session = FakeSession(FakeResponse(200, [commit('2015-03-01'), commit('2015-04-01')]))

    assert extractor.get_commits_for_user('volto', 'alice', 'main') == 2


def test_empty_repository_has_no_commits(extractor):
    extractor.session = FakeSession(FakeResponse(409, {'message': 'Git Repository is empty.'}))

    assert extractor.get_commits_for_user('empty-repo', 'alice', 'main') == 0


def test_api_error_raises_instead_of_counting_zero(extractor):
    # Before #41, a failed request returned 0 commits without notice.
    extractor.session = FakeSession(FakeResponse(500))

    with pytest.raises(GitHubAPIError):
        extractor.get_commits_for_user('volto', 'alice', 'main')


def test_rate_limit_is_waited_out(extractor, monkeypatch):
    waits = []
    monkeypatch.setattr('github_api.time.sleep', waits.append)
    limited = FakeResponse(403, headers={'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '9999999999'})
    extractor.session = FakeSession(limited, FakeResponse(200, [commit('2015-03-01')]))

    assert extractor.get_commits_for_user('volto', 'alice', 'main') == 1
    assert len(waits) == 1


def test_forbidden_organization_listing_raises(extractor):
    # Before #41, a 403 fell back to five hard-coded repositories.
    extractor.session = FakeSession(FakeResponse(403))

    with pytest.raises(GitHubAPIError):
        extractor.get_organization_repos()


def test_failed_repository_stops_the_extraction(extractor, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(extractor, 'get_organization_repos', lambda: [{'name': 'a'}, {'name': 'b'}])
    processed = []

    def contributors(name):
        processed.append(name)
        raise GitHubAPIError('boom')

    monkeypatch.setattr(extractor, 'get_repository_contributors_list', contributors)

    with pytest.raises(GitHubAPIError):
        extractor.extract_all_stats(save_every=0)
    assert processed == ['a']


def test_main_keeps_only_a_checkpoint_when_the_run_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    monkeypatch.setattr(sys, 'argv', ['plone_contributors.py', '--year', '2015', '--token', 'test-token'])

    def failing_run(self, *args, **kwargs):
        self.contributors_data['alice']['commits'] = 3
        raise GitHubAPIError('rate limit not recovered')

    monkeypatch.setattr(plone_contributors.PloneStatsExtractor, 'extract_all_stats', failing_run)

    assert plone_contributors.main() == 1
    assert not (tmp_path / 'data' / '2015-plone-contributors.csv').exists()
    assert (tmp_path / 'data' / '2015-plone-contributors_checkpoint.csv').exists()
