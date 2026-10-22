"""The helpers that find the person behind a commit author and the mail domain of an address."""

import os
import subprocess

import pytest

from scripts.lib import git_history
from scripts.lib.commit_authors import domain_of, is_company_domain
from tests.test_address_proposals import make_clone

# Names of machines and placeholders, no public mail domains; some of them carry a person's name
LOCAL_NAMES = ['pepper.local', 'katjas-imac.local', 'office.lan', 'box.home', 'api.localdomain',
               'localhost.localdomain', 'timos-mbp.fritz.box', 'ip-1.2.3.4.in-addr.arpa', 'rudolf.(none)',
               'pawel-dell.(none)', 'planetmobile', 'example.com', 'example.org', 'mail.example.net',
               'acme.example']


def test_domain_of_folds_case_and_trailing_dot():
    assert domain_of('Jane@Foo.COM.') == 'foo.com'
    assert domain_of(' jane@foo.com ') == 'foo.com'
    assert domain_of('a@b@mail.Foo.com') == 'mail.foo.com'


def test_domain_of_skips_svn_and_localhost():
    assert domain_of('andyd@localhost') is None
    assert domain_of('Andy@LOCALHOST.') is None
    assert domain_of('jane@6a2e9a5c-0e3f-0410-9a18-ab4d3b6c1e0d') is None
    assert domain_of('jane@users.sourceforge.net') is None
    assert domain_of('no-at-sign') is None
    assert domain_of('jane@') is None


@pytest.mark.parametrize('domain', LOCAL_NAMES)
def test_domain_of_skips_the_names_of_machines_and_placeholders(domain):
    assert domain_of(f'jane@{domain}') is None
    assert domain_of(f'jane@{domain.upper()}.') is None


@pytest.mark.parametrize('domain', LOCAL_NAMES)
def test_the_names_of_machines_and_placeholders_name_no_company(domain):
    assert not is_company_domain(domain)


def test_public_domains_that_look_local_are_kept():
    assert domain_of('jane@localhost-systems.com') == 'localhost-systems.com'
    assert domain_of('jane@example.company.de') == 'example.company.de'
    assert domain_of('jane@homes.de') == 'homes.de'


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


def test_read_authors_can_leave_out_copies_and_duplicates(tmp_path):
    work, _ = make_clone(tmp_path, 'a', [
        ('Ann', 'ann@x.test', 2010, 'Fix the thing'),
        ('Ann', 'ann@x.test', 2010, 'Fix the thing'),  # the same change again, e.g. a rebased branch
        ('Bo', 'bo@y.test', 2011, '[fc] Repository: plone.app.x'),  # the automatic copy in buildout.coredev
        ('Cy', 'cy@z.test', 2010, 'Fix the other thing'),
        ('Di', 'di@w.test', 2012, 'Fix the thing'),  # the same message at another time
    ])
    assert len(git_history.read_authors(work)) == 5
    assert sorted(a[1] for a in git_history.read_authors(work, duplicates=False)) == [
        'ann@x.test', 'cy@z.test', 'di@w.test']
