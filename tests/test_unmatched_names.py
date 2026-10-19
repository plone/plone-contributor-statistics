"""Listing people without a GitHub login who appear as a login, and proposing the login (#117)."""

from scripts.lib import paths
from scripts.lib.model import load_registry
from scripts.tools import unmatched_names


def write_people(rows):
    paths.PEOPLE.write_text('id,name,github,source\n' + ''.join(
        f'{i},{name},{github},https://example.org/{i}\n' for i, name, github in rows), encoding='utf-8')


def write_contributors(*logins):
    (paths.CONTRIBUTORS_DIR / '2025-plone-contributors.csv').write_text(
        'username,total_commits\n' + ''.join(f'{login},1\n' for login in logins), encoding='utf-8')


def test_contributor_logins_are_collected_and_registered(tmp_repo):
    write_people([('mauro-amico', 'Mauro Amico', 'mamico'), ('jane-doe', 'Jane Doe', '')])
    write_contributors('janedoe', 'person:jane-doe', 'bad login!')
    assert unmatched_names.contributor_logins(load_registry()) == ['janedoe', 'mamico']


def test_lists_people_without_a_login_whose_name_is_a_login(tmp_repo):
    write_people([('mauro-amico', 'Mauro Amico', 'mamico'), ('jane-doe', 'Jane Doe', ''), ('tisto', 'Tisto', '')])
    registry = load_registry()
    found = unmatched_names.unmatched_people(registry, ['mamico', 'janedoe', 'Tisto', 'other'])
    assert found == {'jane-doe': ['janedoe'], 'tisto': ['Tisto']}


def test_a_registered_login_is_no_match(tmp_repo):
    write_people([('jane-doe', 'Jane Doe', ''), ('jd', 'J D', 'janedoe')])
    assert unmatched_names.unmatched_people(load_registry(), ['janedoe']) == {}


def test_proposes_only_unique_exact_profile_names(tmp_repo):
    write_people([('jane-doe', 'Jane Doe', ''), ('john-roe', 'John Roe', ''), ('mauro-amico', 'Mauro Amico', 'mamico')])
    profiles = {'janedoe': 'Jane  Doe', 'jroe1': 'John Roe', 'jroe2': 'John Roe', 'mamico': 'Mauro Amico'}
    assert unmatched_names.propose(load_registry(), profiles) == [
        ('jane-doe', 'login', 'janedoe', 'https://github.com/janedoe')]


def test_does_not_propose_a_login_of_another_person(tmp_repo):
    write_people([('jane-doe', 'Jane Doe', ''), ('other', 'Other', 'janedoe')])
    assert unmatched_names.propose(load_registry(), {'janedoe': 'Jane Doe'}) == []


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
