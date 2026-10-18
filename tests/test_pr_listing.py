"""PR counting uses the merge date everywhere and pages far enough (#42)."""

from datetime import datetime

import pytest

from scripts.collect import plone_contributors


class FakeResponse:
    def __init__(self, data):
        self.status_code = 200
        self._data = data
        self.headers = {}
        self.text = ''

    def json(self):
        return self._data


class PagedSession:
    """Serves the given pages and records which ones were requested."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url, params=None, timeout=None):
        self.requested.append(params['page'])
        index = params['page'] - 1
        return FakeResponse(self.pages[index] if index < len(self.pages) else [])


def pr(number, merged=None, updated='2026-01-01', base='main'):
    return {
        'number': number,
        'merged_at': f'{merged}T12:00:00Z' if merged else None,
        'updated_at': f'{updated}T12:00:00Z',
        'base': {'ref': base},
        'user': {'login': f'user{number}', 'type': 'User'},
    }


@pytest.fixture
def extractor(monkeypatch):
    monkeypatch.setattr(plone_contributors.time, 'sleep', lambda seconds: None)
    return plone_contributors.PloneStatsExtractor(
        token='test-token', start_date=datetime(2015, 1, 1), end_date=datetime(2015, 12, 31, 23, 59, 59)
    )


def test_keeps_paging_past_old_prs_that_were_updated_recently(extractor):
    # Page 1: PRs merged before 2015, but commented on recently. The old check
    # looked at the merge dates only and stopped here.
    pages = [
        [pr(i, merged='2013-05-01', updated='2025-06-01') for i in range(1, 101)],
        [pr(101, merged='2015-04-01', updated='2015-04-02'), pr(102, merged='2014-12-01', updated='2014-12-02')],
    ]
    extractor.session = PagedSession(pages)

    prs = extractor.get_repository_pull_requests('Products.CMFPlone')

    assert [p['number'] for p in prs] == [101]
    assert extractor.session.requested == [1, 2]


def test_stops_once_a_whole_page_was_updated_before_the_range(extractor):
    pages = [
        [pr(i, merged='2015-06-01', updated='2015-06-02') for i in range(1, 101)],
        [pr(i, merged='2014-06-01', updated='2014-06-02') for i in range(101, 201)],
        [pr(i, merged='2013-06-01', updated='2013-06-02') for i in range(201, 301)],
    ]
    extractor.session = PagedSession(pages)

    prs = extractor.get_repository_pull_requests('Products.CMFPlone')

    assert len(prs) == 100
    assert extractor.session.requested == [1, 2]


def test_unmerged_and_backport_prs(extractor):
    pages = [[
        pr(1, merged=None, updated='2015-03-01'),  # closed without merge
        pr(2, merged='2015-03-01', updated='2015-03-02', base='5.0.x'),  # backport
    ]]
    extractor.session = PagedSession(pages)

    prs = extractor.get_repository_pull_requests('Products.CMFPlone')

    # Backports to maintenance branches are work too and count as PRs.
    assert [p['number'] for p in prs] == [2]
