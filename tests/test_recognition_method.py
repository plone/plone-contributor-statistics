"""The recognition points follow community-recognition-points.csv (#56, #95)."""

import pytest

from scripts.report import generate_community_recognition_report as recognition
from scripts.derive import plip_organisation_stats as plips

PLIP_HEADER = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


@pytest.fixture
def data(tmp_path):
    """An empty data directory with a mapping: tisto is kitconcept from 2022, mamico RedTurtle."""
    write(tmp_path / 'organisations.csv', 'Organisation,Team\nkitconcept GmbH,tisto\nRedTurtle,mamico\n')
    write(tmp_path / 'overrides.csv', 'github_username,organisation,from_year,to_year,source\n'
                                      'tisto,Unmapped,2002,2021,test\n')
    write(tmp_path / 'plips.csv', PLIP_HEADER)
    # Every input the points need exists, but is empty
    for year in range(2020, 2026):
        write(tmp_path / 'data' / f'{year}-plone-organisation-contributors.csv',
              'organisation,total_commits,total_pull_requests\n')
    write(tmp_path / 'data' / 'community-contributions' / '2025-plone-conference.csv', 'Organisation\n')
    return tmp_path


def points(data, year=2025):
    org_points, _ = recognition.calculate_community_recognition_points(
        year=year, data_dir=str(data / 'data'), community_dir=str(data / 'data' / 'community-contributions'),
        plips_file=str(data / 'plips.csv'),
        organisations=str(data / 'organisations.csv'), overrides=str(data / 'overrides.csv'))
    return {org: dict(categories) for org, categories in org_points.items()}


def community(data, name, text):
    write(data / 'data' / 'community-contributions' / f'2025-{name}.csv', text)


def test_five_years_end_with_the_recognition_year():
    assert list(recognition.five_years(2025)) == [2021, 2022, 2023, 2024, 2025]


def test_strategic_sprint_points_are_split_and_given_once_per_year(data):
    community(data, 'sprints', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
                               'Beethoven Sprint,,,Bonn,Jakob Kahl,kitconcept GmbH;RedTurtle,strategic,https://plone.org,\n'
                               'Second Sprint,,,Bonn,Timo Stollenwerk,kitconcept GmbH,strategic,https://plone.org,\n'
                               'Community Sprint,,,Ferrara,Mauro,RedTurtle,community,https://plone.org,\n')
    result = points(data)
    assert result['kitconcept GmbH']['Strategic Sprint'] == 6
    assert result['RedTurtle']['Strategic Sprint'] == 6


def test_world_plone_day_event_points_are_split(data):
    community(data, 'world-plone-day-event', 'Date,Location,Format,Organisation,Source,Notes\n'
                                             '2025-04-10,Bologna,in person,RedTurtle;kitconcept GmbH,https://plone.org,\n')
    assert points(data)['RedTurtle']['WPD Event'] == 1.5


def test_only_world_plone_day_events_held_in_person_count(data):
    # Online editions are recorded, but only events held in person or hybrid get points (#118)
    community(data, 'world-plone-day-event', 'Date,Location,Format,Organisation,Source,Notes\n'
                                             '2025-04-10,Online,online,RedTurtle,https://plone.org,\n'
                                             '2025-04-10,Tokyo,hybrid,kitconcept GmbH,https://plone.org,\n')
    result = points(data)
    assert 'RedTurtle' not in result
    assert result['kitconcept GmbH']['WPD Event'] == 3


def test_a_training_gives_four_points_split_among_trainers(data):
    community(data, 'plone-conference-trainings', 'Title,Trainer(s),GitHub Handle(s),Organisation\n'
                                                  'Solo,Timo,tisto,kitconcept GmbH\n'
                                                  'Duo,Timo;Mauro,tisto;mamico,kitconcept GmbH;RedTurtle\n')
    result = points(data)
    assert result['kitconcept GmbH']['Training Session'] == 6
    assert result['RedTurtle']['Training Session'] == 2


def test_pull_requests_count_over_the_five_years_up_to_the_recognition_year(data):
    for year, prs in [(2020, 1000), (2021, 50), (2022, 50), (2023, 50), (2024, 50), (2025, 50)]:
        write(data / 'data' / f'{year}-plone-organisation-contributors.csv',
              f'organisation,total_commits,total_pull_requests\nRedTurtle,1,{prs}\n')
    # 50 PRs per year from 2021 to 2025; 2020 is outside the window
    assert points(data)['RedTurtle']['PR Contributions'] == 10


def test_plips_count_when_closed_in_the_five_years_for_the_organisation_of_that_year(data):
    rows = [f'{n},PLIP,tisto,closed,{year}-01-01,{year}-06-01,{year}-06-01,plone/volto,u\n'
            for n, year in enumerate([2019, 2021, 2022, 2023], 1)]
    rows.append('9,PLIP,tisto,open,2024-01-01,2024-01-02,,plone/volto,u\n')
    write(data / 'plips.csv', PLIP_HEADER + ''.join(rows))

    plip_data = recognition.load_plip_data(recognition.five_years(2025), str(data / 'plips.csv'),
                                           str(data / 'organisations.csv'), str(data / 'overrides.csv'))
    # 2019 is outside the window, 2021 is Unmapped by the override, the open PLIP doesn't count
    assert plip_data == {'kitconcept GmbH': {'closed_plips': 2}, 'Unmapped': {'closed_plips': 1}}


