"""The migration from the mapping files and the old community files to the registers (#139).

A miniature old structure is migrated once per module; each test checks one fact of the result.
"""

import csv
import shutil
from pathlib import Path

import pytest

from scripts.lib import paths
from scripts.tools import check, datapackage
from scripts.tools import migrate_data_structure as migrate

REPO = Path(__file__).resolve().parent.parent

OLD_FILES = {
    paths.ORGANISATIONS: (
        'Organisation,Team\n'
        'Starzel,pbauer\n'
        'Thomas Schorr (independent),tschorr\n'
        'Zest Software,\n'
    ),
    paths.OVERRIDES: (
        'github_username,organisation,from_year,to_year,source\n'
        'pbauer,Unmapped,2002,2009,the organisation before 2010 is not documented (#70)\n'
        'tschorr,Zest Software,2005,2012,https://example.org/tschorr-at-zest\n'
    ),
    paths.SOURCES: (
        'github_username,organisation,source,checked\n'
        'pbauer,Starzel,https://example.org/pbauer-at-starzel,2026-10-18\n'
        'tschorr,Thomas Schorr (independent),https://example.org/tschorr-independent,2026-10-18\n'
    ),
    paths.PROPOSALS: (
        'contributor,organisation,from_year,to_year,evidence\n'
        'tschorr,Starzel,2014,2014,Company address in commits 2014 (example: https://example.org/commit)\n'
    ),
    paths.FULLNAMES: (
        'github username,fullname,source\n'
        'pbauer,Phil Bauer,"GitHub profile name ""Philip Bauer"", login pbauer: https://github.com/pbauer"\n'
        'pbauer,Philip Bauer,GitHub profile name: https://github.com/pbauer\n'
    ),
    paths.COMMIT_AUTHORS: (
        'email,github_username,name,source\n'
        'alan@example.org,,Alan Runyan,Review in #69; example commit: https://example.org/commit/1\n'
        'Tom@Example.org,tschorr,Tom Schorr,Same name in commits; example commit: https://example.org/commit/2\n'
    ),
    paths.ACCOUNT_ALIASES: 'alias,github_username,source\n',
    paths.CHANGELOG_NAMES: 'changelog_name,github_username,name,source\n',
    paths.BOT_ACCOUNTS: 'login,reason\n',
    paths.EXCLUDED_REPOSITORIES: 'repository,reason\n',
    paths.COMMUNITY / '2006-board-of-directors.csv': (
        'Name,Organisation,Source,Role\n'
        'Philip Bauer;Thomas Schorr,Zest Software;Zest Software,https://example.org/board-2006; '
        'organisation of Philip Bauer from the Board page of the year: https://example.org/board-page,voting\n'
    ),
    paths.COMMUNITY / '2016-plone-conference-trainings.csv': (
        'Title,Trainer(s),GitHub Handle(s),Organisation,Source,Notes\n'
        'Mastering Plone,Philip Bauer;Thomas Schorr,pbauer;tschorr,Starzel;Thomas Schorr (independent),'
        'https://example.org/training-2016; organisation of Thomas Schorr from the organisation mapping: '
        'https://example.org/tschorr,Two-day class\n'
    ),
    paths.COMMUNITY / '2023-sprints.csv': (
        'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
        'Alpine Sprint,2023-02-06,2023-02-10,Innsbruck,Philip Bauer; Thomas Schorr; Alan Runyan,'
        'Starzel;Zest Software,strategic,https://example.org/sprint-2023,\n'
    ),
    paths.contributors_file(2005): (
        'username,total_commits,total_pull_requests,repositories_count,repositories,first_contribution,'
        'last_contribution\n'
        'tschorr,5,0,2,"Plone, plone.app.layout",2005-01-02,2005-11-30\n'
        'Alan Runyan,3,0,1,Plone,2005-03-01,2005-04-01\n'
    ),
    paths.checkpoint_file('2005-plone-contributors'): (
        'username,total_commits\n'
        'Alan Runyan,3\n'
    ),
    paths.changelog_entries_file(2005): (
        'username,changelog_entries,repositories_count,repositories,changelog_names,matched_by\n'
        'Alan Runyan,2,1,Plone,Alan Runyan,commit_authors\n'
    ),
}
PROFILE_NAMES = 'login,name,fetched\ntschorr,Thomas Schorr,2026-10-19\n'


def rows(root, path):
    with open(root / path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def migrated(tmp_path_factory):
    """(root, report) of the miniature old structure after the migration and the data package."""
    root = tmp_path_factory.mktemp('repo')
    shutil.copytree(REPO / 'curated/schemas', root / 'curated/schemas')
    for path, text in OLD_FILES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding='utf-8')
    profile_names = root / 'profile_names.csv'
    profile_names.write_text(PROFILE_NAMES, encoding='utf-8')
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(root)
        report = migrate.migrate(root=root, until=2026, profile_names=profile_names)
        datapackage.main([])
        yield root, report


def test_people_get_slug_ids_and_names(migrated):
    root, _ = migrated
    people = {row['id']: row for row in rows(root, paths.PEOPLE)}
    assert people['philip-bauer']['github'] == 'pbauer'
    assert people['philip-bauer']['name'] == 'Philip Bauer'
    assert people['alan-runyan']['github'] == ''
    assert people['thomas-schorr']['github'] == 'tschorr'


