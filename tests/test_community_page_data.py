"""The data of the community page (design: archive/specs-and-plans/2026-10-19-community-page-design.md)."""

import json

import pytest

from scripts.derive import community_page
from scripts.lib import paths
from scripts.report import generate_community_recognition_report as recognition

CONTRIBUTORS = 'username,total_commits,total_pull_requests\n'
ORGANISATIONS = 'organisation,total_commits,total_pull_requests,contributors_count\n'
PLIPS = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'
LEVELS = ('Level,Min Points,Max Points,Description\nBronze Contributor,1,9,\nSilver Contributor,10,24,\n'
          'Gold Contributor,25,,\n')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


@pytest.fixture
def repo(tmp_repo):
    """A small repository: data for 2021-2025, nothing before."""
    recognition.load_organisation_names.cache_clear()
    write(paths.ORGANISATIONS, 'Organisation,Team\nJane Doe (independent),janedoe\nkitconcept GmbH,tisto\n'
                               'RedTurtle,mamico\n')
    write(paths.OVERRIDES, 'github_username,organisation,from_year,to_year,source\n')
    write(paths.FULLNAMES, 'github username,fullname\n')
    write(paths.RECOGNITION_LEVELS, LEVELS)
    write(paths.PLIPS_DETAILED, PLIPS)
    for year in range(2021, 2026):
        write(paths.contributors_file(year), CONTRIBUTORS)
        write(paths.organisation_contributors_file(year), ORGANISATIONS)
    write(paths.COMMUNITY / '2025-plone-conference.csv', 'Organisation\nRedTurtle\n')
    yield tmp_repo
    recognition.load_organisation_names.cache_clear()


