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
    """A bare clone at <cache>/plone/<repository>.git; commits are (name, email, year or full date[, message])."""
    work = cache / 'work' / repository
    work.mkdir(parents=True)
    git(work, 'init', '-q', '-b', 'main')
    for number, (name, email, year, *message) in enumerate(commits):
        git(work, 'commit', '--allow-empty', '-q', '-m', message[0] if message else f'change {number}',
            author=(name, email), date=year if isinstance(year, str) else f'{year}-06-01T12:00:00Z')
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
        'id,name,kind,github,aliases,notes\n'
        'acme,Acme Industries,organisation,,acme-industries.test;widgets.test,\n'
        'bubblenet,BubbleNet,organisation,,,\n'
        'greenfinity,Greenfinity,organisation,,,\n'
        'oldco,Old Co,organisation,,,\n', encoding='utf-8')
    paths.BOT_ACCOUNTS.write_text('login,reason\nrobot,a bot\n', encoding='utf-8')
    return tmp_repo


def run(cache, **kwargs):
    return address_proposals.run(str(cache), **kwargs)


def test_read_authors_of_bare_and_non_bare_clones(tmp_path):
    work, bare = make_clone(tmp_path, 'a', [('Ann Author', 'ann@x.test', 2010), ('Bo Bee', 'bo@y.test', 2011)])
    for path in (work, bare):
        assert sorted(git_history.read_authors(path), key=lambda a: a[3]) == [
            (sha_of(work, 0), 'ann@x.test', 'Ann Author', '2010-06-01T12:00:00Z'),
            (sha_of(work, 1), 'bo@y.test', 'Bo Bee', '2011-06-01T12:00:00Z')]


def test_read_authors_includes_other_branches(tmp_path):
    work, _ = make_clone(tmp_path, 'a', [('Ann', 'ann@x.test', 2010)])
    git(work, 'checkout', '-q', '-b', 'feature')
    git(work, 'commit', '--allow-empty', '-q', '-m', 'on a branch', author=('Bo', 'bo@y.test'),
        date='2012-01-01T00:00:00Z')
    git(work, 'checkout', '-q', 'main')
    assert {a[1] for a in git_history.read_authors(work)} == {'ann@x.test', 'bo@y.test'}


def test_read_authors_can_leave_out_the_commits_imported_from_subversion(tmp_path):
    work, _ = make_clone(tmp_path, 'a', [
        ('Ann', 'ann@x.test', 2010),
        ('Bo', 'bo@y.test', 2005, 'Fix the thing\n\nsvn path=/CMFPlone/trunk/; revision=917\n'),
        ('Cy', 'cy@z.test', 2006, 'Fix\n\ngit-svn-id: https://svn.test/trunk@12 0000-uuid\n'),
        ('Di', 'di@w.test', 2012, 'Mentions svn path= and revision=3 in the middle of a line'),
    ])
    everything = {'ann@x.test', 'bo@y.test', 'cy@z.test', 'di@w.test'}
    assert {a[1] for a in git_history.read_authors(work)} == everything
    assert {a[1] for a in git_history.read_authors(work, converted=False)} == {'ann@x.test', 'di@w.test'}


def test_organisation_for_domain(setup):
    registry = load_registry()
    assert registry.organisation_for_domain('greenfinity.hu') == 'greenfinity'
    assert registry.organisation_for_domain('mail.bubblenet.be') == 'bubblenet'
    assert registry.organisation_for_domain('widgets.test') == 'acme'  # an alias
    assert registry.organisation_for_domain('acme.test') == 'acme'  # the first word of the name
    assert registry.organisation_for_domain('nothing.test') is None
    assert registry.organisation_for_domain('greenfinity') is None  # no dot: the label is the top-level domain


def test_domain_keys_have_two_tiers(tmp_repo, write_registers):
    write_registers(organisations=[('acme', 'Acme'), ('acme-industries', 'Acme Industries'),
                                   ('other', 'Other Thing')])
    registry = load_registry()
    assert registry.match_domain('acme.com') == ('acme', 'name')  # the whole name beats the first word
    assert registry.match_domain('acmeindustries.com') == ('acme-industries', 'name')
    assert registry.match_domain('other.com') == ('other', 'first word')
    assert registry.match_domain('x.com') is None


