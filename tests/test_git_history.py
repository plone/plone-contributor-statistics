"""Commits from local clones, including history on old release branches (#68)."""

import os
import subprocess

import pytest

from scripts.lib import git_history
from scripts.collect import plone_contributors
from scripts.lib.github_api import GitHubAPIError


def git(path, *args, date=None, email='alice@example.org'):
    env = {**os.environ, 'GIT_AUTHOR_NAME': email.split('@')[0], 'GIT_AUTHOR_EMAIL': email,
           'GIT_COMMITTER_NAME': 'committer', 'GIT_COMMITTER_EMAIL': 'committer@example.org',
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
    if date:
        env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = date
    return subprocess.run(['git', *args], cwd=path, env=env, check=True, capture_output=True, text=True).stdout.strip()


def commit(path, message, date, email='alice@example.org'):
    git(path, 'commit', '--allow-empty', '-q', '-m', message, date=date, email=email)


@pytest.fixture
def upstream(tmp_path):
    """A repository like Products.CMFPlone: the old history is only on the release branch 3.0."""
    path = tmp_path / 'upstream'
    path.mkdir()
    git(path, 'init', '-q', '-b', '3.0')
    commit(path, 'Initial revision', '2002-02-21T16:09:32+00:00', email='andyd_@localhost')
    commit(path, 'Plone 2', '2003-06-01T12:00:00+02:00')  # 10:00 UTC
    git(path, 'tag', '3.0')  # a tag with the same name as the branch

    # master starts later, without the old history ("Move 3.1 into the egg structure")
    git(path, 'checkout', '-q', '--orphan', 'master')
    commit(path, 'Move 3.1 into the egg structure', '2008-08-02T13:13:39+00:00')
    commit(path, 'Plone 4', '2010-05-01T12:00:00+00:00', email='Bob@Example.org')

    # A backport on the release branch, and a feature branch
    git(path, 'checkout', '-q', '3.0')
    commit(path, 'Backport a fix', '2009-01-01T12:00:00+00:00')
    git(path, 'checkout', '-q', '-b', 'plip-123-experiment')
    commit(path, 'Never merged', '2004-01-01T12:00:00+00:00')
    git(path, 'checkout', '-q', 'master')
    return path


def test_default_branch_plus_older_history_of_release_branches(upstream, tmp_path):
    commits = git_history.repository_commits(f'file://{upstream}', str(tmp_path / 'cache' / 'r.git'), 'master')

    by_date = {c['commit']['committer']['date']: c for c in commits}
    # Old history from 3.0, master; not the backport (2009) and not the feature branch (2004)
    assert sorted(by_date) == ['2002-02-21T16:09:32Z', '2003-06-01T10:00:00Z',
                               '2008-08-02T13:13:39Z', '2010-05-01T12:00:00Z']
    old = by_date['2002-02-21T16:09:32Z']
    assert old['commit']['author'] == {'name': 'andyd_', 'email': 'andyd_@localhost', 'date': '2002-02-21T16:09:32Z'}
    assert old['commit']['message'] == 'Initial revision'
    assert old['parents'] == [] and old['author'] is None


def test_fetch_updates_the_clone(upstream, tmp_path):
    clone = str(tmp_path / 'cache' / 'r.git')
    git_history.repository_commits(f'file://{upstream}', clone, 'master')
    commit(upstream, 'Plone 6', '2023-01-01T12:00:00+00:00')

    commits = git_history.repository_commits(f'file://{upstream}', clone, 'master')

    assert '2023-01-01T12:00:00Z' in {c['commit']['committer']['date'] for c in commits}


def test_empty_repository(tmp_path):
    path = tmp_path / 'empty'
    path.mkdir()
    git(path, 'init', '-q', '-b', 'main')

    assert git_history.repository_commits(f'file://{path}', str(tmp_path / 'cache' / 'e.git'), 'main') == []


def test_git_errors_raise(tmp_path):
    with pytest.raises(git_history.GitError):
        git_history.repository_commits(f'file://{tmp_path}/missing', str(tmp_path / 'cache' / 'm.git'), 'main')


def test_release_branches():
    branches = ['master', '2.5', '3.0', '4.3.x', '6.0.x', 'plip-123', '5.2.1-release', 'fix-3.0']

    assert git_history.release_branches(branches, 'master') == ['2.5', '3.0', '4.3.x', '6.0.x']


# Linking commits to GitHub accounts


def local_commit(sha, email, date='2003-06-01T10:00:00Z'):
    return {'sha': sha, 'parents': [{'sha': 'p'}], 'author': None,
            'commit': {'author': {'name': 'x', 'email': email, 'date': date}, 'committer': {'date': date}}}


@pytest.fixture
def extractor(tmp_repo, monkeypatch, tmp_path):
    return plone_contributors.PloneStatsExtractor(token='test-token', periods=plone_contributors.year_periods(2003, 2010))


def test_link_authors_looks_up_each_email_once(extractor, monkeypatch):
    queries = []
    users = {'s1': 'alice', 's2': None, 's4': 'bob'}  # s2: email not linked to an account

    def fake_graphql(session, query, variables=None, **kwargs):
        queries.append(query)
        shas = [part.split('"')[1] for part in query.split('object(oid: ')[1:]]
        return {'repository': {f'c{i}': {'author': {'user': {'login': users[sha]} if users[sha] else None}}
                               for i, sha in enumerate(shas)}}

    monkeypatch.setattr(plone_contributors, 'github_graphql', fake_graphql)
    commits = [local_commit('s1', 'alice@example.org'), local_commit('s2', 'andyd_@localhost'),
               local_commit('s3', 'Alice@Example.org'), local_commit('s4', 'bob@example.org')]

    extractor.link_authors('Products.CMFPlone', commits, batch_size=2)

    assert [c['author'] and c['author']['login'] for c in commits] == ['alice', None, 'alice', 'bob']
    assert len(queries) == 2  # three emails, two per query

    # Known emails are not looked up again, also not for another repository
    extractor.link_authors('plone.api', [local_commit('s5', 'bob@example.org')])
    assert len(queries) == 2


def test_github_apps_are_bots(extractor, monkeypatch):
    def fake_graphql(session, query, variables=None, **kwargs):
        return {'repository': {'c0': {'author': {'user': {'login': 'pre-commit-ci[bot]'}}}}}

    monkeypatch.setattr(plone_contributors, 'github_graphql', fake_graphql)
    commits = [local_commit('s1', '66853113+pre-commit-ci[bot]@users.noreply.github.com')]

    extractor.link_authors('volto', commits)

    assert commits[0]['author'] == {'login': 'pre-commit-ci[bot]', 'type': 'Bot'}
    assert not extractor._is_person(commits[0]['author'])


def test_link_authors_raises_on_api_errors(extractor, monkeypatch):
    def failing(session, query, variables=None, **kwargs):
        raise GitHubAPIError('HTTP 502')

    monkeypatch.setattr(plone_contributors, 'github_graphql', failing)

    with pytest.raises(GitHubAPIError):
        extractor.link_authors('volto', [local_commit('s1', 'alice@example.org')])


def test_commits_are_filtered_to_the_date_range(extractor, monkeypatch):
    monkeypatch.setattr(plone_contributors.git_history, 'repository_commits', lambda url, path, branch, token=None: [
        local_commit('a', 'alice@example.org', '2002-12-31T23:59:59Z'),
        local_commit('b', 'alice@example.org', '2003-01-01T00:00:00Z'),
        local_commit('c', 'alice@example.org', '2011-01-01T00:00:00Z'),
    ])
    linked = []
    monkeypatch.setattr(extractor, 'link_authors', lambda repo, commits: linked.extend(commits))

    commits = extractor.get_repository_commits('Products.CMFPlone', 'master')

    assert [c['sha'] for c in commits] == ['b']
    assert linked == commits


# Commits that exist twice (#78)


def test_copies_and_duplicates_are_counted_once(tmp_path):
    path = tmp_path / 'coredev'
    path.mkdir()
    git(path, 'init', '-q', '-b', 'master')
    commit(path, 'Prototype with mod_transform', '2008-07-28T12:00:00+00:00', email='paul@localhost')
    # The same commit, imported again from another SVN repository under another user name
    commit(path, 'Prototype with mod_transform', '2008-07-28T12:00:00+00:00', email='zopepaul@localhost')
    # Same message, but another time: another change
    commit(path, 'Prototype with mod_transform', '2008-07-29T12:00:00+00:00', email='paul@localhost')
    commit(path, '[fc] Repository: plone.keyring', '2015-06-01T10:00:00+00:00')
    commit(path, 'Pin plone.keyring', '2015-06-01T10:05:00+00:00')

    commits = git_history.repository_commits(f'file://{path}', str(tmp_path / 'cache' / 'c.git'), 'master')

    assert sorted((c['commit']['author']['date'], c['commit']['message']) for c in commits) == [
        ('2008-07-28T12:00:00Z', 'Prototype with mod_transform'),
        ('2008-07-29T12:00:00Z', 'Prototype with mod_transform'),
        ('2015-06-01T10:05:00Z', 'Pin plone.keyring'),
    ]
