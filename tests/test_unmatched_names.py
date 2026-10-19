"""Listing community names without a GitHub login, and proposing logins (#117)."""

from scripts.lib import paths
from scripts.tools import unmatched_names


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_lists_names_without_a_login(tmp_repo):
    write(paths.ORGANISATIONS, 'Organisation,Team\nRedTurtle,mamico\n')
    write(paths.FULLNAMES, 'github username,fullname,source\nmamico,Mauro Amico,https://github.com/mamico\n')
    write(paths.COMMUNITY / '2025-team-leaders.csv',
          'Name,Team,Organisation,Source\nMauro Amico,Volto Team,RedTurtle,https://a\nJane Doe,Docs Team,Unmapped,https://b\n')
    found = unmatched_names.unmatched_names(range(2025, 2026))
    assert found == {'jane doe': {'spelling': 'Jane Doe', 'years': [2025], 'mentions': 1}}


def test_proposes_only_unique_exact_profile_names():
    unmatched = {'jane doe': {'spelling': 'Jane Doe', 'years': [2025], 'mentions': 1},
                 'john roe': {'spelling': 'John Roe', 'years': [2025], 'mentions': 1}}
    profiles = {'janedoe': 'Jane  Doe', 'jroe1': 'John Roe', 'jroe2': 'John Roe'}
    assert unmatched_names.propose(unmatched, profiles) == [
        ('janedoe', 'Jane Doe', 'GitHub profile name: https://github.com/janedoe')]


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, data):
        self._data = data

    def json(self):
        return {'data': self._data}


class FakeSession:
    def __init__(self):
        self.queries = []

    def post(self, url, json=None, timeout=None):
        self.queries.append(json['query'])
        return FakeResponse({'u0': {'login': 'janedoe', 'name': 'Jane Doe'}, 'u1': {'login': 'noname', 'name': None}})


def test_fetches_profile_names_in_batches():
    session = FakeSession()
    names = unmatched_names.fetch_profile_names(session, ['janedoe', 'noname'])
    assert names == {'janedoe': 'Jane Doe'}
    assert 'repositoryOwner(login: "janedoe")' in session.queries[0]
