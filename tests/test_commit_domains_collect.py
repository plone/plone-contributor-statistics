"""The collector of commit mail domains per person and year: offline, with real git repositories."""

import csv
import os

import pytest

from scripts.collect import plone_commit_domains
from scripts.lib import paths
from scripts.lib.commit_authors import Finder
from scripts.lib.model import load_bot_accounts, load_registry
from tests.conftest import record_source
from tests.test_address_proposals import SOURCE, git, make_clone


@pytest.fixture
def setup(tmp_repo, write_registers):
    write_registers(people=[('jane-doe', 'janedoe'), ('bob-builder', '')], affiliations=[],
                    organisations=[('acme', 'Acme Industries')])
    sid = record_source(SOURCE)
    paths.PEOPLE.write_text('id,name\nbob-builder,Bob Builder\njane-doe,Jane Doe\n', encoding='utf-8')
    paths.IDENTITIES.write_text('person,kind,value,source,snippet,notes\n'
                                f'bob-builder,email,bob@old.test,{sid},,\n'
                                f'jane-doe,email,j.doe@ACME.test.,{sid},,\n'
                                f'jane-doe,email,jane@acme.test,{sid},,\n'
                                f'jane-doe,github,janedoe,{sid},,\n', encoding='utf-8')
    paths.BOT_ACCOUNTS.write_text('login,reason\nrobot,a bot\n', encoding='utf-8')
    return tmp_repo


def run(tmp_path, repositories):
    clones = [make_clone(tmp_path, name, commits)[1] for name, commits in repositories.items()]
    registry = load_registry()
    finder = Finder(registry, load_bot_accounts())
    return plone_commit_domains.collect(list(zip(repositories, clones)), finder, registry)


def test_a_commit_on_two_branches_counts_once(setup, tmp_path):
    work, bare = make_clone(tmp_path, 'a', [('Jane Doe', 'jane@acme.test', 2010)])
    git(work, 'branch', 'other')
    git(work, 'push', '-q', str(bare), 'other')
    registry = load_registry()
    counts = plone_commit_domains.collect([('a', bare)], Finder(registry, load_bot_accounts()), registry)
    assert counts == {2010: {('janedoe', 'acme.test'): 1}}


def test_counts_add_up_per_domain(setup, tmp_path):
    counts = run(tmp_path, {
        'a': [('Jane Doe', 'jane@acme.test', 2010), ('Jane', 'j.doe@ACME.test.', 2010)],
        'b': [('Jane Doe', 'jane@acme.test', 2010, 'another change'),
              ('Jane Doe', '1+janedoe@users.noreply.github.com', 2011)]})
    assert counts[2010] == {('janedoe', 'acme.test'): 3}
    assert counts[2011] == {('janedoe', 'users.noreply.github.com'): 1}


def test_a_commit_in_two_clones_counts_once(setup, tmp_path):
    # Repositories that share history, such as a repository and its copy, hold the same commits
    work, bare = make_clone(tmp_path, 'a', [('Jane Doe', 'jane@acme.test', 2010)])
    other = tmp_path / 'plone' / 'b.git'
    git(tmp_path, 'clone', '-q', '--bare', str(work), str(other))
    registry = load_registry()
    counts = plone_commit_domains.collect([('a', bare), ('b', other)], Finder(registry, load_bot_accounts()), registry)
    assert counts == {2010: {('janedoe', 'acme.test'): 1}}


def test_the_copies_in_buildout_coredev_are_skipped(setup, tmp_path):
    counts = run(tmp_path, {'buildout.coredev': [
        ('Jane Doe', 'jane@acme.test', 2010, '[fc] Repository: plone.app.x\n\nBranch: refs/heads/master\n'),
        ('Jane Doe', 'jane@acme.test', 2010, 'Update the versions')]})
    assert counts == {2010: {('janedoe', 'acme.test'): 1}}


def test_the_same_change_twice_in_a_repository_counts_once(setup, tmp_path):
    # Same author date and message, another commit: a rebased branch that was merged as well
    counts = run(tmp_path, {'a': [('Jane Doe', 'jane@acme.test', 2010, 'Fix the thing'),
                                  ('Jane Doe', 'jane@acme.test', 2010, 'Fix the thing')]})
    assert counts == {2010: {('janedoe', 'acme.test'): 1}}


def test_machine_names_are_skipped(setup, tmp_path):
    paths.IDENTITIES.write_text(paths.IDENTITIES.read_text(encoding='utf-8')
                                + f'jane-doe,email,jane@janes-imac.local,{SOURCE}\n', encoding='utf-8')
    counts = run(tmp_path, {'a': [('Jane Doe', 'jane@janes-imac.local', 2010), ('Jane Doe', 'jane@acme.test', 2011)]})
    assert counts == {2011: {('janedoe', 'acme.test'): 1}}


def test_unidentified_authors_and_bots_are_skipped(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Stranger', 'x@nowhere.test', 2010), ('robot', 'robot@acme.test', 2010),
                                  ('Jane Doe', 'jane@acme.test', 2010)]})
    assert counts == {2010: {('janedoe', 'acme.test'): 1}}


def test_converted_commits_are_skipped(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Jane Doe', 'jane@acme.test', 2005, 'Fix\n\nsvn path=/x/; revision=3\n')]})
    assert counts == {}


def test_a_year_without_commits_has_a_header_only_file(setup, tmp_path):
    plone_commit_domains.write({2010: {('janedoe', 'acme.test'): 2}}, range(2009, 2012))
    assert paths.commit_domains_file(2009).read_text(encoding='utf-8') == 'username,domain,commits\n'
    assert paths.commit_domains_file(2011).read_text(encoding='utf-8') == 'username,domain,commits\n'
    with open(paths.commit_domains_file(2010), encoding='utf-8') as handle:
        assert list(csv.DictReader(handle)) == [{'username': 'janedoe', 'domain': 'acme.test', 'commits': '2'}]


def test_rows_are_sorted(setup):
    plone_commit_domains.write({2010: {('b', 'x.test'): 1, ('a', 'z.test'): 1, ('a', 'y.test'): 1,
                                       ('a', 'w.test'): 5}}, [2010])
    lines = paths.commit_domains_file(2010).read_text(encoding='utf-8').splitlines()[1:]
    assert lines == ['a,w.test,5', 'a,y.test,1', 'a,z.test,1', 'b,x.test,1']


def test_username_is_the_collected_key(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Bob Builder', 'bob@old.test', 2010)]})
    assert counts == {2010: {('person:bob-builder', 'old.test'): 1}}


def test_the_cache_must_hold_clones(setup, tmp_path):
    with pytest.raises(SystemExit, match='make run-changelogs'):
        plone_commit_domains.main(['--cache', str(tmp_path / 'empty')])


def test_first_year_after_last_year_is_a_usage_error(setup, capsys):
    with pytest.raises(SystemExit) as exit_info:
        plone_commit_domains.main(['--first-year', '2020', '--last-year', '2019'])
    assert exit_info.value.code == 2
    assert '--first-year must not be after --last-year' in capsys.readouterr().err
