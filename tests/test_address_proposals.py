"""The tool that proposes affiliations from company addresses in commits: offline, with real git repositories."""

import os
import subprocess

import pytest

from scripts.lib import git_history, paths
from scripts.lib.model import load_registry, read_rows
from scripts.tools import address_proposals, check, datapackage

SOURCE = 'https://example.org/record'
NOREPLY = '1234+janedoe@users.noreply.github.com'


def git(path, *args, author=('Someone', 'someone@example.org'), date=None):
    env = {**os.environ, 'GIT_AUTHOR_NAME': author[0], 'GIT_AUTHOR_EMAIL': author[1],
           'GIT_COMMITTER_NAME': 'committer', 'GIT_COMMITTER_EMAIL': 'committer@example.org',
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
    if date:
        env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = date
    return subprocess.run(['git', *args], cwd=path, env=env, check=True, capture_output=True, text=True).stdout


def make_clone(cache, repository, commits):
    """A bare clone at <cache>/plone/<repository>.git; commits are (name, email, year)."""
    work = cache / 'work' / repository
    work.mkdir(parents=True)
    git(work, 'init', '-q', '-b', 'main')
    for number, (name, email, year) in enumerate(commits):
        git(work, 'commit', '--allow-empty', '-q', '-m', f'change {number}', author=(name, email),
            date=f'{year}-06-01T12:00:00Z')
    target = cache / 'plone' / f'{repository}.git'
    target.parent.mkdir(parents=True, exist_ok=True)
    git(cache, 'clone', '-q', '--bare', str(work), str(target))
    return work, target


def sha_of(work, number=0):
    return git(work, 'log', '--reverse', '--format=%H').split()[number]


@pytest.fixture
def setup(tmp_repo, write_registers):
    write_registers(
        people=[('jane-doe', 'janedoe'), ('hanno-schlichting', 'hannosch'), ('mononym', ''), ('bob-builder', '')],
        affiliations=[('jane-doe', 'oldco', 2012, 2012)],
        organisations=[('greenfinity', 'Greenfinity'), ('bubblenet', 'BubbleNet'), ('oldco', 'Old Co'),
                       ('acme', 'Acme Industries')])
    paths.PEOPLE.write_text(
        'id,name,github,source\n'
        f'bob-builder,Bob Builder,,{SOURCE}\n'
        f'hanno-schlichting,Hanno Schlichting,hannosch,{SOURCE}\n'
        f'jane-doe,Jane Doe,janedoe,{SOURCE}\n'
        f'mononym,Mononym,,{SOURCE}\n', encoding='utf-8')
    paths.IDENTITIES.write_text('person,kind,value,source\n'
                                f'bob-builder,email,bob@old.example.org,{SOURCE}\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text(
        'id,name,kind,aliases,notes\n'
        'acme,Acme Industries,organisation,acme-industries.example;widgets.example,\n'
        'bubblenet,BubbleNet,organisation,,\n'
        'greenfinity,Greenfinity,organisation,,\n'
        'oldco,Old Co,organisation,,\n', encoding='utf-8')
    paths.BOT_ACCOUNTS.write_text('login,reason\nrobot,a bot\n', encoding='utf-8')
    return tmp_repo


def run(cache, **kwargs):
    return address_proposals.run(str(cache), **kwargs)


def test_read_authors_of_bare_and_non_bare_clones(tmp_path):
    work, bare = make_clone(tmp_path, 'a', [('Ann Author', 'ann@x.example', 2010), ('Bo Bee', 'bo@y.example', 2011)])
    for path in (work, bare):
        assert sorted(git_history.read_authors(path), key=lambda a: a[3]) == [
            (sha_of(work, 0), 'ann@x.example', 'Ann Author', 2010),
            (sha_of(work, 1), 'bo@y.example', 'Bo Bee', 2011)]


def test_read_authors_includes_other_branches(tmp_path):
    work, _ = make_clone(tmp_path, 'a', [('Ann', 'ann@x.example', 2010)])
    git(work, 'checkout', '-q', '-b', 'feature')
    git(work, 'commit', '--allow-empty', '-q', '-m', 'on a branch', author=('Bo', 'bo@y.example'),
        date='2012-01-01T00:00:00Z')
    git(work, 'checkout', '-q', 'main')
    assert {a[1] for a in git_history.read_authors(work)} == {'ann@x.example', 'bo@y.example'}


def test_organisation_for_domain(setup):
    registry = load_registry()
    assert registry.organisation_for_domain('greenfinity.hu') == 'greenfinity'
    assert registry.organisation_for_domain('mail.bubblenet.be') == 'bubblenet'
    assert registry.organisation_for_domain('widgets.example') == 'acme'  # an alias
    assert registry.organisation_for_domain('acme.example') == 'acme'  # the first word of the name
    assert registry.organisation_for_domain('nothing.example') is None
    assert registry.organisation_for_domain('greenfinity') is None  # no dot: the label is the top-level domain


def test_organisation_for_domain_ignores_independents_and_ambiguous_keys(tmp_repo, write_registers):
    write_registers(organisations=[('one', 'Twin One'), ('two', 'Twin Two')])
    paths.ORGANISATIONS.write_text(
        'id,name,kind,aliases,notes\none,Twin One,organisation,,\ntwo,Twin Two,organisation,,\n'
        'solo,Twin Solo (independent),independent,,\n', encoding='utf-8')
    registry = load_registry()
    assert registry.organisation_for_domain('twin.example') is None  # the first word names three organisations
    assert registry.organisation_for_domain('twinone.example') == 'one'


def test_matching_by_login_email_and_name(setup):
    finder = address_proposals.Finder(load_registry(), [])
    assert finder.person(NOREPLY, 'J').id == 'jane-doe'
    assert finder.person('janedoe@users.noreply.github.com', 'J').id == 'jane-doe'
    assert finder.person('jane@greenfinity.hu', 'J') is None
    assert finder.person('hanno@bubblenet.be', 'Hanno Schlichting').id == 'hanno-schlichting'
    assert finder.person('bob@old.example.org', 'Bob').id == 'bob-builder'
    assert finder.person('mono@greenfinity.hu', 'Mononym') is None


def test_bots_are_skipped(setup):
    finder = address_proposals.Finder(load_registry(), ['robot'])
    assert finder.person('49699333+dependabot[bot]@users.noreply.github.com', 'dependabot[bot]') is None
    assert finder.person('robot@users.noreply.github.com', 'robot') is None
    assert finder.person('x@greenfinity.hu', 'robot[bot]') is None


@pytest.mark.parametrize('domain,company', [
    ('greenfinity.hu', True), ('gmail.com', False), ('yahoo.co.uk', False), ('hotmail.fr', False),
    ('plone.org', False), ('zope.org', False), ('users.noreply.github.com', False), ('localhost', False),
    ('myhost.local', False), ('intranet', False), ('(none)', False), ('example.lan', False),
    ('1b3f2c4d-0000-4000-8000-123456789abc', False),
    ('hannosch.eu', False),  # the stem is a part of the name of Hanno Schlichting
    ('janedoe.net', False),  # the login
    ('icts.kuleuven.be', True),
])
def test_company_domain(domain, company):
    class P:
        name = 'Hanno Schlichting'
        github = 'janedoe'
    assert address_proposals.is_company_domain(domain, P) is company


def test_proposals_runs_evidence_and_unmapped(setup):
    cache = setup / 'cache'
    work, _ = make_clone(cache, 'plone.app.x', [
        ('Hanno Schlichting', 'hanno@greenfinity.hu', 2016),
        ('Hanno Schlichting', 'hanno@greenfinity.hu', 2017),
        ('Hanno Schlichting', 'hanno@greenfinity.hu', 2017),
        ('Hanno Schlichting', 'hanno@greenfinity.hu', 2019),
        ('Hanno Schlichting', 'hanno@hannosch.eu', 2016),  # own domain
        ('Hanno Schlichting', 'hanno@gmail.com', 2016),  # personal
        ('Hanno Schlichting', 'hanno@localhost', 2005),  # Subversion era
        ('Hanno Schlichting', 'hanno@widgets.example', 2018),  # alias
        ('Hanno Schlichting', 'hanno@mystery.example', 2018),  # unmapped
        ('Hanno Schlichting', 'hanno@mystery.example', 2019),
        ('Stranger', 'x@greenfinity.hu', 2016),  # nobody
        ('dependabot[bot]', '1+dependabot[bot]@users.noreply.github.com', 2016),
    ])
    text, added = run(cache)
    sha = sha_of(work, 0)
    assert added == []
    assert f'| hanno-schlichting | greenfinity | 2016-2017 | 3 | plone.app.x@{sha[:10]} |' in text
    proposals, conflicts = address_proposals.propose(load_registry(), address_proposals.gather(
        [('plone.app.x', str(cache / 'plone' / 'plone.app.x.git'))],
        address_proposals.Finder(load_registry(), []), 2002)[0])
    assert [(p['organisation'], p['from'], p['to'], p['commits']) for p in proposals] == [
        ('acme', 2018, 2018, 1), ('greenfinity', 2016, 2017, 3), ('greenfinity', 2019, 2019, 1)]
    green = proposals[1]
    assert green['evidence'] == (f'Company address @greenfinity.hu in commits 2016-2017 '
                                 f'(example: https://github.com/plone/plone.app.x/commit/{sha})')
    assert conflicts == []
    assert '## Proposals' in text and '## Conflicts' in text and '## Unmapped domains' in text
    assert '| mystery.example | 2 | 2018-2019 | 1 |' in text
    assert 'hannosch.eu' not in text and 'gmail' not in text and 'localhost' not in text


def test_covered_year_splits_the_run_and_other_organisation_conflicts(setup):
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'jane-doe,greenfinity,2016,2016,{SOURCE},,\n'
        f'jane-doe,oldco,2018,2018,{SOURCE},,\n', encoding='utf-8')
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', y) for y in (2015, 2016, 2017, 2018)])
    text, _ = run(cache)
    proposals, conflicts = address_proposals.propose(load_registry(), address_proposals.gather(
        [('r', str(cache / 'plone' / 'r.git'))], address_proposals.Finder(load_registry(), []), 2002)[0])
    assert [(p['from'], p['to']) for p in proposals] == [(2015, 2015), (2017, 2018)]  # 2016 is covered already
    assert conflicts == [{'person': 'jane-doe', 'from': 2018, 'to': 2018, 'proposed': 'greenfinity',
                          'existing': 'oldco'}]
    assert '| jane-doe | 2018 | greenfinity | oldco |' in text


