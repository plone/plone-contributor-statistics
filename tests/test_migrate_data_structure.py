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
from scripts.tools.migrate_data import legacy_mappings as old

REPO = Path(__file__).resolve().parent.parent

OLD_FILES = {
    paths.ORGANISATIONS: (
        'Organisation,Team\n'
        'Starzel,pbauer\n'
        'Thomas Schorr (independent),tschorr\n'
        'Zest Software,\n'
    ),
    old.OVERRIDES: (
        'github_username,organisation,from_year,to_year,source\n'
        'pbauer,Unmapped,2002,2009,the organisation before 2010 is not documented (#70)\n'
        'tschorr,Zest Software,2005,2012,https://example.org/tschorr-at-zest\n'
    ),
    old.SOURCES: (
        'github_username,organisation,source,checked\n'
        'pbauer,Starzel,https://example.org/pbauer-at-starzel,2026-10-18\n'
        'tschorr,Thomas Schorr (independent),https://example.org/tschorr-independent,2026-10-18\n'
    ),
    old.PROPOSALS: (
        'contributor,organisation,from_year,to_year,evidence\n'
        'tschorr,Starzel,2014,2014,Company address in commits 2014 (example: https://example.org/commit)\n'
        'tschorr,Acme Labs,2015,2015,Company address @acme in commits 2015 (example: https://example.org/acme)\n'
    ),
    old.FULLNAMES: (
        'github username,fullname,source\n'
        'pbauer,Phil Bauer,"GitHub profile name ""Philip Bauer"", login pbauer: https://github.com/pbauer"\n'
        'pbauer,Philip Bauer,GitHub profile name: https://github.com/pbauer\n'
    ),
    old.COMMIT_AUTHORS: (
        'email,github_username,name,source\n'
        'alan@example.org,,Alan Runyan,Review in #69; example commit: https://example.org/commit/1\n'
        'Tom@Example.org,tschorr,Tom Schorr,Same name in commits; example commit: https://example.org/commit/2\n'
        'anne@example.org,,Anne Marie Doe,Review in #69; example commit: https://example.org/commit/3\n'
    ),
    old.ACCOUNT_ALIASES: 'alias,github_username,source\n',
    old.CHANGELOG_NAMES: 'changelog_name,github_username,name,source\n',
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
    paths.COMMUNITY / '2019-plone-conference-trainings.csv': (
        'Title,Trainer(s),GitHub Handle(s),Organisation,Source,Notes\n'
        # Only Philip's cell is a copy; Thomas's states an organisation the mapping does not give for 2019
        'Advanced Plone,Philip Bauer;Thomas Schorr,pbauer;tschorr,Starzel;Zest Software,'
        'https://example.org/training-2019; organisation of Philip Bauer from the organisation mapping: '
        'https://example.org/pb,\n'
        # One handle for two trainers: the handles are not used
        'Plone Basics,Philip Bauer;Thomas Schorr,pbauer,Starzel;Thomas Schorr (independent),'
        'https://example.org/basics-2019,\n'
    ),
    paths.COMMUNITY / '2020-release-managers.csv': (
        'Name,Github,Organisation,Source\n'
        'Thomas Schorr,tschorr,Starzel,https://example.org/release-2020; '
        'organisation of Thomas Schorr from the release page: https://example.org/rm-page\n'
        'Anne-Marie Doe,,Unmapped,https://example.org/release-2020\n'
    ),
    paths.COMMUNITY / '2021-podcasts.csv': (
        'Series,Host,Organisation,Episodes,Source\n'
        'Plone Talks,Alan Runyan,Zest Software,2,episodes: https://example.org/ep1; '
        'organisation: staff page: https://example.org/staff\n'
        'Plone Talks,,Starzel,1,episodes: https://example.org/ep2\n'
    ),
    paths.COMMUNITY / '2024-team-leaders.csv': (
        'Name,Team,Organisation,Source\n'
        'Philip Bauer;Thomas Schorr;Alan Runyan,Release Team,Zest Software;Starzel,https://example.org/team-2024\n'
    ),
    paths.COMMUNITY / '2024-world-plone-day-talks.csv': (
        'Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID,Source,Notes\n'
        'Starzel Demo,Starzel team,Starzel,Online,Talk,abc111,https://www.youtube.com/watch?v=abc111,\n'
        'Plone Talk,Philip Bauer,Starzel,Munich,Talk,abc222,'
        'https://www.youtube.com/watch?v=abc222; Philip Bauer: https://github.com/pbauer,\n'
        'No Source Talk,Thomas Schorr,,Online,Talk,abc333,,\n'
    ),
    paths.COMMUNITY / '2003-plone-conference.csv': (
        'Organisation,Organiser(s),Source,Notes\n'
        'Unmapped,Alan Runyan,https://example.org/conference-2003,No company named\n'
    ),
    paths.COMMUNITY / '2022-sprints.csv': (
        'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
        # The Board record comes after the note on Philip's organisation and must stay
        'Note Sprint,2022-03-01,2022-03-02,Bonn,Philip Bauer,Starzel,strategic,'
        'https://a; organisation of Philip Bauer from the organisation mapping: https://b; Board: https://c,\n'
        # A note with two links: the bare second link belongs to the note
        'Stray Sprint,2022-04-01,2022-04-02,Bonn,Philip Bauer,Starzel,strategic,'
        'https://a2; organisation of Philip Bauer from the organisation mapping: https://b2; https://b3; '
        'Board: https://c2,\n'
    ),
    paths.COMMUNITY / '2023-sprints.csv': (
        'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
        'Alpine Sprint,2023-02-06,2023-02-10,Innsbruck,Philip Bauer; Thomas Schorr; Alan Runyan,'
        'Starzel;Zest Software,strategic,https://example.org/sprint-2023; '
        'organisation of Philip Bauer from the organisation mapping: https://example.org/pb-sprint,\n'
        'Bonn Sprint,2023-05-01,2023-05-02,Bonn,Bonn Sprint Team,Starzel,community,https://example.org/bonn,\n'
    ),
    paths.contributors_file(2006): (
        'username,total_commits\r\n'
        'tschorr,"1"\r\n'
        'Alan Runyan,2\r\n'
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


def build(root, changes=None):
    """Write the miniature old structure under root, with `changes` ({path: text}) on top; the profile names."""
    shutil.copytree(REPO / 'curated/schemas', root / 'curated/schemas')
    for path, text in {**OLD_FILES, **(changes or {})}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        with open(root / path, 'w', newline='', encoding='utf-8') as f:
            f.write(text)
    profile_names = root / 'profile_names.csv'
    profile_names.write_text(PROFILE_NAMES, encoding='utf-8')
    return profile_names


@pytest.fixture(scope='module')
def migrated(tmp_path_factory):
    """(root, report) of the miniature old structure after the migration and the data package."""
    root = tmp_path_factory.mktemp('repo')
    profile_names = build(root)
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(root)
        report = migrate.migrate(root=root, until=2026, profile_names=profile_names)
        datapackage.main([])
        yield root, report


def proposals_of(root, file):
    """(person, organisation, from, to) of the proposals whose evidence names the file."""
    return {(row['person'], row['organisation'], row['from'], row['to'])
            for row in rows(root, paths.AFFILIATION_PROPOSALS) if f'{file}:' in row['evidence']}


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
    sprint = rows(root, paths.COMMUNITY / '2023-sprints.csv')[0]
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
    for path in (old.OVERRIDES, old.SOURCES, old.PROPOSALS, old.COMMIT_AUTHORS, old.ACCOUNT_ALIASES,
                 old.FULLNAMES, old.CHANGELOG_NAMES):
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
    assert '| people | 5 |' in text


def test_team_speaker_becomes_organisation_of_talk(migrated):
    root, _ = migrated
    talk = rows(root, paths.COMMUNITY / '2024-world-plone-day-talks.csv')[0]
    assert (talk['speakers'], talk['organisations']) == ('', 'starzel')


def test_talk_source_is_cut_at_speaker_link(migrated):
    root, report = migrated
    talk = rows(root, paths.COMMUNITY / '2024-world-plone-day-talks.csv')[1]
    assert talk['source'] == 'https://www.youtube.com/watch?v=abc222'
    assert ('curated/community-contributions/2024-world-plone-day-talks.csv', 3,
            '; Philip Bauer: https://github.com/pbauer') in report.cut_sources


def test_talk_without_source_takes_its_video(migrated):
    root, _ = migrated
    talk = rows(root, paths.COMMUNITY / '2024-world-plone-day-talks.csv')[2]
    assert talk['source'] == 'https://www.youtube.com/watch?v=abc333'


def test_talk_location_comes_from_event_column(migrated):
    root, _ = migrated
    talks = rows(root, paths.COMMUNITY / '2024-world-plone-day-talks.csv')
    assert [talk['location'] for talk in talks] == ['Online', 'Munich', 'Online']


def test_unaligned_row_is_reported(migrated):
    _, report = migrated
    assert [(file, line) for file, line, _, _ in report.unaligned] == [
        ('curated/community-contributions/2024-team-leaders.csv', 2)]


def test_unaligned_row_gives_proposals_for_each_person(migrated):
    root, _ = migrated
    assert proposals_of(root, '2024-team-leaders.csv') == {
        ('philip-bauer', 'zest-software', '2024', '2024'),
        ('thomas-schorr', 'zest-software', '2024', '2024'),
        ('thomas-schorr', 'starzel', '2024', '2024'),
        ('alan-runyan', 'zest-software', '2024', '2024'),
        ('alan-runyan', 'starzel', '2024', '2024'),
    }


def test_organisation_differing_from_mapping_is_proposed(migrated):
    root, _ = migrated
    assert proposals_of(root, '2020-release-managers.csv') == {('thomas-schorr', 'starzel', '2020', '2020')}


def test_proposal_evidence_is_the_persons_record(migrated):
    root, _ = migrated
    [evidence] = [row['evidence'] for row in rows(root, paths.AFFILIATION_PROPOSALS)
                  if '2020-release-managers.csv' in row['evidence']]
    assert evidence == 'curated/community-contributions/2020-release-managers.csv:2; https://example.org/rm-page'


def test_organisation_of_person_without_login_is_proposed(migrated):
    root, _ = migrated
    assert proposals_of(root, '2021-podcasts.csv') == {('alan-runyan', 'zest-software', '2021', '2021')}


def test_copy_note_covers_only_the_person_it_names(migrated):
    root, _ = migrated
    assert proposals_of(root, '2019-plone-conference-trainings.csv') == {('thomas-schorr', 'zest-software', '2019',
                                                                          '2019')}


def test_copy_that_disagrees_with_mapping_stops_the_run(tmp_path):
    board = ('Name,Organisation,Source,Role\nThomas Schorr,Starzel,https://example.org/board-2010; '
             'organisation from the organisation mapping: https://example.org/x,voting\n')
    profile_names = build(tmp_path, {paths.COMMUNITY / '2010-board-of-directors.csv': board})
    with pytest.raises(ValueError, match='marked as copied'):
        migrate.migrate(root=tmp_path, until=2026, profile_names=profile_names)


def test_unknown_organisation_stops_the_run(tmp_path):
    sprints = ('Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
               'Some Sprint,2023-01-01,2023-01-02,Bonn,,Nowhere Ltd,community,https://example.org/s,\n')
    profile_names = build(tmp_path, {paths.COMMUNITY / '2023-sprints.csv': sprints})
    with pytest.raises(ValueError, match='Nowhere Ltd'):
        migrate.migrate(root=tmp_path, until=2026, profile_names=profile_names)


def test_group_in_sprint_is_dropped_and_reported(migrated):
    root, report = migrated
    assert rows(root, paths.COMMUNITY / '2023-sprints.csv')[1]['organisers'] == ''
    assert ('curated/community-contributions/2023-sprints.csv', 3, 'Bonn Sprint Team') in report.dropped_groups


def test_event_source_is_cut_too(migrated):
    root, _ = migrated
    assert rows(root, paths.COMMUNITY / '2023-sprints.csv')[0]['source'] == 'https://example.org/sprint-2023'


def test_source_segments_after_a_note_are_kept(migrated):
    root, report = migrated
    assert rows(root, paths.COMMUNITY / '2022-sprints.csv')[0]['source'] == 'https://a; Board: https://c'
    assert ('curated/community-contributions/2022-sprints.csv', 2,
            '; organisation of Philip Bauer from the organisation mapping: https://b') in report.cut_sources


def test_bare_link_after_a_note_is_cut_with_it(migrated):
    root, report = migrated
    assert rows(root, paths.COMMUNITY / '2022-sprints.csv')[1]['source'] == 'https://a2; Board: https://c2'
    cut = '; organisation of Philip Bauer from the organisation mapping: https://b2; https://b3'
    assert ('curated/community-contributions/2022-sprints.csv', 3, cut) in report.cut_sources


def test_source_is_cut_at_bare_organisation_note(migrated):
    root, _ = migrated
    assert rows(root, paths.COMMUNITY / '2021-podcasts.csv')[0]['source'] == 'episodes: https://example.org/ep1'


def test_conference_without_host_keeps_its_organisers(migrated):
    root, _ = migrated
    [conference] = rows(root, paths.COMMUNITY / '2003-plone-conference.csv')
    assert (conference['organisation'], conference['organisers'], conference['notes']) == (
        '', 'alan-runyan', 'No company named')


def test_podcast_without_host_keeps_its_row(migrated):
    root, _ = migrated
    podcast = rows(root, paths.COMMUNITY / '2021-podcasts.csv')[1]
    assert (podcast['person'], podcast['episodes'], podcast['notes']) == (
        '', '1', 'organisation in the old file: Starzel')


def test_proposal_may_introduce_an_organisation(migrated):
    root, report = migrated
    organisations = {row['id']: row['name'] for row in rows(root, paths.ORGANISATIONS)}
    assert organisations['acme-labs'] == 'Acme Labs'
    assert [(name, 'https://example.org/acme' in reason) for name, reason in report.added_organisations] == [
        ('Acme Labs', True)]


def test_id_collisions_are_reported(migrated):
    _, report = migrated
    assert report.id_collisions == [('anne-marie-doe', 'anne-marie-doe;anne-marie-doe-2', ';')]


def test_handles_not_one_per_name_are_reported(migrated):
    _, report = migrated
    assert report.dropped_handles == [
        ('curated/community-contributions/2019-plone-conference-trainings.csv', 3, 'Philip Bauer;Thomas Schorr',
         'pbauer')]


def test_crlf_collected_file_keeps_its_line_endings(migrated):
    root, _ = migrated
    assert (root / paths.contributors_file(2006)).read_bytes() == (
        b'username,total_commits\r\ntschorr,"1"\r\nperson:alan-runyan,2\r\n')


def test_migration_is_deterministic(tmp_path):
    outputs = []
    for name in ('a', 'b'):
        root = tmp_path / name
        migrate.migrate(root=root, until=2026, profile_names=build(root))
        outputs.append({path.relative_to(root): path.read_bytes() for path in sorted(root.rglob('*'))
                        if path.is_file()})
    assert outputs[0] == outputs[1]