def test_match_domain_says_alias(setup):
    registry = load_registry()
    assert registry.match_domain('widgets.test') == ('acme', 'alias')
    assert registry.match_domain('acme.test') == ('acme', 'first word')
    assert registry.match_domain('greenfinity.hu') == ('greenfinity', 'name')


def test_organisation_for_domain_ignores_independents_and_ambiguous_keys(tmp_repo, write_registers):
    write_registers(organisations=[('one', 'Twin One'), ('two', 'Twin Two')])
    paths.ORGANISATIONS.write_text(
        'id,name,kind,github,aliases,notes\none,Twin One,organisation,,,\ntwo,Twin Two,organisation,,,\n'
        'solo,Twin Solo (independent),independent,,,\n', encoding='utf-8')
    registry = load_registry()
    assert registry.organisation_for_domain('twin.test') is None  # the first word names three organisations
    assert registry.organisation_for_domain('twinone.test') == 'one'


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
    ('plone.org', False), ('zope.org', False), ('lists.plone.org', False), ('svn.zope.org', False),
    ('localhost.localdomain', False), ('users.noreply.github.com', False), ('localhost', False),
    ('myhost.local', False), ('intranet', False), ('(none)', False), ('example.lan', False),
    ('1b3f2c4d-0000-4000-8000-123456789abc', False),
    ('icts.kuleuven.be', True), ('computer.org', False), ('acm.org', False), ('arcor.de', False),
    ('iki.fi', False), ('gnome.org', False), ('apache.org', False), ('bluedynamics.com', False),
])
def test_company_domain(domain, company):
    assert address_proposals.is_company_domain(domain) is company


class Person:
    def __init__(self, name, github=None):
        self.name, self.github = name, github


@pytest.mark.parametrize('domain,name,github,own', [
    ('hannosch.eu', 'Hanno Schlichting', None, True),  # a name part of four letters or more inside the label
    ('janedoe.net', 'Someone Else', 'janedoe', True),  # the login
    ('tom.net', 'Tom Comer', None, True),  # a whole name part
    ('foo.com.au', 'Tom Comer', None, False),  # `com` is no part of the name; only the label `foo` counts
    ('andersonleeb.com', 'Jane Leeb', None, True),
    ('mail.glicksoftware.com', 'David Glick', None, True),
    ('com.test', 'Tom Comer', None, False),
    ('ab.test', 'Abe Bee', None, False),  # a part shorter than four letters is no evidence in a longer label
])
def test_own_domain(domain, name, github, own):
    assert address_proposals.is_own_domain(domain, Person(name, github)) is own


def test_registrable_label():
    assert address_proposals.registrable_label('mail.foo.co.uk') == 'foo'
    assert address_proposals.registrable_label('foo.com.au') == 'foo'
    assert address_proposals.registrable_label('a.b.foo.de') == 'foo'
    assert address_proposals.registrable_label('foo.com') == 'foo'


def test_a_registered_organisation_wins_over_the_own_domain(setup):
    paths.ORGANISATIONS.write_text(paths.ORGANISATIONS.read_text(encoding='utf-8')
                                   + 'glick-software,Glick Software,organisation,,,\n', encoding='utf-8')
    paths.PEOPLE.write_text(paths.PEOPLE.read_text(encoding='utf-8')
                            + f'david-glick,David Glick,davisagli,{SOURCE}\n', encoding='utf-8')
    cache = setup / 'cache'
    make_clone(cache, 'r', [('David Glick', 'david@glicksoftware.com', 2011), ('Tom', 'x@foo.com.au', 2011)])
    text, _ = run(cache)
    assert '| david-glick | glick-software | 2011 | 1 | glicksoftware.com | name |' in text
    paths.ORGANISATIONS.write_text(paths.ORGANISATIONS.read_text(encoding='utf-8').replace(
        'glick-software,Glick Software,organisation,,,\n', ''), encoding='utf-8')
    text, _ = run(cache)
    assert 'glicksoftware.com' not in text  # unmapped and the person's own


