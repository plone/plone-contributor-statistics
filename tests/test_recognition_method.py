"""The recognition points follow community-recognition-points.csv (#56, #95), read through the model (#139)."""

import pytest

from scripts.lib import paths
from scripts.report import generate_community_recognition_report as recognition
from scripts.derive import plip_organisation_stats as plips
from tests.conftest import community_event, community_rows

PLIP_HEADER = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'
CONFERENCE = 'plone-conference-2025'
WPD_ONLINE = 'wpd-2025-online'

# timo is kitconcept from 2022 (Unmapped before), the others belong to one organisation; nobody to none
PEOPLE = [('timo', 'tisto'), ('mauro', 'mamico'), ('philip', ''), ('fred', ''), ('kim', ''), ('astrid', ''),
          ('karel', ''), ('nobody', '')]
AFFILIATIONS = [('timo', 'kitconcept', 2022, ''), ('mauro', 'redturtle', 2000, ''), ('philip', 'starzel', 2000, ''),
                ('fred', 'kitconcept', 2000, ''), ('kim', 'sixfeetup', 2000, ''), ('astrid', 'juizi', 2000, ''),
                ('karel', 'juizi', 2000, '')]
ORGANISATIONS = [('kitconcept', 'kitconcept GmbH'), ('redturtle', 'RedTurtle'), ('starzel', 'Starzel'),
                 ('sixfeetup', 'Sixfeetup'), ('juizi', 'Juizi')]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


@pytest.fixture
def data(write_registers, tmp_repo):
    """An empty data directory with the registers above."""
    write_registers(PEOPLE, AFFILIATIONS, ORGANISATIONS)
    write(tmp_repo / 'plips.csv', PLIP_HEADER)
    # Every input the points need exists, but is empty
    for year in range(2020, 2026):
        write(tmp_repo / 'data' / f'{year}-plone-organisation-contributors.csv',
              'organisation,total_commits,total_pull_requests\n')
    # The conference of the recognition year, without organisers yet
    community_event(CONFERENCE, 'conference', 2025, cited_as='', name='Plone Conference 2025')
    community_event(WPD_ONLINE, 'wpd', 2025, cited_as='', name='World Plone Day 2025, Online', location='Online',
                    format='online')
    return tmp_repo


def points(data, year=2025):
    org_points, _ = recognition.calculate_community_recognition_points(
        year=year, data_dir=str(data / 'data'), community_dir=paths.COMMUNITY, plips_file=str(data / 'plips.csv'))
    return {org: dict(categories) for org, categories in org_points.items()}


def sprint(name, organisers=(), organisations=(), level='', cited_as='https://plone.org'):
    community_event(name.lower().replace(' ', '-'), 'sprint', 2025, organisers, organisations, cited_as=cited_as,
                    name=name, level=level)


def wpd_event(location, fmt, organisations=(), cited_as='https://plone.org'):
    community_event(f'wpd-2025-04-10-{location.lower()}', 'wpd', 2025, organisations=organisations,
                    cited_as=cited_as, start='2025-04-10', location=location, format=fmt)


def wpd_talk(title, speakers='', organisations='', kind='Talk', cited_as='https://a', event=WPD_ONLINE):
    community_rows('talks', {'event': event, 'type': kind, 'title': title, 'speakers': speakers,
                             'organisations': organisations, 'cited_as': cited_as})


def training(title, trainers):
    community_rows('trainings', {'event': CONFERENCE, 'title': title, 'trainers': trainers, 'cited_as': 'https://t'})


def organiser(person='', organisation='', cited_as='https://c'):
    community_rows('organisers', {'event': CONFERENCE, 'person': person, 'organisation': organisation,
                                  'cited_as': cited_as})


def role(kind, cited_as, **cells):
    community_rows(kind, {'year': 2025, 'cited_as': cited_as, **cells})


def test_five_years_end_with_the_recognition_year():
    assert list(recognition.five_years(2025)) == [2021, 2022, 2023, 2024, 2025]


