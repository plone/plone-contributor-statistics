"""The tool that proposes affiliations from the GitHub commit search: offline, with a fake session."""

import json
import os

import pytest

from scripts.lib import paths
from scripts.lib.model import load_registry, read_rows
from scripts.tools import github_evidence

SOURCE = 'https://example.org/record'
GUESS = 'range from the current entry; years before 2026 not verified (#139)'


def commit(email, date, sha):
    return {'html_url': f'https://github.com/plone/repo/commit/{sha}',
            'commit': {'author': {'email': email, 'date': date}, 'committer': {'date': date}}}


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload, self.text = payload, json.dumps(payload)

    def json(self):
        return self.payload


class FakeSession:
    """Answers search requests from a dict {query: payload}; an unknown query is an empty result."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params)))
        return Response(self.answers.get(params['q'], {'total_count': 0, 'items': []}))


def q1(year, login='janedoe'):
    return f'author:{login} committer-date:{year}-01-01..{year}-12-31'


def q2(year, handle='greenfinity-hu', login='janedoe'):
    return f'author:{login} org:{handle} committer-date:{year}-01-01..{year}-12-31'


ANSWERS = {
    q1(2014): {'total_count': 4, 'items': [
        commit('jane@greenfinity.hu', '2014-05-02T10:00:00Z', 'aaa'),
        commit('jane@greenfinity.hu', '2014-03-01T10:00:00Z', 'early'),
        commit('jane@gmail.com', '2014-04-01T10:00:00Z', 'bbb'),
        commit('jane@janedoe.net', '2014-04-02T10:00:00Z', 'ccc'),
        commit('jane@nothing.example', '2014-04-03T10:00:00Z', 'ddd'),
        commit('', '2014-04-03T10:00:00Z', 'eee')]},
    q1(2015): {'total_count': 1, 'items': [commit('jane@greenfinity.hu', '2015-01-02T10:00:00Z', 'fff')]},
    q2(2016): {'total_count': 3, 'items': [commit('x@y.example', '2016-01-01T00:00:00Z', 'ggg')]},
}


@pytest.fixture
def setup(tmp_repo):
    paths.PEOPLE.write_text('id,name,github,source\n'
                            f'jane-doe,Jane Doe,janedoe,{SOURCE}\n'
                            f'no-login,No Login,,{SOURCE}\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text(
        'id,name,kind,github,aliases,notes\n'
        'bubblenet,BubbleNet,organisation,,,\n'
        'greenfinity,Greenfinity,organisation,greenfinity-hu,,\n', encoding='utf-8')
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'jane-doe,greenfinity,2014,2016,{SOURCE},,{GUESS}\n'
        f'jane-doe,bubblenet,2017,2018,{SOURCE},,\n', encoding='utf-8')
    for year, rows in {2013: 'otheruser,5,0', 2014: 'janedoe,5,1', 2015: 'JaneDoe,0,2', 2016: 'janedoe,1,0',
                       2017: 'janedoe,0,0'}.items():
        (paths.CONTRIBUTORS_DIR / f'{year}-plone-contributors.csv').write_text(
            f'username,total_commits,total_pull_requests\n{rows}\n', encoding='utf-8')
    return tmp_repo


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


def run(setup, answers=ANSWERS, session=None, **kwargs):
    session = session or FakeSession(answers)
    sleeps = Sleeps()
    kwargs.setdefault('cache', str(setup / 'cache'))
    text, added = github_evidence.run(session=session, sleep=sleeps, **kwargs)
    return text, added, session, sleeps


def test_years_come_from_the_rows_and_the_collected_activity(setup):
    registry = load_registry()
    activity = github_evidence.active_years()
    assert activity[2015] == {'janedoe'}
    assert activity[2017] == set()  # no commits and no pull requests
    # By default only the "not verified" rows count, and only their years with activity
    assert github_evidence.targets(registry, set(), False, activity) == {'jane-doe': [2014, 2015, 2016]}
    # A given person has all rows queried; --all-years adds the years without activity
    assert github_evidence.targets(registry, {'jane-doe'}, False, activity) == {'jane-doe': [2014, 2015, 2016]}
    assert github_evidence.targets(registry, {'jane-doe'}, True, activity) == {
        'jane-doe': [2014, 2015, 2016, 2017, 2018]}


def test_query_one_classifies_the_domains(setup):
    text, _, session, _ = run(setup)
    first = session.calls[0]
    assert first[0] == github_evidence.SEARCH_URL
    assert first[1] == {'q': q1(2014), 'sort': 'committer-date', 'order': 'asc', 'per_page': 100}
    proposals = text.split('## Conflicts')[0]
    assert '| jane-doe | greenfinity | 2014-2015 | 3 | address @greenfinity.hu (name) |' in proposals
    # the earliest commit of the first year is the example
    assert 'https://github.com/plone/repo/commit/early' in proposals
    unmapped = text.split('## Unmapped domains')[1].split('## Organisations')[0]
    assert '| nothing.example | 1 | 2014 | 1 |' in unmapped
    for ignored in ('gmail.com', 'janedoe.net'):
        assert ignored not in unmapped


def test_query_two_follows_an_empty_query_one(setup):
    text, _, session, _ = run(setup)
    queries = [params['q'] for _, params in session.calls]
    assert queries == [q1(2014), q1(2015), q1(2016), q2(2016)]  # not for the years that query 1 explained
    assert session.calls[3][1] == {'q': q2(2016), 'per_page': 1}
    assert ('| jane-doe | greenfinity | 2016 | 3 | organisation @greenfinity-hu |'
            ' https://github.com/search?q=author%3Ajanedoe+org%3Agreenfinity-hu+committer-date%3A2016-01-01..2016-12-31'
            '&type=commits |') in text


def test_query_two_with_a_count_of_zero_is_no_evidence(setup):
    text, _, _, _ = run(setup, answers={})
    assert text.split('## Proposals')[1].split('## Conflicts')[0].strip() == 'None.'


def test_the_evidence_texts(setup):
    _, added, _, _ = run(setup, write=True)
    assert [(p['from'], p['to']) for p in added] == [(2014, 2015), (2016, 2016)]
    assert added[0]['evidence'] == ('Company address @greenfinity.hu in commits 2014-2015 found by the GitHub '
                                    'commit search (example: https://github.com/plone/repo/commit/early)')
    assert added[1]['evidence'].startswith(
        'Commits in the GitHub organisation @greenfinity-hu in 2016 (3 in 2016; search: https://github.com/search?q=')


def test_organisations_without_a_handle_are_listed(setup):
    text, _, _, _ = run(setup)
    section = text.split('## Organisations without a handle')[1]
    assert '| bubblenet | 1 |' in section  # a neighbouring year of 2016 names it, and it has no handle


def test_a_proposal_for_a_verified_row_is_left_out_but_a_guess_is_not(setup):
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'jane-doe,greenfinity,2014,2014,{SOURCE},,\n'
        f'jane-doe,greenfinity,2015,2016,{SOURCE},,{GUESS}\n', encoding='utf-8')
    _, added, _, _ = run(setup, write=True)
    assert [(p['from'], p['to']) for p in added] == [(2015, 2015), (2016, 2016)]


def test_conflicts_say_whether_the_other_row_is_a_guess(setup):
    answers = {q1(2017): {'total_count': 1, 'items': [commit('jane@greenfinity.hu', '2017-01-02T10:00:00Z', 'hhh')]}}
    text, _, _, _ = run(setup, answers=answers, people=['jane-doe'], all_years=True)
    conflicts = text.split('## Conflicts')[1].split('## Unmapped')[0]
    assert '| jane-doe | 2017 | greenfinity | bubblenet | no |' in conflicts
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'jane-doe,bubblenet,2014,2016,{SOURCE},,{GUESS}\n', encoding='utf-8')
    text, _, _, _ = run(setup, answers={q1(2015): ANSWERS[q1(2015)]}, people=['jane-doe'],
                        cache=str(setup / 'cache2'))
    assert '| jane-doe | 2015 | greenfinity | bubblenet | yes |' in text


def test_the_cache_saves_requests_and_refresh_ignores_it(setup):
    _, _, first, _ = run(setup)
    assert len(first.calls) == 4
    assert os.path.exists(setup / 'cache/janedoe/2014.json')
    assert os.path.exists(setup / 'cache/janedoe/2016-org-greenfinity-hu.json')
    text, _, second, sleeps = run(setup)
    assert second.calls == [] and sleeps == []
    assert 'greenfinity | 2014-2015' in text
    _, _, third, _ = run(setup, refresh=True)
    assert len(third.calls) == 4


def test_requests_are_paced(setup):
    _, _, session, sleeps = run(setup)
    assert sleeps == [github_evidence.PACE] * len(session.calls)
    assert 2 <= github_evidence.PACE < 3


def test_write_appends_once(setup):
    _, added, _, _ = run(setup, write=True)
    assert len(added) == 2
    rows = read_rows(paths.AFFILIATION_PROPOSALS)
    assert [(r['person'], r['organisation'], r['from'], r['to']) for r in rows] == [
        ('jane-doe', 'greenfinity', 2014, 2015), ('jane-doe', 'greenfinity', 2016, 2016)]
    _, again, _, _ = run(setup, write=True)
    assert again == []
    assert len(read_rows(paths.AFFILIATION_PROPOSALS)) == 2


def test_without_write_nothing_is_written(setup):
    run(setup)
    assert read_rows(paths.AFFILIATION_PROPOSALS) == []


def test_unknown_people_and_people_without_a_login_stop_the_run(setup):
    with pytest.raises(SystemExit, match='Not in people.csv: nobody'):
        run(setup, people=['nobody'])
    with pytest.raises(SystemExit, match='No GitHub login'):
        run(setup, people=['no-login'])


def test_the_session_needs_a_token_and_sends_the_search_headers(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    with pytest.raises(SystemExit, match='GITHUB_TOKEN'):
        github_evidence.make_session()
    monkeypatch.setenv('GITHUB_TOKEN', 'secret')
    session = github_evidence.make_session()
    assert session.headers['Accept'] == 'application/vnd.github+json'
    assert session.headers['Authorization'] == 'token secret'


def test_main_prints_the_report(setup, monkeypatch, capsys):
    monkeypatch.setattr(github_evidence, 'make_session', lambda: FakeSession(ANSWERS))
    monkeypatch.setattr(github_evidence.time, 'sleep', lambda seconds: None)
    github_evidence.main(['--cache', str(setup / 'cache'), '--write'])
    out = capsys.readouterr().out
    assert out.startswith('# Affiliations from the GitHub commit search')
    assert 'Wrote 2 new proposals' in out