def test_since(setup):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', y) for y in (2005, 2010)])
    text, _ = run(cache, since=2008)
    assert '| jane-doe | greenfinity | 2010 |' in text
    assert '2005' not in text


def test_person_option(setup):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', 2015),
                            ('Hanno Schlichting', 'hanno@bubblenet.be', 2015),
                            ('Hanno Schlichting', 'hanno@mystery.example', 2015)])
    text, _ = run(cache, people=['hanno-schlichting'])
    assert 'bubblenet' in text and 'jane-doe' not in text and 'mystery.example' in text
    with pytest.raises(SystemExit, match='nobody'):
        run(cache, people=['nobody'])


def test_write_appends_once_and_stays_valid(setup):
    cache = setup / 'cache'
    work, _ = make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', y) for y in (2015, 2016)])
    _, added = run(cache, write=True)
    assert len(added) == 1
    rows = read_rows(paths.AFFILIATION_PROPOSALS)
    assert rows == [{'person': 'jane-doe', 'organisation': 'greenfinity', 'from': 2015, 'to': 2016,
                     'evidence': f'Company address @greenfinity.hu in commits 2015-2016 '
                                 f'(example: https://github.com/plone/r/commit/{sha_of(work, 0)})'}]
    _, again = run(cache, write=True)
    assert again == []
    assert len(read_rows(paths.AFFILIATION_PROPOSALS)) == 1
    datapackage.main([])
    assert check.validate() == []


def test_no_write_leaves_the_file_alone(setup):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', 2015)])
    run(cache)
    assert read_rows(paths.AFFILIATION_PROPOSALS) == []


def test_missing_cache_names_the_command(setup):
    with pytest.raises(SystemExit, match='make run-changelogs'):
        run(setup / 'nowhere')


def test_main_prints_the_report(setup, capsys):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', 2015)])
    address_proposals.main(['--cache', str(cache)])
    assert '## Proposals' in capsys.readouterr().out