def test_strategic_sprint_points_are_split_and_given_once_per_year(data):
    sprint('Beethoven Sprint', ('jakob',), ('kitconcept', 'redturtle'), 'strategic')
    sprint('Second Sprint', ('timo',), ('kitconcept',), 'strategic')
    sprint('Community Sprint', ('mauro',), ('redturtle',), 'community')
    result = points(data)
    assert result['kitconcept GmbH']['Strategic Sprint'] == 6
    assert result['RedTurtle']['Strategic Sprint'] == 6


def test_world_plone_day_event_points_are_split(data):
    wpd_event('Bologna', 'in person', ('redturtle', 'kitconcept'))
    assert points(data)['RedTurtle']['WPD Event'] == 1.5


def test_only_world_plone_day_events_held_in_person_count(data):
    # Online editions are recorded, but only events held in person or hybrid get points (#118)
    wpd_event('Online', 'online', ('redturtle',))
    wpd_event('Tokyo', 'hybrid', ('kitconcept',))
    result = points(data)
    assert 'RedTurtle' not in result
    assert result['kitconcept GmbH']['WPD Event'] == 3


def test_a_training_gives_four_points_split_among_trainers(data):
    training('Solo', 'timo')
    training('Duo', 'timo;mauro')
    result = points(data)
    assert result['kitconcept GmbH']['Training Session'] == 6
    assert result['RedTurtle']['Training Session'] == 2


def test_a_trainer_without_an_organisation_keeps_the_share_out_of_the_points(data):
    # nobody has no affiliation in 2025: the share is Unmapped and dropped, the other share stays at 4 / 2
    training('Duo', 'timo;nobody')
    assert points(data) == {'kitconcept GmbH': {'Training Session': 2}}
    assert recognition.UNMAPPED not in contributions(data)


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

    plip_data = recognition.load_plip_data(recognition.five_years(2025), str(data / 'plips.csv'))
    # 2019 is outside the window, 2021 is before the affiliation (Unmapped), the open PLIP doesn't count
    assert plip_data == {'kitconcept GmbH': {'closed_plips': 2}, 'Unmapped': {'closed_plips': 1}}


def test_plip_summary_maps_open_plips_by_the_year_they_were_created(data):
    write(data / 'plips.csv', PLIP_HEADER
          + '1,PLIP,tisto,open,2021-03-01,2021-03-02,,plone/volto,u\n'
          + '2,PLIP,tisto,closed,2020-01-01,2023-01-01,2023-01-01,plone/plone.restapi,u\n'
          + '3,PLIP,mamico,closed,2020-01-01,2020-02-01,2020-02-01,plone/volto,u\n')
    lookup = plips.organisation_lookup()
    rows = plips.summary_rows(plips.plips_by_organisation(plips.read_plips(str(data / 'plips.csv')), lookup))

    by_org = {row['organisation']: row for row in rows}
    assert by_org['Unmapped']['open_plips'] == 1
    assert by_org['kitconcept GmbH']['closed_plips'] == 1
    assert by_org['kitconcept GmbH']['repositories'] == 'plone/plone.restapi'
    assert by_org['RedTurtle']['total_plips'] == 1


def test_recognition_raises_without_community_year(data):
    # The community folder exists, but has no rows for the year: a wrong year, not a quiet one
    with pytest.raises(FileNotFoundError, match='2026'):
        points(data, year=2026)


def test_recognition_raises_without_community_folder(data):
    with pytest.raises(FileNotFoundError, match='missing'):
        recognition.calculate_community_recognition_points(
            year=2025, data_dir=str(data / 'data'), community_dir=str(data / 'missing'),
            plips_file=str(data / 'plips.csv'))


def test_recognition_raises_on_missing_organisation_year(tmp_path):
    with pytest.raises(FileNotFoundError, match='2023-plone-organisation-contributors.csv'):
        recognition.load_pr_data([2023], data_dir=str(tmp_path))


def test_recognition_raises_on_missing_plips_file(data):
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        recognition.load_plip_data([2025], str(data / 'missing.csv'))