def test_people_active_counts_code_and_community_once(repo):
    # Review focus: a login counts once, from code work and from a handle
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\nmamico,3,1\n')
    write(paths.COMMUNITY / '2025-release-managers.csv',
          'Name,Github,Organisation,Source\nTimo Stollenwerk,tisto,kitconcept GmbH,https://a\n')
    write(paths.COMMUNITY / '2025-board-of-directors.csv',
          'Name,Organisation,Source,Role\nAnna Board,Unmapped,https://b,voting\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['people'] == 3  # tisto, mamico, Anna Board


def test_organisations_active_leave_out_unmapped_and_independents(repo):
    write(paths.organisation_contributors_file(2025), ORGANISATIONS + 'kitconcept GmbH,10,5,1\nUnmapped,4,2,3\n'
                                                                      'Jane Doe (independent),1,1,1\n')
    data = community_page.build_page_data(2025)
    # kitconcept from code, RedTurtle from organising the conference
    assert data['headline']['year']['organisations'] == 2


def test_events_count_one_world_plone_day_per_year(repo):
    write(paths.COMMUNITY / '2025-world-plone-day-event.csv',
          'Organisation,Reference\nRedTurtle,https://w\nkitconcept GmbH,https://w\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['events'] == 2  # the conference and one World Plone Day


def test_wall_lists_every_organisation_with_a_level(repo):
    # Review focus: independents earn levels too and are shown
    write(paths.COMMUNITY / '2025-team-leaders.csv',
          'Name,Team,Organisation,Source\nJane Doe,Docs Team,Jane Doe (independent),https://c\n')
    data = community_page.build_page_data(2025)
    on_wall = {o['name'] for group in data['wall'] for o in group['organisations']}
    assert on_wall == {'RedTurtle', 'Jane Doe (independent)'}
    assert [group['level'] for group in data['wall']] == ['Silver Contributor', 'Bronze Contributor']


def test_points_to_next_level_with_fractions(repo):
    # Review focus: 9.5 points are Bronze, with 0.5 to Silver
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv',
          'Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID\n'
          + ''.join(f'Talk {n},Mauro,RedTurtle,Online,Talk,v{n}\n' for n in range(4)))
    write(paths.COMMUNITY / '2025-world-plone-day-event.csv',
          'Organisation,Reference\nRedTurtle;kitconcept GmbH,https://w\n')
    write(paths.COMMUNITY / '2025-plone-conference.csv', 'Organisation\n')  # no conference points
    write(paths.COMMUNITY / '2025-team-leaders.csv',
          'Name,Team,Organisation,Source\nMauro,Volto Team,RedTurtle,https://t\n')
    organisation = community_page.build_page_data(2025)['organisations']['redturtle']
    assert organisation['points'] == 11.5  # 4 talks + 1.5 WPD event + 6 team lead
    assert organisation['level'] == 'Silver Contributor'
    assert organisation['next_level'] == 'Gold Contributor'
    assert organisation['points_to_next'] == 13.5


def test_contributions_link_their_rows(repo):
    redturtle = community_page.build_page_data(2025)['organisations']['redturtle']
    [contribution] = redturtle['categories']['Conference Organization']['contributions']
    assert contribution['file'] == 'curated/community-contributions/2025-plone-conference.csv'
    assert contribution['line'] == 2
    assert contribution['source'] is None


def test_history_pull_requests_none_before_pull_requests(repo):
    # Review focus: years without pull requests show none, not 0
    write(paths.contributors_file(2005), CONTRIBUTORS + 'limi,100,0\n')
    write(paths.organisation_contributors_file(2005), ORGANISATIONS)
    history = community_page.build_page_data(2025)['history']
    assert history['2005']['commits'] == 100
    assert history['2005']['pull_requests'] is None


def test_people_are_sorted_by_id_and_carry_no_rank(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'zed,1,1\nalice,5,9\n')
    people = community_page.build_page_data(2025)['people']['2025']
    assert [p['id'] for p in people] == ['alice', 'zed']
    assert set(people[0]) == {'id', 'commits', 'pull_requests', 'roles'}


def test_data_is_deterministic(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\n')
    first = json.dumps(community_page.build_page_data(2025), sort_keys=True)
    assert json.dumps(community_page.build_page_data(2025), sort_keys=True) == first


def test_organisation_without_a_person_counts_as_active(repo):
    # A talk with an organisation but no speaker still counts for the organisation
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv',
          'Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID\nA talk,,kitconcept GmbH,Online,Talk,v1\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['organisations'] == 2  # RedTurtle (conference) and kitconcept (talk)
    assert data['organisations']['kitconcept-gmbh']['history']['2025']['roles'] == 1


def test_organisations_in_person_columns_are_not_people(repo):
    write(paths.ORGANISATIONS, 'Organisation,Team\nJuizi,\nkitconcept GmbH,tisto\nPloneGov-BR,\nRedTurtle,mamico\n'
                               'UNAM,\n')
    write(paths.COMMUNITY / '2025-sprints.csv', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
          'Sprint A,,,X,PloneGov-BR,PloneGov-BR,strategic,https://a,\n'
          'Sprint B,,,X,Mathematics Institute at UNAM,UNAM,strategic,https://b,\n'
          'Sprint C,,,X,Alex (Juizi),Juizi,community,https://c,\n')
    ids = [p['id'] for p in community_page.build_page_data(2025)['people']['2025']]
    assert ids == ['name:alex (juizi)']


def test_unmapped_is_not_listed_as_an_event_organiser(repo):
    write(paths.COMMUNITY / '2025-plone-conference.csv', 'Organisation\nUnmapped\nRedTurtle\n')
    [conference] = community_page.build_page_data(2025)['history']['2025']['events']
    assert conference['organisations'] == ['RedTurtle']


def test_equal_contributions_are_merged(repo):
    write(paths.COMMUNITY / '2025-plone-conference-trainings.csv',
          'Title,Trainer(s),GitHub Handle(s),Organisation,Source\n'
          'Volto,Timo;Rob,tisto;robgietema,kitconcept GmbH;kitconcept GmbH,https://t\n')
    [training] = community_page.build_page_data(2025)['organisations']['kitconcept-gmbh']['categories'][
        'Training Session']['contributions']
    assert training['points'] == 4


def test_commit_author_named_like_an_organisation_is_skipped(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'RedTurtle Team,3,0\nalice,1,1\n')
    assert [p['id'] for p in community_page.build_page_data(2025)['people']['2025']] == ['alice']