def test_plip_summary_maps_open_plips_by_the_year_they_were_created(data):
    write(data / 'plips.csv', PLIP_HEADER
          + '1,PLIP,tisto,open,2021-03-01,2021-03-02,,plone/volto,u\n'
          + '2,PLIP,tisto,closed,2020-01-01,2023-01-01,2023-01-01,plone/plone.restapi,u\n'
          + '3,PLIP,mamico,closed,2020-01-01,2020-02-01,2020-02-01,plone/volto,u\n')
    lookup = plips.organisation_lookup(str(data / 'organisations.csv'), str(data / 'overrides.csv'))
    rows = plips.summary_rows(plips.plips_by_organisation(plips.read_plips(str(data / 'plips.csv')), lookup))

    by_org = {row['organisation']: row for row in rows}
    assert by_org['Unmapped']['open_plips'] == 1
    assert by_org['kitconcept GmbH']['closed_plips'] == 1
    assert by_org['kitconcept GmbH']['repositories'] == 'plone/plone.restapi'
    assert by_org['RedTurtle']['total_plips'] == 1


def test_recognition_raises_without_community_year(data):
    # The community folder exists, but has no curated files for the year: a wrong path, not a quiet year
    (data / 'data' / 'community-contributions' / '2025-plone-conference.csv').unlink()
    with pytest.raises(FileNotFoundError, match='2025'):
        points(data)


def test_recognition_raises_without_community_folder(data):
    with pytest.raises(FileNotFoundError, match='missing'):
        recognition.calculate_community_recognition_points(
            year=2025, data_dir=str(data / 'data'), community_dir=str(data / 'missing'),
            plips_file=str(data / 'plips.csv'), organisations=str(data / 'organisations.csv'),
            overrides=str(data / 'overrides.csv'))


def test_recognition_raises_on_missing_organisation_year(tmp_path):
    with pytest.raises(FileNotFoundError, match='2023-plone-organisation-contributors.csv'):
        recognition.load_pr_data([2023], data_dir=str(tmp_path))


def test_recognition_raises_on_missing_plips_file(data):
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        recognition.load_plip_data([2025], str(data / 'missing.csv'),
                                   str(data / 'organisations.csv'), str(data / 'overrides.csv'))


def test_recognition_raises_on_missing_levels_file(tmp_path):
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        recognition.load_recognition_levels(tmp_path / 'missing.csv')


def test_recognition_warns_on_one_missing_kind(data, capsys):
    # Some kinds of community data didn't exist in every year: one missing kind is a warning
    community(data, 'plone-conference', 'Organisation\nRedTurtle\n')
    points(data)
    assert '2025-podcasts.csv not found' in capsys.readouterr().out


LEVELS = [
    {'name': 'Bronze', 'min_points': 3, 'max_points': 9, 'description': ''},
    {'name': 'Silver', 'min_points': 10, 'max_points': float('inf'), 'description': ''},
]


@pytest.mark.parametrize('points, level', [(0, 'No Level'), (2.5, 'No Level'), (3, 'Bronze'), (9, 'Bronze'),
                                           (9.5, 'Bronze'), (10, 'Silver'), (1000, 'Silver')])
def test_a_level_applies_from_its_minimum(points, level):
    # Points can be fractions (split among organisers); 9.5 hasn't reached Silver yet
    assert recognition.get_recognition_level(points, LEVELS) == level


def test_levels_file_has_no_gaps():
    from pathlib import Path
    from scripts.lib import paths
    levels = recognition.load_recognition_levels(Path(__file__).resolve().parent.parent / paths.RECOGNITION_LEVELS)
    for lower, upper in zip(levels, levels[1:]):
        assert upper['min_points'] == lower['max_points'] + 1, (lower['name'], upper['name'])
    assert levels[-1]['max_points'] == float('inf')


def contributions(data, year=2025):
    found = {}
    recognition.calculate_community_recognition_points(
        year=year, data_dir=str(data / 'data'), community_dir=str(data / 'data' / 'community-contributions'),
        plips_file=str(data / 'plips.csv'), organisations=str(data / 'organisations.csv'),
        overrides=str(data / 'overrides.csv'), contributions=found)
    return found


def test_contributions_carry_file_line_and_source(data):
    # The community page links every point to its row and public record
    community(data, 'sprints', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
                               'Beethoven Sprint,,,Bonn,Jakob Kahl,RedTurtle,strategic,https://example.org/sprint,\n')
    [sprint] = contributions(data)['RedTurtle']['Strategic Sprint']
    assert sprint.points == 12
    assert sprint.file.endswith('2025-sprints.csv')
    assert sprint.line == 2
    assert sprint.source == 'https://example.org/sprint'
    assert sprint.text == 'Beethoven Sprint'


def test_wpd_talk_source_is_the_video(data):
    community(data, 'world-plone-day-talks', 'Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID\n'
                                             'A talk,Mauro,RedTurtle,Online,Talk,abc\n')
    [talk] = contributions(data)['RedTurtle']['WPD Talk']
    assert talk.source == 'https://www.youtube.com/watch?v=abc'


def test_contributions_match_points(data):
    community(data, 'sprints', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
                               'Beethoven Sprint,,,Bonn,Jakob Kahl,kitconcept GmbH;RedTurtle,strategic,https://s,\n')
    community(data, 'team-leaders', 'Name,Team,Organisation,Source\n'
                                    'Timo,Volto Team,kitconcept GmbH,https://a\nMauro,Volto Team,RedTurtle,https://b\n')
    for year, prs in [(2021, 150), (2022, 150), (2023, 150), (2024, 150), (2025, 150)]:
        write(data / 'data' / f'{year}-plone-organisation-contributors.csv',
              f'organisation,total_commits,total_pull_requests\nRedTurtle,1,{prs}\n')
    found = contributions(data)
    for org, categories in points(data).items():
        for category, value in categories.items():
            assert sum(c.points for c in found[org][category]) == pytest.approx(value), (org, category)
