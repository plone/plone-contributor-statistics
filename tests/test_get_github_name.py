"""The profile name lookup for a single login, with the GitHub API faked."""

from scripts.lib.github_api import GitHubAPIError
from scripts.tools import get_github_name as tool


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def fake_api(monkeypatch, answers):
    """Replace github_get: a dict answers with that JSON, an exception is raised."""
    asked = []

    def github_get(session, url, params=None, **kwargs):
        asked.append(url)
        answer = answers[url.rsplit('/', 1)[1]]
        if isinstance(answer, Exception):
            raise answer
        return FakeResponse(answer)

    monkeypatch.setattr(tool, 'github_get', github_get)
    return asked


def test_the_profile_name_of_a_login(monkeypatch):
    asked = fake_api(monkeypatch, {'pbauer': {'login': 'pbauer', 'name': 'Philip Bauer'}})
    assert tool.get_github_name(None, 'pbauer') == 'Philip Bauer'
    assert asked == ['https://api.github.com/users/pbauer']


def test_a_profile_without_a_name_gives_none(monkeypatch):
    fake_api(monkeypatch, {'noname': {'login': 'noname', 'name': None}, 'bare': {'login': 'bare'}})
    assert tool.get_github_name(None, 'noname') is None
    assert tool.get_github_name(None, 'bare') is None


def test_an_unknown_login_says_not_found(monkeypatch, capsys):
    fake_api(monkeypatch, {'ghost': GitHubAPIError('https://api.github.com/users/ghost: HTTP 404 Not Found'),
                           'broken': GitHubAPIError('https://api.github.com/users/broken: HTTP 500 oops')})
    assert tool.get_github_name(None, 'ghost') is None
    assert capsys.readouterr().err == "User 'ghost' not found\n"
    assert tool.get_github_name(None, 'broken') is None
    assert capsys.readouterr().err.startswith('Error: ')


def test_the_session_sends_the_token_from_the_environment(monkeypatch):
    monkeypatch.setattr(tool, 'load_dotenv', lambda: None)
    monkeypatch.setenv('GITHUB_TOKEN', 'secret-token')
    assert tool.make_session().headers['Authorization'] == 'token secret-token'


def test_without_a_token_the_session_warns(monkeypatch, capsys):
    monkeypatch.setattr(tool, 'load_dotenv', lambda: None)
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    assert 'Authorization' not in tool.make_session().headers
    assert 'no GITHUB_TOKEN' in capsys.readouterr().err


def test_main_prints_one_line_per_login(monkeypatch, capsys):
    monkeypatch.setattr(tool, 'load_dotenv', lambda: None)
    monkeypatch.setenv('GITHUB_TOKEN', 'secret-token')
    fake_api(monkeypatch, {'pbauer': {'name': 'Philip Bauer'}, 'noname': {}})
    tool.main(['pbauer'])
    assert capsys.readouterr().out == 'pbauer: Philip Bauer\n'
    monkeypatch.setattr(tool.time, 'sleep', lambda seconds: None)
    tool.main(['pbauer', 'noname'])
    assert capsys.readouterr().out == 'pbauer: Philip Bauer\nnoname: No name set or user not found\n'
