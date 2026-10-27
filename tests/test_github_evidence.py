"""The tool that proposes affiliations from the GitHub commit search: offline, with a fake session."""

import json
import os

import pytest

from scripts.lib.addresses import mask_address
from scripts.lib import paths
from scripts.lib.model import affiliation_id, load_registry, load_sources, read_rows, source_id
from scripts.tools import check, datapackage, github_evidence
from tests.conftest import assert_no_raw_addresses, record_source

SOURCE = 'https://example.org/record'
GUESS = 'range from the current entry; years before 2026 not verified (#139)'


def write_affiliations(*rows):
    """affiliations.csv: (person, organisation, from, to, status, notes), each citing the record."""
    sid = record_source(SOURCE)
    ids = [affiliation_id(*row[:4]) for row in rows]
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n' + ''.join(
        f'{aid},{person},{org},{start},{end},{status},,{notes}\n'
        for aid, (person, org, start, end, status, notes) in zip(ids, rows)), encoding='utf-8')
    paths.CITATIONS.write_text('affiliation,source,snippet,supersedes,notes\n' + ''.join(
        f'{aid},{sid},,,\n' for aid in sorted(ids)), encoding='utf-8')


def proposed():
    return [row for row in read_rows(paths.AFFILIATIONS) if row['status'] == 'proposed']


def commit(email, date, sha):
    return {'html_url': f'https://github.com/plone/repo/commit/{sha}',
            'commit': {'author': {'email': email, 'date': date}, 'committer': {'date': date}}}


def api_commit(item):
    """The answer of the commits API for a commit the search found."""
    author = item['commit']['author']
    return {'commit': {'author': {'name': 'Jane Doe', **author}, 'message': 'Fix a bug'}}


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload, self.text = payload, json.dumps(payload)

    def json(self):
        return self.payload


class FakeSession:
    """Answers search requests from a dict {query: payload}, an unknown query with an empty result, and the
    commits API with the commits of the answers."""

    def __init__(self, answers):
        self.answers, self.calls, self.commits = answers, [], []
        self.items = {item['html_url'].rsplit('/', 1)[1]: item
                      for answer in answers.values() for item in answer.get('items', [])}

    def get(self, url, params=None, timeout=None):
        if url.startswith('https://api.github.com/repos/plone/repo/commits/'):
            self.commits.append(url)
            return Response(api_commit(self.items[url.rsplit('/', 1)[1]]))
        self.calls.append((url, dict(params)))
        return Response(self.answers.get(params['q'], {'total_count': 0, 'items': []}))


def q1(year, login='janedoe'):
    return f'author:{login} committer-date:{year}-01-01..{year}-12-31'


def q2(year, handle='greenfinity-hu', login='janedoe'):
    return f'author:{login} org:{handle} committer-date:{year}-01-01..{year}-12-31'


ANSWERS = {
    q1(2014): {'total_count': 4, 'items': [
        commit('jane@greenfinity.test', '2014-05-02T10:00:00Z', 'aaa'),
        commit('jane@greenfinity.test', '2014-03-01T10:00:00Z', 'ea7'),
        commit('jane@gmx.test', '2014-04-01T10:00:00Z', 'bbb'),
        commit('jane@janedoe.test', '2014-04-02T10:00:00Z', 'ccc'),
        commit('jane@nothing.test', '2014-04-03T10:00:00Z', 'ddd'),
        commit('', '2014-04-03T10:00:00Z', 'eee')]},
    q1(2015): {'total_count': 1, 'items': [commit('jane@greenfinity.test', '2015-01-02T10:00:00Z', 'fff')]},
    q2(2016): {'total_count': 3, 'items': [commit('x@y.test', '2016-01-01T00:00:00Z', 'abc')]},
}


@pytest.fixture
def setup(tmp_repo, monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)  # the fake session answers every request
    sid = record_source(SOURCE)
    paths.PEOPLE.write_text('id,name\njane-doe,Jane Doe\nno-login,No Login\n', encoding='utf-8')
    paths.IDENTITIES.write_text('person,kind,value,source,snippet,notes\n'
                                f'jane-doe,github,janedoe,{sid},,\nno-login,name,No Login,{sid},,\n',
                                encoding='utf-8')
    paths.ORGANISATIONS.write_text(
        'id,name,kind,github,aliases,notes\n'
        'bubblenet,BubbleNet,organisation,,,\n'
        'greenfinity,Greenfinity,organisation,greenfinity-hu,,\n', encoding='utf-8')
    write_affiliations(('jane-doe', 'greenfinity', 2014, 2016, 'assumed', GUESS),
                       ('jane-doe', 'bubblenet', 2017, 2018, 'stated', ''))
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
    assert '| jane-doe | greenfinity | 2014-2015 | 3 | address @greenfinity.test (name) |' in proposals
    # the earliest commit of the first year is the example
    assert 'https://github.com/plone/repo/commit/ea7' in proposals
    unmapped = text.split('## Unmapped domains')[1].split('## Organisations')[0]
    assert '| nothing.test | 1 | 2014 | 1 |' in unmapped
    for ignored in ('gmx.test', 'janedoe.test'):
        assert ignored not in unmapped