def test_recognition_raises_on_missing_levels_file(tmp_path):
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        recognition.load_recognition_levels(tmp_path / 'missing.csv')


def test_recognition_warns_on_one_missing_kind(data, capsys):
    # Some kinds of community data didn't exist in every year: one missing kind is a warning
    organiser(organisation='redturtle')
    points(data)
    out = capsys.readouterr().out
    assert 'no podcasts rows for 2025' in out and 'plone-conference rows' not in out


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
    levels = recognition.load_recognition_levels(Path(__file__).resolve().parent.parent / paths.RECOGNITION_LEVELS)
    for lower, upper in zip(levels, levels[1:]):
        assert upper['min_points'] == lower['max_points'] + 1, (lower['name'], upper['name'])
    assert levels[-1]['max_points'] == float('inf')


def contributions(data, year=2025):
    found = {}
    recognition.calculate_community_recognition_points(
        year=year, data_dir=str(data / 'data'), community_dir=paths.COMMUNITY, plips_file=str(data / 'plips.csv'),
        contributions=found)
    return found


def test_contributions_carry_file_line_and_source(data):
    # The community page links every point to its row and public record
    sprint('Beethoven Sprint', ('jakob',), ('redturtle',), 'strategic', cited_as='report: https://example.org/sprint')
    [found] = contributions(data)['RedTurtle']['Strategic Sprint']
    assert found.points == 12
    assert found.file == 'curated/community/events.csv'
    assert found.line == 4  # after the conference and the online World Plone Day
    assert found.source == 'report: https://example.org/sprint'
    assert found.text == 'Beethoven Sprint'


def test_people_are_shown_by_their_name_in_the_register(data):
    paths.PEOPLE.write_text('id,name,github,source\ntimo,Timo Stollenwerk,tisto,https://r\n', encoding='utf-8')
    role('release-managers', 'https://rm', person='timo')
    role('board-of-directors', 'https://b', person='timo', role='voting')
    role('team-leaders', 'https://t', person='timo', team='Volto Team')
    found = contributions(data)['kitconcept GmbH']
    assert [(c.text, c.points, c.source) for c in found['Release Manager']] == [('Timo Stollenwerk', 12, 'https://rm')]
    assert [(c.text, c.points) for c in found['Board Member']] == [('Timo Stollenwerk', 6)]
    assert [(c.text, c.points) for c in found['Team Leader']] == [('Timo Stollenwerk (Volto Team)', 6)]


def test_pull_request_points_link_the_row_of_each_year(data):
    # The points add up five yearly files; each year's row is linked, not a summary
    for year in range(2021, 2026):
        other = 'kitconcept GmbH,9,90\n' if year == 2023 else ''
        write(data / 'data' / f'{year}-plone-organisation-contributors.csv',
              f'organisation,total_commits,total_pull_requests\n{other}RedTurtle,1,150\n')
    [prs] = contributions(data)['RedTurtle']['PR Contributions']
    folder = str(data / 'data')
    assert prs.rows == tuple((str(year), f'{folder}/{year}-plone-organisation-contributors.csv',
                              3 if year == 2023 else 2) for year in range(2021, 2026))


def test_wpd_talk_source_is_the_video(data):
    wpd_talk('A talk', 'mauro', cited_as='https://www.youtube.com/watch?v=abc')
    [talk] = contributions(data)['RedTurtle']['WPD Talk']
    assert talk.source == 'https://www.youtube.com/watch?v=abc'
    assert talk.text == 'A talk'


def test_a_talk_counts_once_per_organisation(data):
    # Two speakers can share one organisation, and the organisations set can name it again
    wpd_talk('A talk', 'astrid;karel', 'juizi')
    wpd_talk('Another', 'astrid;mauro', cited_as='https://b')
    result = points(data)
    assert result['Juizi']['WPD Talk'] == 2
    assert result['RedTurtle']['WPD Talk'] == 1


def test_a_talk_by_a_company_team_counts_for_the_company(data):
    wpd_talk('Team talk', organisations='juizi')
    assert points(data) == {'Juizi': {'WPD Talk': 1}}


