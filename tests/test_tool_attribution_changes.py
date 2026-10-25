"""The list of the person-years whose organisation differs between a base commit and the working tree."""

import shutil
import subprocess

import pytest

from scripts.lib import paths
from scripts.lib.model import load_registry
from scripts.tools import attribution_changes
from tests.conftest import REPO, community_rows

CONTRIBUTORS = 'username,total_commits,total_pull_requests,repositories_count,repositories,first_contribution,' \
               'last_contribution\n'
CHANGELOG = 'username,changelog_entries,repositories_count,repositories,changelog_names,matched_by\n'
PLIPS = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'
ORGANISATIONS = [('zest', 'Zest Software'), ('beta', 'Beta')]
BASE_ROWS = [('jane-doe', 'zest', 2010, 2011), ('jane-doe', 'zest', 2014, 2015)]  # 2012-2013 are bridged


def git(*args):
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', '-c', 'commit.gpgsign=false',
                    *args], check=True, capture_output=True)


def contributors(year, *rows):
    paths.contributors_file(year).write_text(CONTRIBUTORS + ''.join(
        f'{login},{commits},{pulls},1,plone.app.example,{year}-01-01,{year}-12-31\n' for login, commits, pulls in rows),
        encoding='utf-8')


@pytest.fixture
def base(tmp_repo, write_registers):
    """A git repository with the code of the checkout and the base registers committed; returns the commit."""
    shutil.copytree(REPO / 'scripts', tmp_repo / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    write_registers(people=[('jane-doe', 'janedoe')], affiliations=BASE_ROWS, organisations=ORGANISATIONS)
    contributors(2010, ('janedoe', 5, 0))
    contributors(2012, ('janedoe', 3, 1))
    git('init', '-q')
    git('add', '-A')
    git('commit', '-qm', 'base')
    return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()


def test_a_changed_year_is_listed_and_an_inactive_one_hidden(base, write_registers):
    # A record of Beta in 2012 breaks the bridge: 2012 counts for Beta, 2013 is open
    write_registers(people=[('jane-doe', 'janedoe')], affiliations=[*BASE_ROWS, ('jane-doe', 'beta', 2012, 2012)],
                    organisations=ORGANISATIONS)
    rows, active, inactive = attribution_changes.compute(base, until=2016)
    assert rows == [{'person': 'jane-doe', 'year': 2012, 'before': 'Zest Software', 'after': 'Beta',
                     'rule': 'one organisation', 'activity': '3 commits, 1 pull request'}]
    assert (active, inactive) == (1, 1)  # 2010 is active but unchanged; 2013 changed but inactive
    rows, _, _ = attribution_changes.compute(base, until=2016, all_years=True)
    assert [(row['year'], row['before'], row['after'], row['rule'], row['activity']) for row in rows] == [
        (2012, 'Zest Software', 'Beta', 'one organisation', '3 commits, 1 pull request'),
        (2013, 'Zest Software', 'Unmapped', 'unmapped', '')]


def test_no_change_lists_nothing(base, capsys):
    assert attribution_changes.compute(base, until=2016) == ([], 0, 0)
    assert attribution_changes.main(['--base', base]) == 0
    assert capsys.readouterr().out == f'Compared with {base}: 0 active person-years count for another organisation, ' \
                                      '0 inactive ones.\n'


def test_a_removed_row_is_compared(base, write_registers):
    # The years of the rows at the base are compared even when no row covers them now
    write_registers(people=[('jane-doe', 'janedoe')], affiliations=BASE_ROWS[1:], organisations=ORGANISATIONS)
    rows, _, _ = attribution_changes.compute(base, until=2016, all_years=True)
    assert [(row['year'], row['before'], row['after']) for row in rows] == [
        (2010, 'Zest Software', 'Unmapped'), (2011, 'Zest Software', 'Unmapped'),
        (2012, 'Zest Software', 'Unmapped'), (2013, 'Zest Software', 'Unmapped')]


def test_the_counting_before_runs_the_code_of_the_base(tmp_repo, base):
    # The counting after is that of the code under test. A base whose model spells every organisation in
    # capitals: the counting before is that of the base's code
    registers = tmp_repo / 'scripts/lib/model/registers.py'
    text = registers.read_text(encoding='utf-8')
    spelled = 'return self.organisations[org_id].name\n'
    assert spelled in text
    registers.write_text(text.replace(spelled, 'return self.organisations[org_id].name.upper()\n'), encoding='utf-8')
    git('commit', '-qam', 'capitals')
    capitals = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    rows, _, _ = attribution_changes.compute(capitals, until=2016)
    assert [(row['year'], row['before'], row['after']) for row in rows] == [
        (2010, 'ZEST SOFTWARE', 'Zest Software'), (2012, 'ZEST SOFTWARE', 'Zest Software')]


def test_the_activity_of_a_year(tmp_repo, write_registers):
    write_registers(people=[('jane-doe', 'janedoe'), ('joe', '')], organisations=ORGANISATIONS)
    contributors(2015, ('janedoe', 2, 0), ('person:joe', 0, 0), ('someone-else', 4, 0))
    paths.changelog_entries_file(2015).write_text(
        CHANGELOG + 'janedoe,3,1,plone.app.example,janedoe,login\n'
        'joe,7,1,plone.app.example,joe,unmatched\n', encoding='utf-8')  # an unmatched name is no login
    paths.PLIPS_DETAILED.parent.mkdir(parents=True, exist_ok=True)
    paths.PLIPS_DETAILED.write_text(PLIPS + '1,PLIP: one,janedoe,closed,2014-05-01,2015-02-01,2015-02-01,'
                                    'plone/Products.CMFPlone,https://example.org/1\n', encoding='utf-8')
    community_rows('board-of-directors', {'year': 2016, 'person': 'joe', 'role': 'Member'})
    credited = attribution_changes.activity(load_registry())
    assert credited == {('jane-doe', 2015): {'commits': 2, 'changelog entries': 3, 'PLIPs': 1},
                        ('joe', 2016): {'Board': 1}}
    assert attribution_changes.describe(credited[('jane-doe', 2015)]) == '2 commits, 3 changelog entries, 1 PLIP'


def test_the_tables(capsys):
    rows = [{'person': 'jane-doe', 'year': 2012, 'before': 'Unmapped', 'after': 'Zest Software', 'rule': 'bridged',
             'activity': 'Speaker'},
            {'person': 'jo', 'year': 2013, 'before': 'Unmapped', 'after': 'Zest Software', 'rule': 'bridged',
             'activity': ''}]
    assert attribution_changes.text_table(rows).splitlines() == [
        'person    year  before    after          rule now  activity',
        'jane-doe  2012  Unmapped  Zest Software  bridged   Speaker',
        'jo        2013  Unmapped  Zest Software  bridged   inactive']
    assert attribution_changes.markdown_table(rows).splitlines()[:3] == [
        '| person | year | before | after | rule now | activity |', '|---|---|---|---|---|---|',
        '| jane-doe | 2012 | Unmapped | Zest Software | bridged | Speaker |']


def test_a_bridge_to_an_assumed_row_is_listed(tmp_repo, write_registers):
    # At the base a fill row covers 2012-2013 up to an assumed row; without it, assumed rows bridge nothing
    shutil.copytree(REPO / 'scripts', tmp_repo / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))

    def registers(rows):
        write_registers(people=[('jane-doe', 'janedoe')], affiliations=rows, organisations=ORGANISATIONS)
        text = paths.AFFILIATIONS.read_text(encoding='utf-8')
        paths.AFFILIATIONS.write_text(text.replace(',2014,2015,stated,', ',2014,2015,assumed,'), encoding='utf-8')

    registers([*BASE_ROWS, ('jane-doe', 'zest', 2012, 2013)])
    contributors(2012, ('janedoe', 3, 0))
    git('init', '-q')
    git('add', '-A')
    git('commit', '-qm', 'base')
    registers(BASE_ROWS)
    rows, active, inactive = attribution_changes.compute('HEAD', until=2016)
    assert [(row['year'], row['before'], row['after'], row['rule']) for row in rows] == [
        (2012, 'Zest Software', 'Unmapped', 'unmapped')]
    assert (active, inactive) == (1, 1)
