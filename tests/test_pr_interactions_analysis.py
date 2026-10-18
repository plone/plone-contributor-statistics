"""PR interactions: counting, bots, deleted users and the yearly files (#37)."""

from datetime import datetime

import pytest

import plone_pr_interactions
from github_api import GitHubAPIError
from plone_pr_interactions import PlonePRInteractionExtractor


def comment(login, at, reactions=0):
    return {'login': login, 'created_at': f'{at}Z', 'reactions': reactions}


def review(login, state, at):
    return {'login': login, 'state': state, 'submitted_at': f'{at}Z' if at else None}


def pr(number=1, author='alice', created='2015-03-01T10:00:00', comments=(), reviews=()):
    return {
        'number': number, 'title': f'PR {number}', 'author': author,
        'created_at': f'{created}Z', 'updated_at': f'{created}Z', 'merged_at': None, 'closed_at': None,
        'state': 'open', 'merged': False,
        'comments': list(comments), 'reviews': list(reviews),
    }


@pytest.fixture
def extractor(tmp_repo, monkeypatch, tmp_path):
    (tmp_path / 'bot_accounts.csv').write_text('login,reason\nmister-roboto,Plone CI bot\n', encoding='utf-8')
    return PlonePRInteractionExtractor(github_token='test-token')


def test_counts_comments_reviews_and_participants(extractor):
    analysis = extractor.analyze_pr_interactions('plone/volto', pr(
        comments=[comment('bob', '2015-03-01T12:00:00', reactions=2), comment('alice', '2015-03-01T11:00:00')],
        reviews=[review('carol', 'APPROVED', '2015-03-02T10:00:00'),
                 review('bob', 'CHANGES_REQUESTED', '2015-03-01T15:00:00'),
                 review('dave', 'PENDING', None)],  # not submitted
    ), review_comments=[comment('carol', '2015-03-02T09:00:00')])

    assert analysis['issue_comments_count'] == 2
    assert analysis['review_comments_count'] == 1
    assert analysis['total_comments'] == 3
    assert analysis['reviews_count'] == 2
    assert (analysis['approved_reviews'], analysis['changes_requested_reviews']) == (1, 1)
    assert analysis['participants'] == ['alice', 'bob', 'carol']
    assert analysis['reviewers'] == ['bob', 'carol']
    assert analysis['reactions_total'] == 2
    # The author's own comment at 11:00 is no response
    assert analysis['first_response_time'] == 2.0


def test_bots_are_not_interactions(extractor):
    analysis = extractor.analyze_pr_interactions('plone/volto', pr(
        comments=[comment('mister-roboto', '2015-03-01T10:00:05'), comment('github-actions[bot]', '2015-03-01T10:01:00'),
                  comment('bob', '2015-03-01T13:00:00')],
        reviews=[review('copilot-pull-request-reviewer[bot]', 'COMMENTED', '2015-03-01T10:02:00')],
    ))

    assert analysis['issue_comments_count'] == 1
    assert analysis['reviews_count'] == 0
    assert analysis['participants'] == ['alice', 'bob']
    assert analysis['first_response_time'] == 3.0


def test_deleted_users_do_not_break_the_repository(extractor):
    analysis = extractor.analyze_pr_interactions('plone/volto', pr(
        author='ghost', comments=[comment('ghost', '2015-03-01T12:00:00')]))

    assert analysis['participants'] == ['ghost']


def test_review_comments_are_grouped_by_pr(extractor, monkeypatch):
    calls = []

    def fake_pages(url, params=None):
        calls.append((url, params))
        return [
            {'user': {'login': 'bob'}, 'created_at': '2015-03-02T12:00:00Z',
             'pull_request_url': 'https://api.github.com/repos/plone/volto/pulls/12'},
            {'user': None, 'created_at': '2015-03-02T13:00:00Z',
             'pull_request_url': 'https://api.github.com/repos/plone/volto/pulls/7'},
        ]

    monkeypatch.setattr(extractor, 'get_all_pages', fake_pages)

    by_pr = extractor.get_review_comments('plone/volto', datetime(2015, 1, 1))

    assert by_pr == {12: [{'login': 'bob', 'created_at': '2015-03-02T12:00:00Z'}],
                     7: [{'login': 'ghost', 'created_at': '2015-03-02T13:00:00Z'}]}
    assert calls[0][1]['since'] == '2015-01-01T00:00:00Z'


def test_bot_prs_are_left_out(extractor, monkeypatch):
    monkeypatch.setattr(extractor, 'get_pull_requests', lambda repo, start, end: [
        pr(1, author='pre-commit-ci[bot]'), pr(2, author='alice')])
    monkeypatch.setattr(extractor, 'get_review_comments', lambda repo, start: {})

    analyses = extractor.extract_interactions(['plone/volto'], *(datetime(2015, 1, 1), datetime(2015, 12, 31)))

    assert [a['pr_number'] for a in analyses] == [2]


def test_token_from_environment_without_env_file(tmp_repo, monkeypatch, tmp_path):
    monkeypatch.setenv('GITHUB_TOKEN', 'from-env')

    assert PlonePRInteractionExtractor().github_token == 'from-env'


# The command line: one run, one file per year


def run_main(monkeypatch, *argv, analyses=None, error=None):
    def fake_extract(self, repos=None, start_date=None, end_date=None):
        if error:
            raise error
        return analyses

    monkeypatch.setattr(PlonePRInteractionExtractor, 'extract_interactions', fake_extract)
    monkeypatch.setattr('sys.argv', ['plone_pr_interactions.py', '--token', 'test-token', *argv])
    return plone_pr_interactions.main()


def test_writes_one_file_per_year(extractor, monkeypatch, tmp_path):
    analyses = [extractor.analyze_pr_interactions('plone/volto', pr(1, created='2014-12-31T23:59:59')),
                extractor.analyze_pr_interactions('plone/volto', pr(2, created='2015-01-01T00:00:00'))]

    assert run_main(monkeypatch, '--from-year', '2014', '--to-year', '2015', analyses=analyses) == 0

    for year, number in [(2014, 1), (2015, 2)]:
        rows = (tmp_path / f'data/{year}-plone-pr-interactions.csv').read_text(encoding='utf-8').splitlines()
        assert len(rows) == 2 and rows[1].startswith(f'plone/volto,{number},')
        assert (tmp_path / f'reports/github-pr-interactions-report-{year}.md').exists()


def test_writes_nothing_after_an_api_error(extractor, monkeypatch, tmp_path):
    assert run_main(monkeypatch, '--year', '2015', error=GitHubAPIError('HTTP 500')) == 1

    assert not (tmp_path / 'data').exists()
