"""PR interactions: GraphQL pagination and date filtering in plone_pr_interactions.py (#37)."""

from datetime import datetime

import pytest

import plone_pr_interactions
from plone_pr_interactions import PlonePRInteractionExtractor

YEAR_2015 = (datetime(2015, 1, 1), datetime(2015, 12, 31, 23, 59, 59))


def node(number, created, comments=(), reviews=(), author='alice', comments_total=None, reviews_total=None):
    return {
        'number': number, 'title': f'PR {number}', 'state': 'MERGED',
        'createdAt': f'{created}T12:00:00Z', 'updatedAt': f'{created}T13:00:00Z',
        'mergedAt': f'{created}T14:00:00Z', 'closedAt': f'{created}T14:00:00Z',
        'author': {'login': author, '__typename': 'User'},
        'comments': {'totalCount': len(comments) if comments_total is None else comments_total,
                     'nodes': list(comments)},
        'reviews': {'totalCount': len(reviews) if reviews_total is None else reviews_total, 'nodes': list(reviews)},
    }


def page(nodes, has_next):
    return {'repository': {'pullRequests': {
        'pageInfo': {'hasNextPage': has_next, 'endCursor': f'cursor-after-{nodes[-1]["number"]}' if nodes else None},
        'nodes': nodes,
    }}}


@pytest.fixture
def extractor_with_pages(monkeypatch):
    """Return an extractor whose GraphQL queries serve the given pages, plus the requested cursors."""

    def build(pages):
        extractor = PlonePRInteractionExtractor(github_token='test-token')
        cursors = []

        def fake_graphql(session, query, variables=None, **kwargs):
            cursors.append(variables['after'])
            return pages[len(cursors) - 1]

        monkeypatch.setattr(plone_pr_interactions, 'github_graphql', fake_graphql)
        return extractor, cursors

    return build


def test_pages_back_until_the_range_starts(extractor_with_pages):
    # Sorted by creation, newest first
    pages = [
        page([node(30, '2024-03-01'), node(29, '2016-01-01')], has_next=True),
        page([node(28, '2015-06-01'), node(27, '2015-01-01')], has_next=True),
        page([node(26, '2014-12-31'), node(25, '2014-06-01')], has_next=True),
        page([node(24, '2013-01-01')], has_next=False),
    ]
    extractor, cursors = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert [pr['number'] for pr in prs] == [28, 27]
    # Stops at the first PR created before the range
    assert cursors == [None, 'cursor-after-29', 'cursor-after-27']


def test_without_date_range_returns_everything(extractor_with_pages):
    pages = [page([node(2, '2024-01-01')], has_next=True), page([node(1, '2010-01-01')], has_next=False)]
    extractor, cursors = extractor_with_pages(pages)

    prs = extractor.get_pull_requests('plone/volto')

    assert [pr['number'] for pr in prs] == [2, 1]


def test_empty_repository(extractor_with_pages):
    extractor, _ = extractor_with_pages([page([], has_next=False)])

    assert extractor.get_pull_requests('plone/volto', *YEAR_2015) == []


def test_pr_state_and_bot_logins(extractor_with_pages):
    open_pr = node(2, '2015-03-01', author='pre-commit-ci')
    open_pr.update(state='OPEN', mergedAt=None, closedAt=None)
    open_pr['author']['__typename'] = 'Bot'
    deleted = node(1, '2015-02-01')
    deleted['author'] = None
    extractor, _ = extractor_with_pages([page([open_pr, deleted], has_next=False)])

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert [(pr['author'], pr['state'], pr['merged']) for pr in prs] == [
        ('pre-commit-ci[bot]', 'open', False),
        ('ghost', 'closed', True),
    ]


def test_gets_the_rest_of_long_discussions_from_rest(extractor_with_pages, monkeypatch):
    comment = {'author': {'login': 'bob', '__typename': 'User'}, 'createdAt': '2015-03-02T12:00:00Z',
               'reactionGroups': []}
    extractor, _ = extractor_with_pages([page([node(1, '2015-03-01', comments=[comment], comments_total=150)],
                                              has_next=False)])
    requested = []

    def fake_pages(url, params=None):
        requested.append(url)
        return [{'user': {'login': 'bob'}, 'created_at': '2015-03-02T12:00:00Z', 'reactions': {'total_count': 1}}] * 150

    monkeypatch.setattr(extractor, 'get_all_pages', fake_pages)

    prs = extractor.get_pull_requests('plone/volto', *YEAR_2015)

    assert requested == ['https://api.github.com/repos/plone/volto/issues/1/comments']
    assert len(prs[0]['comments']) == 150
