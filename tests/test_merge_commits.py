"""Merge commits are not counted as commits (#39)."""

from datetime import datetime

from scripts.collect import plone_contributors
from scripts.lib.github_api import is_merge_commit


class FakeResponse:
    def __init__(self, data):
        self.status_code = 200
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


def commit(date, parents=1, login='alice'):
    return {
        'author': {'login': login, 'type': 'User'},
        'commit': {'author': {'date': f'{date}T12:00:00Z'}, 'committer': {'date': f'{date}T12:00:00Z'}},
        'parents': [{'sha': str(i)} for i in range(parents)],
    }


def make_extractor(monkeypatch):
    monkeypatch.setattr(plone_contributors.time, 'sleep', lambda seconds: None)
    return plone_contributors.PloneStatsExtractor(
        token='test-token', start_date=datetime(2015, 1, 1), end_date=datetime(2015, 12, 31, 23, 59, 59)
    )


def test_is_merge_commit():
    assert is_merge_commit(commit('2015-01-01', parents=2))
    assert not is_merge_commit(commit('2015-01-01', parents=1))
    assert not is_merge_commit(commit('2015-01-01', parents=0))  # root commit
    assert not is_merge_commit({})


def test_contributors_skip_merge_commits_and_their_dates(monkeypatch):
    extractor = make_extractor(monkeypatch)

    extractor.process_commits('Products.CMFPlone', [
        commit('2015-01-10', parents=2),  # merge via the merge button
        commit('2015-03-01'),
        commit('2015-06-01'),
        commit('2015-12-20', parents=2),
    ])

    data = extractor.contributors_data['2015-plone-contributors']['alice']
    assert data['commits'] == 2
    assert data['first_contribution'] == datetime(2015, 3, 1, 12, 0)
    assert data['last_contribution'] == datetime(2015, 6, 1, 12, 0)


def test_only_merge_commits_count_as_no_commits(monkeypatch):
    extractor = make_extractor(monkeypatch)

    extractor.process_commits('Products.CMFPlone', [commit('2015-01-10', parents=2)])

    assert 'alice' not in extractor.contributors_data['2015-plone-contributors']