def test_second_spelling_becomes_identity(migrated):
    root, _ = migrated
    identities = {(row['person'], row['kind'], row['value']) for row in rows(root, paths.IDENTITIES)}
    assert ('philip-bauer', 'name', 'Phil Bauer') in identities
    assert ('thomas-schorr', 'email', 'tom@example.org') in identities


def test_affiliations_have_no_default_and_no_unmapped(migrated):
    root, _ = migrated
    affiliations = rows(root, paths.AFFILIATIONS)
    philip = [row for row in affiliations if row['person'] == 'philip-bauer']
    assert [(row['organisation'], row['from'], row['to']) for row in philip] == [('starzel', '2010', '')]
    assert 'unmapped' not in {row['organisation'] for row in affiliations}
    assert 'not verified' in philip[0]['notes']
    assert philip[0]['checked'] == '2026-10-18'


def test_override_becomes_dated_range(migrated):
    root, _ = migrated
    thomas = [(row['organisation'], row['from'], row['to'], row['source'], row['checked'])
              for row in rows(root, paths.AFFILIATIONS) if row['person'] == 'thomas-schorr']
    assert thomas == [
        ('thomas-schorr-independent', '2002', '2004', 'https://example.org/tschorr-independent', '2026-10-18'),
        ('zest-software', '2005', '2012', 'https://example.org/tschorr-at-zest', ''),
        ('thomas-schorr-independent', '2013', '', 'https://example.org/tschorr-independent', '2026-10-18'),
    ]


def test_trainings_row_keeps_one_row_with_a_set(migrated):
    root, _ = migrated
    trainings = rows(root, paths.COMMUNITY / '2016-plone-conference-trainings.csv')
    assert [row['trainers'] for row in trainings] == ['philip-bauer;thomas-schorr']
    assert list(trainings[0]) == ['title', 'trainers', 'source', 'notes']


def test_board_row_is_split_and_conflict_goes_to_proposals(migrated):
    root, _ = migrated
    board = rows(root, paths.COMMUNITY / '2006-board-of-directors.csv')
    assert [(row['person'], row['role']) for row in board] == [('philip-bauer', 'voting'),
                                                               ('thomas-schorr', 'voting')]
    proposals = [row for row in rows(root, paths.AFFILIATION_PROPOSALS) if row['from'] == '2006']
    assert [(row['person'], row['organisation'], row['to']) for row in proposals] == [
        ('philip-bauer', 'zest-software', '2006')]
    assert '2006-board-of-directors.csv:2' in proposals[0]['evidence']


def test_old_proposals_are_carried_over(migrated):
    root, _ = migrated
    proposals = [(row['person'], row['organisation'], row['from'], row['to'])
                 for row in rows(root, paths.AFFILIATION_PROPOSALS)]
    assert ('thomas-schorr', 'starzel', '2014', '2014') in proposals


def test_sprint_sets_are_ids(migrated):
    root, _ = migrated
    [sprint] = rows(root, paths.COMMUNITY / '2023-sprints.csv')
    assert sprint['organisers'] == 'philip-bauer;thomas-schorr;alan-runyan'
    assert sprint['organisations'] == 'starzel;zest-software'


def test_source_cell_is_cut_at_mapping_note(migrated):
    root, report = migrated
    trainings = rows(root, paths.COMMUNITY / '2016-plone-conference-trainings.csv')
    assert trainings[0]['source'] == 'https://example.org/training-2016'
    assert any('organisation of Thomas Schorr from the organisation mapping' in cut
               for _, _, cut in report.cut_sources)


def test_no_login_username_is_renamed_in_collected(migrated):
    root, _ = migrated
    usernames = [row['username'] for row in rows(root, paths.contributors_file(2005))]
    assert usernames == ['tschorr', 'person:alan-runyan']
    assert rows(root, paths.changelog_entries_file(2005))[0]['username'] == 'person:alan-runyan'
    assert (root / paths.checkpoint_file('2005-plone-contributors')).read_text().endswith('Alan Runyan,3\n')


def test_collected_files_keep_their_other_bytes(migrated):
    root, _ = migrated
    text = (root / paths.contributors_file(2005)).read_text(encoding='utf-8')
    assert text == OLD_FILES[paths.contributors_file(2005)].replace('\nAlan Runyan,', '\nperson:alan-runyan,')


def test_old_files_are_removed(migrated):
    root, _ = migrated
    for path in (paths.OVERRIDES, paths.SOURCES, paths.PROPOSALS, paths.COMMIT_AUTHORS, paths.ACCOUNT_ALIASES,
                 paths.FULLNAMES, paths.CHANGELOG_NAMES):
        assert not (root / path).exists(), path
    assert (root / paths.ORGANISATIONS).read_text(encoding='utf-8').startswith('id,name,kind,aliases,notes\n')


def test_plone_foundation_is_added(migrated):
    root, _ = migrated
    organisations = {row['id']: row for row in rows(root, paths.ORGANISATIONS)}
    assert organisations['plone-foundation']['kind'] == 'foundation'
    assert organisations['thomas-schorr-independent']['kind'] == 'independent'


def test_aliases_without_organisation_are_dropped(migrated):
    _, report = migrated
    assert ('vangheem', 'Vangheem') in {(alias, target) for alias, target, _ in report.dropped_aliases}


def test_output_validates(migrated):
    root, _ = migrated
    assert check.validate(root) == []


def test_report_renders_counts_first(migrated):
    _, report = migrated
    text = migrate.write_report(report)
    assert text.splitlines()[0].startswith('# ')
    assert '| people | 3 |' in text
