"""The recognition points follow community-recognition-points.csv (#56, #95)."""

import pytest

import generate_community_recognition_report as recognition
import plip_organisation_stats as plips

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
    (tmp_path / 'data' / 'community-contributions').mkdir(parents=True)
    return tmp_path


def points(data, year=2025):
    org_points, _ = recognition.calculate_community_recognition_points(
        year=year, data_dir=str(data / 'data'), plips_file=str(data / 'plips.csv'),
        organisations=str(data / 'organisations.csv'), overrides=str(data / 'overrides.csv'))
    return {org: dict(categories) for org, categories in org_points.items()}


def community(data, name, text):
    write(data / 'data' / 'community-contributions' / f'2025-{name}.csv', text)


def test_five_years_end_with_the_recognition_year():
    assert list(recognition.five_years(2025)) == [2021, 2022, 2023, 2024, 2025]


def test_strategic_sprint_points_are_split_and_given_once_per_year(data):
    community(data, 'strategic-sprints', 'Sprint,Organiser/Host,Organisation\n'
                                         'Beethoven Sprint,Jakob Kahl,kitconcept GmbH;RedTurtle\n'
                                         'Second Sprint,Timo Stollenwerk,kitconcept GmbH\n')
    result = points(data)
    assert result['kitconcept GmbH']['Strategic Sprint'] == 6
    assert result['RedTurtle']['Strategic Sprint'] == 6


def test_world_plone_day_event_points_are_split(data):
    community(data, 'world-plone-day-event', 'Organisation,Reference\nRedTurtle;kitconcept GmbH,https://plone.org\n')
    assert points(data)['RedTurtle']['WPD Event'] == 1.5


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
