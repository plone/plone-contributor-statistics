"""The helpers that find the person behind a commit author and the mail domain of an address."""

import os
import subprocess

from scripts.lib import git_history
from scripts.lib.commit_authors import domain_of


def test_domain_of_folds_case_and_trailing_dot():
    assert domain_of('Jane@Foo.COM.') == 'foo.com'
    assert domain_of(' jane@foo.com ') == 'foo.com'
    assert domain_of('a@b@mail.Foo.com') == 'mail.foo.com'


def test_domain_of_skips_svn_and_localhost():
    assert domain_of('andyd@localhost') is None
    assert domain_of('Andy@LOCALHOST.') is None
    assert domain_of('jane@6a2e9a5c-0e3f-0410-9a18-ab4d3b6c1e0d') is None
    assert domain_of('no-at-sign') is None
    assert domain_of('jane@') is None


def test_domain_of_noreply():
    assert domain_of('1234+janedoe@users.noreply.github.com') == 'users.noreply.github.com'
    assert domain_of('janedoe@Users.Noreply.GitHub.com') == 'users.noreply.github.com'


def test_read_authors_without_merges(tmp_path):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 'Ann', 'GIT_AUTHOR_EMAIL': 'ann@x.example',
           'GIT_COMMITTER_NAME': 'Ann', 'GIT_COMMITTER_EMAIL': 'ann@x.example',
           'GIT_AUTHOR_DATE': '2012-01-01T00:00:00Z', 'GIT_COMMITTER_DATE': '2012-01-01T00:00:00Z',
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

    def git(*args):
        subprocess.run(['git', *args], cwd=tmp_path, env=env, check=True, capture_output=True)

    git('init', '-q', '-b', 'main')
    git('commit', '--allow-empty', '-q', '-m', 'first')
    git('checkout', '-q', '-b', 'feature')
    git('commit', '--allow-empty', '-q', '-m', 'on a branch')
    git('checkout', '-q', 'main')
    git('commit', '--allow-empty', '-q', '-m', 'on main')
    git('merge', '--no-ff', '-q', '-m', 'Merge feature', 'feature')
    assert len(git_history.read_authors(tmp_path)) == 4
    assert len(git_history.read_authors(tmp_path, merges=False)) == 3