def test_talks_count_at_most_four_per_organisation(data):
    for n in range(6):
        wpd_talk(f'Talk {n}', 'mauro;nobody', cited_as=f'https://{n}')
    assert points(data) == {'RedTurtle': {'WPD Talk': 4}}
    # The first four talks in the order of the file count
    assert [c.text for c in contributions(data)['RedTurtle']['WPD Talk']] == ['Talk 0', 'Talk 1', 'Talk 2', 'Talk 3']


def test_contributions_match_points(data):
    sprint('Beethoven Sprint', ('jakob',), ('kitconcept', 'redturtle'), 'strategic', cited_as='https://s')
    role('team-leaders', 'https://a', person='timo', team='Volto Team')
    role('team-leaders', 'https://b', person='mauro', team='Volto Team')
    for year, prs in [(2021, 150), (2022, 150), (2023, 150), (2024, 150), (2025, 150)]:
        write(data / 'data' / f'{year}-plone-organisation-contributors.csv',
              f'organisation,total_commits,total_pull_requests\nRedTurtle,1,{prs}\n')
    found = contributions(data)
    result = points(data)
    assert result['kitconcept GmbH']['Team Leader'] == result['RedTurtle']['Team Leader'] == 3
    for org, categories in result.items():
        for category, value in categories.items():
            assert sum(c.points for c in found[org][category]) == pytest.approx(value), (org, category)


def test_only_world_plone_day_talks_count_as_talks(data):
    # Streams, openings and podcast episodes are not talks (#119)
    wpd_talk('A talk', 'mauro')
    wpd_talk('Newsroom', 'philip', kind='Newsroom', cited_as='https://b')
    wpd_talk('Stream', organisations='redturtle', kind='Full stream', cited_as='https://c')
    result = points(data)
    assert result['RedTurtle']['WPD Talk'] == 1
    assert 'Starzel' not in result


def test_a_podcast_counts_with_five_episodes_split_among_its_hosts(data):
    role('podcasts', 'https://n', series='The Plone Newsroom', person='philip', episodes=5)
    role('podcasts', 'https://n', series='The Plone Newsroom', person='fred', episodes=5)
    role('podcasts', 'https://p', series='The Plone Podcast', person='kim', episodes=4)
    role('podcasts', 'https://a', series='Plone Ask Me Anything', person='astrid', episodes=8)
    result = points(data)
    assert result['Starzel']['Podcast Host'] == 3
    assert result['Juizi']['Podcast Host'] == 6
    assert 'Sixfeetup' not in result  # four episodes are not enough


def test_a_podcast_row_without_a_host_is_no_host(data):
    role('podcasts', 'https://n', series='The Plone Newsroom', person='philip', episodes=5)
    role('podcasts', 'https://n', series='The Plone Newsroom', episodes=5)
    [host] = contributions(data)['Starzel']['Podcast Host']
    assert (host.text, host.points) == ('philip (The Plone Newsroom)', 6)


def test_conference_points_are_split_among_the_rows_with_an_organisation(data):
    organiser(organisation='redturtle')
    organiser(person='mauro')
    organiser(person='timo')
    organiser(organisation='kitconcept')
    result = points(data)
    assert result['RedTurtle']['Conference Organization'] == 12
    assert result['kitconcept GmbH']['Conference Organization'] == 12


def test_conference_organisers_are_no_point_source(data):
    # An organiser role counts on the community page, not for the points
    organiser(person='mauro')
    sprint('Sprint', ('mauro',), level='strategic', cited_as='https://s')
    assert points(data) == {}


def test_a_role_names_the_person_by_the_display_name(data):
    from types import SimpleNamespace
    from scripts.lib.model import load_registry

    registry = load_registry()
    row = SimpleNamespace(file='curated/community/team-leaders.csv', line=2)
    assert recognition._name(registry, 'timo', row) == 'timo'
    # The checks refuse an unknown id; if one gets through, the report does not invent a name for it
    with pytest.raises(KeyError, match='team-leaders.csv:2.*ghost'):
        recognition._name(registry, 'ghost', row)
