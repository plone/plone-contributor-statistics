"""The PLIP collector uses the GitHub token and fails loudly on API errors (#44)."""

import pytest

from scripts.collect import plone_plips
from scripts.lib import paths
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
    """Answers each page with the given issues; error_page answers HTTP 500."""

    def __init__(self, pages, error_page=None):
        self.pages = pages
        self.error_page = error_page
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        if params['page'] == self.error_page:
            return FakeResponse(500)
        return FakeResponse(200, self.pages.get(params['page'], []))


def issue(number, pull_request=False):
    data = {
        'number': number, 'title': f'PLIP {number}', 'user': {'login': 'alice'}, 'state': 'closed',
        'created_at': '2024-01-01T10:00:00Z', 'updated_at': '2024-02-01T10:00:00Z',
        'closed_at': '2024-03-01T10:00:00Z', 'html_url': f'https://github.com/plone/volto/issues/{number}',
    }
    if pull_request:
        data['pull_request'] = {}
    return data


def test_token_from_environment(tmp_repo, monkeypatch):
    # Before, the token was never read: all requests were unauthenticated, 60 per hour
    monkeypatch.setenv('GITHUB_TOKEN', 'from-env')
    assert plone_plips.create_session().headers['Authorization'] == 'token from-env'


def test_placeholder_token_is_not_used(tmp_repo, monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'your_token_here')
    assert 'Authorization' not in plone_plips.create_session().headers


def test_collects_all_pages_and_skips_pull_requests():
    session = FakeSession({1: [issue(n) for n in range(1, 101)], 2: [issue(101), issue(102, pull_request=True)]})

    plips = plone_plips.get_plips_from_repo(session, 'plone', 'volto')

    assert [p['number'] for p in plips] == list(range(1, 102))
    assert plips[0]['repository'] == 'plone/volto'


def test_api_error_raises_instead_of_returning_the_pages_so_far():
    # Before, a failed request ended the loop, and the CSV files got whatever was fetched
    session = FakeSession({1: [issue(n) for n in range(1, 101)]}, error_page=2)

    with pytest.raises(GitHubAPIError):
        plone_plips.get_plips_from_repo(session, 'plone', 'volto')


def test_main_writes_nothing_after_an_api_error(tmp_repo, monkeypatch):
    monkeypatch.setattr(plone_plips, 'create_session', lambda: FakeSession({}, error_page=1))

    assert plone_plips.main() == 1
    assert not paths.PLIPS.exists()
    assert not paths.PLIPS_DETAILED.exists()


def test_main_writes_both_files(tmp_repo, monkeypatch):
    monkeypatch.setattr(plone_plips, 'create_session', lambda: FakeSession({1: [issue(1)]}))

    assert plone_plips.main() == 0
    assert paths.PLIPS.read_text(encoding='utf-8').startswith('username,total_plips,')
    assert paths.PLIPS_DETAILED.read_text(encoding='utf-8').startswith('number,title,author,')