def test_a_rejected_year_is_not_proposed_again(setup):
    with open(paths.AFFILIATIONS, 'a', encoding='utf-8') as f:
        f.write('a00000001,jane-doe,greenfinity,2014,2014,denied,,the year of a change\n')
    text, _, _, _ = run(setup)
    proposals = text.split('## Conflicts')[0]
    assert '| jane-doe | greenfinity | 2015 | 1 | address @greenfinity.test (name) |' in proposals
    assert '2014-2015' not in proposals


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
    assert added[0]['evidence'] == ('Company address @greenfinity.test in commits 2014-2015 found by the GitHub '
                                    'commit search (example: https://github.com/plone/repo/commit/ea7)')
    assert added[1]['evidence'].startswith(
        'Commits in the GitHub organisation @greenfinity-hu in 2016 (3 in 2016; search: https://github.com/search?q=')


def test_organisations_without_a_handle_are_listed(setup):
    text, _, _, _ = run(setup)
    section = text.split('## Organisations without a handle')[1]
    assert '| bubblenet | 1 |' in section  # a neighbouring year of 2016 names it, and it has no handle


def test_a_proposal_for_a_verified_row_is_left_out_but_a_guess_is_not(setup):
    write_affiliations(('jane-doe', 'greenfinity', 2014, 2014, 'stated', ''),
                       ('jane-doe', 'greenfinity', 2015, 2016, 'assumed', GUESS))
    _, added, _, _ = run(setup, write=True)
    assert [(p['from'], p['to']) for p in added] == [(2015, 2015), (2016, 2016)]


def test_conflicts_say_whether_the_other_row_is_a_guess(setup):
    answers = {q1(2017): {'total_count': 1, 'items': [commit('jane@greenfinity.test', '2017-01-02T10:00:00Z', 'dad')]}}
    text, _, _, _ = run(setup, answers=answers, people=['jane-doe'], all_years=True)
    conflicts = text.split('## Conflicts')[1].split('## Unmapped')[0]
    assert '| jane-doe | 2017 | greenfinity | bubblenet | no |' in conflicts
    write_affiliations(('jane-doe', 'bubblenet', 2014, 2016, 'assumed', GUESS))
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
    _, added, session, _ = run(setup, write=True)
    assert len(added) == 2
    rows = proposed()
    assert [(r['person'], r['organisation'], r['from'], r['to']) for r in rows] == [
        ('jane-doe', 'greenfinity', 2014, 2015), ('jane-doe', 'greenfinity', 2016, 2016)]
    _, again, second, _ = run(setup, write=True)
    assert again == []
    assert len(proposed()) == 2
    assert second.commits == []  # captured once
    datapackage.main([])
    assert check.validate() == []


def test_the_example_commits_are_captured_and_cited(setup):
    _, _, session, _ = run(setup, write=True)
    early, org = 'https://github.com/plone/repo/commit/ea7', 'https://github.com/plone/repo/commit/abc'
    assert session.commits == ['https://api.github.com/repos/plone/repo/commits/ea7',
                               'https://api.github.com/repos/plone/repo/commits/abc']
    citations = {r['affiliation']: r for r in read_rows(paths.CITATIONS)}
    address = citations[affiliation_id('jane-doe', 'greenfinity', 2014, 2015)]
    assert (address['source'], address['snippet'], address['notes']) == (
        source_id(early), f'Author: Jane Doe <{mask_address("jane@greenfinity.test", True)}>', None)
    organisation = citations[affiliation_id('jane-doe', 'greenfinity', 2016, 2016)]
    assert (organisation['source'], organisation['snippet']) == (
        source_id(org), f'Author: Jane Doe <{mask_address("x@y.test", True)}>')
    assert organisation['notes'] == ('one of 3 commits in the GitHub organisation @greenfinity-hu in 2016 that the '
                                     'search https://github.com/search?q=author%3Ajanedoe+org%3Agreenfinity-hu+'
                                     'committer-date%3A2016-01-01..2016-12-31&type=commits found')
    assert load_sources()[source_id(early)].kind == 'commit'
    assert_no_raw_addresses()


def test_without_write_nothing_is_written(setup):
    before = paths.AFFILIATIONS.read_text(encoding='utf-8')
    run(setup)
    assert paths.AFFILIATIONS.read_text(encoding='utf-8') == before


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


def test_main_reports_an_id_clash_without_a_traceback(setup, monkeypatch, capsys):
    def clash(*args, **kwargs):
        raise ValueError('The id a12345678 is the id of an affiliation already')

    monkeypatch.setattr(github_evidence, 'run', clash)
    with pytest.raises(SystemExit) as exit_info:
        github_evidence.main(['--write'])
    assert exit_info.value.code == 1
    assert capsys.readouterr().err == 'Nothing written: The id a12345678 is the id of an affiliation already\n'


def test_main_reports_a_cell_of_the_wrong_type_as_itself(setup, monkeypatch, capsys):
    from scripts.lib.model.schema import CellTypeError

    def bad_cell(*args, **kwargs):
        raise CellTypeError('affiliations.csv, row 2, field from: cannot read "20O5" (type is "integer/default")')

    monkeypatch.setattr(github_evidence, 'run', bad_cell)
    with pytest.raises(SystemExit) as exit_info:
        github_evidence.main(['--write'])
    assert exit_info.value.code == 1
    assert capsys.readouterr().err == ('affiliations.csv, row 2, field from: cannot read "20O5" '
                                       '(type is "integer/default")\n')
