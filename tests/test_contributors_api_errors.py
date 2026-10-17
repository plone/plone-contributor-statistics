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


def test_forbidden_organization_listing_raises(extractor):
    # Before #41, a 403 fell back to five hard-coded repositories.
    extractor.session = FakeSession(FakeResponse(403))

    with pytest.raises(GitHubAPIError):
        extractor.get_organization_repos()


def test_failed_repository_stops_the_extraction(extractor, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(extractor, 'get_organization_repos', lambda: [{'name': 'a'}, {'name': 'b'}])
    processed = []

    def commits(name, branch):
        processed.append(name)
        raise GitHubAPIError('boom')

    monkeypatch.setattr(extractor, 'get_repository_commits', commits)

    with pytest.raises(GitHubAPIError):
        extractor.extract_all_stats(save_every=0)
    assert processed == ['a']


def test_main_keeps_only_a_checkpoint_when_the_run_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    monkeypatch.setattr(sys, 'argv', ['plone_contributors.py', '--year', '2015', '--token', 'test-token'])

    def failing_run(self, *args, **kwargs):
        self.contributors_data['2015-plone-contributors']['alice']['commits'] = 3
        raise GitHubAPIError('rate limit not recovered')

    monkeypatch.setattr(plone_contributors.PloneStatsExtractor, 'extract_all_stats', failing_run)

    assert plone_contributors.main() == 1
    assert not (tmp_path / 'data' / '2015-plone-contributors.csv').exists()
    assert (tmp_path / 'data' / '2015-plone-contributors_checkpoint.csv').exists()
