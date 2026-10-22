"""The collector of commit mail domains per person and year: offline, with real git repositories."""

import csv
import os

import pytest

from scripts.collect import plone_commit_domains
from scripts.lib import paths
from scripts.lib.commit_authors import Finder
from scripts.lib.model import load_bot_accounts, load_registry
from tests.test_address_proposals import SOURCE, git, make_clone


@pytest.fixture
def setup(tmp_repo, write_registers):
    write_registers(people=[('jane-doe', 'janedoe'), ('bob-builder', '')], affiliations=[],
                    organisations=[('acme', 'Acme Industries')])
    paths.PEOPLE.write_text(
        'id,name,github,source\n'
        f'bob-builder,Bob Builder,,{SOURCE}\n'
        f'jane-doe,Jane Doe,janedoe,{SOURCE}\n', encoding='utf-8')
    paths.IDENTITIES.write_text('person,kind,value,source\n'
                                f'bob-builder,email,bob@old.example.org,{SOURCE}\n'
                                f'jane-doe,email,jane@acme.example,{SOURCE}\n'
                                f'jane-doe,email,j.doe@ACME.example.,{SOURCE}\n', encoding='utf-8')
    paths.BOT_ACCOUNTS.write_text('login,reason\nrobot,a bot\n', encoding='utf-8')
    return tmp_repo


def run(tmp_path, repositories):
    clones = [make_clone(tmp_path, name, commits)[1] for name, commits in repositories.items()]
    registry = load_registry()
    finder = Finder(registry, load_bot_accounts())
    return plone_commit_domains.collect(list(zip(repositories, clones)), finder, registry)


def test_a_commit_on_two_branches_counts_once(setup, tmp_path):
    work, bare = make_clone(tmp_path, 'a', [('Jane Doe', 'jane@acme.example', 2010)])
    git(work, 'branch', 'other')
    git(work, 'push', '-q', str(bare), 'other')
    registry = load_registry()
    counts = plone_commit_domains.collect([('a', bare)], Finder(registry, load_bot_accounts()), registry)
    assert counts == {2010: {('janedoe', 'acme.example'): 1}}


def test_counts_add_up_per_domain(setup, tmp_path):
    counts = run(tmp_path, {
        'a': [('Jane Doe', 'jane@acme.example', 2010), ('Jane', 'j.doe@ACME.example.', 2010)],
        'b': [('Jane Doe', 'jane@acme.example', 2010), ('Jane Doe', '1+janedoe@users.noreply.github.com', 2011)]})
    assert counts[2010] == {('janedoe', 'acme.example'): 3}
    assert counts[2011] == {('janedoe', 'users.noreply.github.com'): 1}


def test_unidentified_authors_and_bots_are_skipped(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Stranger', 'x@nowhere.example', 2010), ('robot', 'robot@acme.example', 2010),
                                  ('Jane Doe', 'jane@acme.example', 2010)]})
    assert counts == {2010: {('janedoe', 'acme.example'): 1}}


def test_converted_commits_are_skipped(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Jane Doe', 'jane@acme.example', 2005, 'Fix\n\nsvn path=/x/; revision=3\n')]})
    assert counts == {}


def test_a_year_without_commits_has_a_header_only_file(setup, tmp_path):
    plone_commit_domains.write({2010: {('janedoe', 'acme.example'): 2}}, range(2009, 2012))
    assert paths.commit_domains_file(2009).read_text(encoding='utf-8') == 'username,domain,commits\n'
    assert paths.commit_domains_file(2011).read_text(encoding='utf-8') == 'username,domain,commits\n'
    with open(paths.commit_domains_file(2010), encoding='utf-8') as handle:
        assert list(csv.DictReader(handle)) == [{'username': 'janedoe', 'domain': 'acme.example', 'commits': '2'}]


def test_rows_are_sorted(setup):
    plone_commit_domains.write({2010: {('b', 'x.example'): 1, ('a', 'z.example'): 1, ('a', 'y.example'): 1,
                                       ('a', 'w.example'): 5}}, [2010])
    lines = paths.commit_domains_file(2010).read_text(encoding='utf-8').splitlines()[1:]
    assert lines == ['a,w.example,5', 'a,y.example,1', 'a,z.example,1', 'b,x.example,1']


def test_username_is_the_collected_key(setup, tmp_path):
    counts = run(tmp_path, {'a': [('Bob Builder', 'bob@old.example.org', 2010)]})
    assert counts == {2010: {('person:bob-builder', 'old.example.org'): 1}}


def test_the_cache_must_hold_clones(setup, tmp_path):
    with pytest.raises(SystemExit, match='make run-changelogs'):
        plone_commit_domains.main(['--cache', str(tmp_path / 'empty')])
