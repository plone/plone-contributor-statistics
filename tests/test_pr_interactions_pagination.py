"""Tests for PR pagination and date filtering in plone_pr_interactions.py (#37)."""

from datetime import datetime

import pytest

from plone_pr_interactions import PlonePRInteractionExtractor


def make_pr(number, created, updated):
    return {
        'number': number,
        'created_at': f'{created}T12:00:00Z',
        'updated_at': f'{updated}T12:00:00Z',
    }


def page(start, count, created, updated):
    return [make_pr(start + i, created, updated) for i in range(count)]


@pytest.fixture
def extractor_with_pages():
    """Return an extractor whose API calls serve the given pages, plus the list of requested pages."""

    def build(pages):
        extractor = PlonePRInteractionExtractor(github_token='test-token')
        requested = []

        def fake_request(url, params=None):
            requested.append(params['page'])
            index = params['page'] - 1
            return pages[index] if index < len(pages) else []

        extractor.make_request = fake_request
        return extractor, requested

    return build


YEAR_2015 = (datetime(2015, 1, 1), datetime(2015, 12, 31, 23, 59, 59))


def test_finds_old_prs_behind_recently_updated_pages(extractor_with_pages):
    # Page 1 only holds PRs updated recently, the 2015 PRs come later.
    # Before the fix, the empty first page stopped the pagination.
    pages = [
        page(1, 100, '2024-03-01', '2026-01-01'),
        page(101, 100, '2015-06-01', '2020-01-01'),
        page(201, 50, '2014-06-01', '2014-07-01'),
    ]
    extractor, requested = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/Products.CMFPlone', *YEAR_2015)

    assert len(prs) == 100
    assert {pr['number'] for pr in prs} == set(range(101, 201))
    assert requested == [1, 2, 3]


def test_filters_by_creation_date_not_by_update(extractor_with_pages):
    pages = [[
        make_pr(1, '2015-05-01', '2025-01-01'),  # created in 2015, commented later
        make_pr(2, '2014-12-31', '2015-02-01'),  # created before, updated in 2015
        make_pr(3, '2016-01-01', '2016-01-02'),  # created after
    ]]
    extractor, _ = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert [pr['number'] for pr in prs] == [1]


def test_stops_once_a_full_page_is_older_than_the_range(extractor_with_pages):
    pages = [
        page(1, 100, '2015-03-01', '2015-04-01'),
        page(101, 100, '2014-01-01', '2014-02-01'),
        page(201, 100, '2013-01-01', '2013-02-01'),
    ]
    extractor, requested = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert len(prs) == 100
    assert requested == [1, 2]


def test_stops_after_a_short_page(extractor_with_pages):
    pages = [page(1, 30, '2015-03-01', '2026-01-01')]
    extractor, requested = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert len(prs) == 30
    assert requested == [1]


def test_without_date_range_returns_everything(extractor_with_pages):
    pages = [
        page(1, 100, '2024-01-01', '2026-01-01'),
        page(101, 10, '2010-01-01', '2010-01-02'),
    ]
    extractor, requested = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto')

    assert len(prs) == 110
    assert requested == [1, 2]
