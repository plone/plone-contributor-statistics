"""Listing people without a GitHub login who appear as a login, and proposing the login (#117)."""

from scripts.lib import paths
from scripts.lib.model import load_registry, source_id
from scripts.tools import unmatched_names
from tests.conftest import record_source


def write_people(rows):
    sid = record_source()
    paths.PEOPLE.write_text('id,name\n' + ''.join(f'{i},{name}\n' for i, name, _ in rows), encoding='utf-8')
    paths.IDENTITIES.write_text('person,kind,value,source,snippet,notes\n' + ''.join(
        f'{i},github,{github},{sid},,\n' for i, _, github in rows if github), encoding='utf-8')


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
    assert unmatched_names.propose(load_registry(), profiles) == [('jane-doe', 'janedoe', 'Jane  Doe')]


def test_a_proposal_is_a_github_identity_citing_the_profile():
    sid = source_id('https://github.com/janedoe')
    assert unmatched_names.proposal_line('jane-doe', 'janedoe', 'Jane Doe') == (
        f'jane-doe,github,janedoe,{sid},,  # profile name "Jane Doe"; capture the profile first: '
        'python -m scripts.tools.capture https://github.com/janedoe --name "Jane Doe"')


def test_main_prints_people_proposals(tmp_repo, monkeypatch, capsys):
    write_people([('jane-doe', 'Jane Doe', ''), ('mauro-amico', 'Mauro Amico', 'mamico')])
    write_contributors('janedoe')
    monkeypatch.setattr('sys.argv', ['unmatched_names', '--propose'])
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    monkeypatch.setattr(unmatched_names, 'load_dotenv', lambda: None)
    monkeypatch.setattr(unmatched_names, 'fetch_profile_names', lambda session, logins: {'janedoe': 'Jane Doe'})
    unmatched_names.main()
    out = capsys.readouterr().out
    assert 'Proposals for curated/mappings/identities.csv' in out
    assert f'jane-doe,github,janedoe,{source_id("https://github.com/janedoe")},,  # profile name "Jane Doe"' in out
    assert 'people.csv' not in out


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