def test_the_foo_and_andersonleeb_cases(setup):
    paths.PEOPLE.write_text(paths.PEOPLE.read_text(encoding='utf-8')
                            + f'tom-comer,Tom Comer,,{SOURCE}\njane-leeb,Jane Leeb,,{SOURCE}\n', encoding='utf-8')
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Tom Comer', 'tom@foo.com.au', 2011), ('Jane Leeb', 'jane@andersonleeb.com', 2011)])
    text, _ = run(cache)
    assert '| foo.com.au | 1 | 2011 | 1 |' in text  # reported as unmapped, not dropped silently
    assert 'andersonleeb.com' not in text


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
        ('Hanno Schlichting', 'hanno@widgets.test', 2018),  # alias
        ('Hanno Schlichting', 'hanno@mystery.test', 2018),  # unmapped
        ('Hanno Schlichting', 'hanno@mystery.test', 2019),
        ('Stranger', 'x@greenfinity.hu', 2016),  # nobody
        ('dependabot[bot]', '1+dependabot[bot]@users.noreply.github.com', 2016),
        # Imported from Subversion: the address was assigned by the migration, not used in 2008
        ('Hanno Schlichting', 'hanno@greenfinity.hu', 2008, 'Imported\n\nsvn path=/plone.app.x/trunk/; revision=1\n'),
    ])
    text, added = run(cache)
    sha = sha_of(work, 0)
    assert added == []
    assert (f'| hanno-schlichting | greenfinity | 2016-2017 | 3 | greenfinity.hu | name | '
            f'plone.app.x@{sha[:10]} |') in text
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
    assert '| mystery.test | 2 | 2018-2019 | 1 |' in text
    assert 'hannosch.eu' not in text and 'gmail' not in text and 'localhost' not in text


def test_a_rejected_year_is_not_proposed_again(setup):
    cache = setup / 'cache'
    make_clone(cache, 'plone.app.x', [('Hanno Schlichting', 'hanno@greenfinity.hu', 2016),
                                      ('Hanno Schlichting', 'hanno@greenfinity.hu', 2017)])
    paths.REJECTED_PROPOSALS.write_text(
        'person,organisation,from,to,reason,source\n'
        'hanno-schlichting,greenfinity,2016,2016,the year of a change,https://example.org/review\n', encoding='utf-8')
    text, _ = run(cache)
    assert '| hanno-schlichting | greenfinity | 2017 | 1 |' in text
    assert '2016' not in text.split('## Conflicts')[0]


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


def test_example_is_the_earliest_commit_and_each_run_has_its_own(setup):
    cache = setup / 'cache'
    # repository "a" sorts first, but its commit is later than the one in "b"
    work_a, _ = make_clone(cache, 'a', [('Jane Doe', 'jane@greenfinity.hu', '2015-09-01T00:00:00Z'),
                                        ('Jane Doe', 'jane@greenfinity.hu', '2017-03-01T00:00:00Z')])
    work_b, _ = make_clone(cache, 'b', [('Jane Doe', 'jane@greenfinity.hu', '2015-02-01T00:00:00Z')])
    text, _ = run(cache, write=True)
    rows = read_rows(paths.AFFILIATION_PROPOSALS)
    assert [(r['from'], r['to']) for r in rows] == [(2015, 2015), (2017, 2017)]
    assert rows[0]['evidence'].endswith(f'(example: https://github.com/plone/b/commit/{sha_of(work_b)})')
    assert rows[1]['evidence'].endswith(f'(example: https://github.com/plone/a/commit/{sha_of(work_a, 1)})')


def test_a_covered_block_of_several_years(setup):
    paths.AFFILIATIONS.write_text(
        'person,organisation,from,to,source,checked,notes\n'
        f'jane-doe,greenfinity,2015,2017,{SOURCE},,\n', encoding='utf-8')
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', y) for y in range(2014, 2020)])
    run(cache, write=True)
    assert [(r['from'], r['to']) for r in read_rows(paths.AFFILIATION_PROPOSALS)] == [(2014, 2014), (2018, 2019)]


def test_since(setup):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', y) for y in (2005, 2010)])
    text, _ = run(cache, since=2008)
    assert '| jane-doe | greenfinity | 2010 | 1 | greenfinity.hu | name |' in text
    assert '2005' not in text


def test_person_option(setup):
    cache = setup / 'cache'
    make_clone(cache, 'r', [('Jane Doe', 'jane@greenfinity.hu', 2015),
                            ('Hanno Schlichting', 'hanno@bubblenet.be', 2015),
                            ('Hanno Schlichting', 'hanno@mystery.test', 2015)])
    text, _ = run(cache, people=['hanno-schlichting'])
    assert 'bubblenet' in text and 'jane-doe' not in text and 'mystery.test' in text
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
