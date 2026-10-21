"""The data of the community page (design: archive/specs-and-plans/2026-10-19-community-page-design.md)."""

import json

import pytest

from scripts.derive import community_page
from scripts.lib import paths
from scripts.lib.model import events, load_registry, roles

CONTRIBUTORS = 'username,total_commits,total_pull_requests\n'
CONF_TALKS = 'event,scope,type,title,speakers,organisations,video,source,notes\n'
ORGANISATIONS = 'organisation,total_commits,total_pull_requests,contributors_count\n'
PLIPS = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'
LEVELS = ('Level,Min Points,Max Points,Description\nBronze Contributor,1,9,\nSilver Contributor,10,24,\n'
          'Gold Contributor,25,,\n')
SPRINTS = 'sprint,start,end,location,organisers,organisations,level,source,notes\n'
WPD_EVENTS = 'date,location,format,organisations,organisers,source,notes\n'
TALKS = 'title,speakers,organisations,type,location,source,notes\n'
TRAININGS = 'title,trainers,source,notes\n'
CONFERENCE = 'organisation,organisers,source,notes\n'
TEAM_LEADERS = 'person,team,source,notes\n'
RELEASE_MANAGERS = 'person,source,notes\n'
BOARD = 'person,role,source,notes\n'

# timo (login tisto) is kitconcept, mauro (mamico) RedTurtle, jane an independent; anna has no organisation
PEOPLE = [('timo', 'tisto'), ('mauro', 'mamico'), ('robert', 'robgietema'), ('anna', ''), ('jane', '')]
AFFILIATIONS = [('timo', 'kitconcept', 2000, ''), ('mauro', 'redturtle', 2000, ''),
                ('robert', 'kitconcept', 2000, ''), ('jane', 'jane', 2000, '')]
REGISTER_ORGANISATIONS = [('kitconcept', 'kitconcept GmbH'), ('redturtle', 'RedTurtle')]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


@pytest.fixture
def repo(write_registers, tmp_repo):
    """A small repository: data for 2021-2025, nothing before."""
    write_registers(PEOPLE, AFFILIATIONS, REGISTER_ORGANISATIONS)
    # An independent person is an organisation row of the register that the page does not count
    with open(paths.ORGANISATIONS, 'a', encoding='utf-8') as f:
        f.write('jane,Jane (independent),independent,,\n')
    write(paths.RECOGNITION_LEVELS, LEVELS)
    write(paths.PLIPS_DETAILED, PLIPS)
    for year in range(2021, 2026):
        write(paths.contributors_file(year), CONTRIBUTORS)
        write(paths.organisation_contributors_file(year), ORGANISATIONS)
    write(paths.COMMUNITY / '2025-plone-conference.csv', CONFERENCE + 'redturtle,,https://a,\n')
    return tmp_repo


def test_people_active_counts_code_and_community_once(repo):
    # Review focus: a person counts once, from code work and from a role
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\nmamico,3,1\n')
    write(paths.COMMUNITY / '2025-release-managers.csv', RELEASE_MANAGERS + 'timo,https://a,\n')
    write(paths.COMMUNITY / '2025-board-of-directors.csv', BOARD + 'anna,voting,https://b,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['people'] == 3  # timo, mauro, anna


def test_people_active_counts_a_person_once_across_code_and_roles(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'Tisto,10,5\n')
    write(paths.COMMUNITY / '2025-release-managers.csv', RELEASE_MANAGERS + 'timo,https://a,\n')
    [entry] = community_page.build_page_data(2025)['people']['2025']
    assert entry == {'id': 'timo', 'name': 'timo', 'commits': 10, 'pull_requests': 5, 'roles': ['Release manager'],
                     'talks': [], 'organisation': 'kitconcept GmbH'}


def test_a_login_outside_the_register_is_keyed_by_the_login(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'Zed,1,1\nperson:anna,2,0\n')
    people = community_page.build_page_data(2025)['people']['2025']
    assert [(p['id'], p['name']) for p in people] == [('anna', 'anna'), ('zed', 'zed')]


def test_organisations_active_leave_out_unmapped_and_independents(repo):
    write(paths.organisation_contributors_file(2025), ORGANISATIONS + 'kitconcept GmbH,10,5,1\nUnmapped,4,2,3\n'
                                                                      'Jane (independent),1,1,1\n')
    data = community_page.build_page_data(2025)
    # kitconcept from code, RedTurtle from organising the conference
    assert data['headline']['year']['organisations'] == 2


def test_events_count_each_local_world_plone_day(repo):
    write(paths.COMMUNITY / '2025-world-plone-day-event.csv', WPD_EVENTS
          + '2025-04-10,Bologna,in person,redturtle,,https://w,\n2025-04-10,Brasilia,in person,,,https://w,\n'
          + '2025-04-10,Online,online,kitconcept,,https://w,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['events'] == 3  # the conference and two local World Plone Days held in person


def test_wall_lists_every_organisation_with_a_level(repo):
    # Review focus: independents earn levels too and are shown
    write(paths.COMMUNITY / '2025-team-leaders.csv', TEAM_LEADERS + 'jane,Docs Team,https://c,\n')
    data = community_page.build_page_data(2025)
    on_wall = {o['name'] for group in data['wall'] for o in group['organisations']}
    assert on_wall == {'RedTurtle', 'Jane (independent)'}
    assert [group['level'] for group in data['wall']] == ['Silver Contributor', 'Bronze Contributor']


def test_points_to_next_level_with_fractions(repo):
    # Review focus: 9.5 points are Bronze, with 0.5 to Silver
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv', TALKS
          + ''.join(f'Talk {n},mauro,,Talk,Online,https://t{n},\n' for n in range(4)))
    write(paths.COMMUNITY / '2025-world-plone-day-event.csv', WPD_EVENTS
          + '2025-04-10,Bologna,in person,redturtle;kitconcept,,https://w,\n')
    write(paths.COMMUNITY / '2025-plone-conference.csv', CONFERENCE)  # no conference points
    write(paths.COMMUNITY / '2025-team-leaders.csv', TEAM_LEADERS + 'mauro,Volto Team,https://t,\n')
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
    assert contribution['source'] == 'https://a'


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
    assert set(people[0]) == {'id', 'name', 'commits', 'pull_requests', 'roles', 'talks', 'organisation'}


def test_data_is_deterministic(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\n')
    first = json.dumps(community_page.build_page_data(2025), sort_keys=True)
    assert json.dumps(community_page.build_page_data(2025), sort_keys=True) == first


def test_organisation_of_a_speaker_counts_as_active(repo):
    # A speaker makes the organisation they belonged to that year active, whatever the organisations column says
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv', TALKS + 'A talk,timo,,Talk,Online,https://t,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['organisations'] == 2  # RedTurtle (conference) and kitconcept (the speaker)
    assert data['history']['2025']['people_active'] == 1


def test_organisation_only_talk_counts_the_organisation(repo):
    # A company team gave the talk: no speakers, but the organisation is active and gets a role credit
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv', TALKS + 'A talk,,kitconcept,Talk,Online,https://t,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['organisations'] == 2  # RedTurtle (conference) and kitconcept (the talk)
    assert data['organisations']['kitconcept-gmbh']['history']['2025']['roles'] == 1


def test_a_second_login_is_keyed_to_the_same_person(repo):
    write(paths.IDENTITIES, 'person,kind,value,source\ntimo,login,tisto-work,https://r\n')
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\nTisto-Work,1,1\n')
    [entry] = community_page.build_page_data(2025)['people']['2025']
    assert (entry['id'], entry['commits'], entry['pull_requests']) == ('timo', 11, 6)


def test_a_speaker_is_active_and_lists_the_talks_sorted(repo):
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Tagung 2025,regional,Talk,Zope news,timo,,,https://s/1,\n'
          'Plone Conference 2025,global,Keynote,A keynote,timo;mauro,,https://v/1,https://s/2,\n')
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv', TALKS + 'WPD talk,timo,,Talk,Online,https://v/3,\n')
    data = community_page.build_page_data(2025)
    timo = next(p for p in data['people']['2025'] if p['id'] == 'timo')
    assert timo['roles'] == ['Speaker']
    assert timo['talks'] == [{'title': 'A keynote', 'event': 'Plone Conference 2025', 'video': 'https://v/1'},
                             {'title': 'Zope news', 'event': 'Plone Tagung 2025', 'video': None},
                             {'title': 'WPD talk', 'event': 'World Plone Day 2025', 'video': 'https://v/3'}]
    mauro = next(p for p in data['people']['2025'] if p['id'] == 'mauro')
    assert mauro['talks'] == [{'title': 'A keynote', 'event': 'Plone Conference 2025', 'video': 'https://v/1'}]
    assert data['history']['2025']['people_active'] == 2
    assert data['headline']['year']['organisations'] == 2  # RedTurtle (conference, mauro) and kitconcept (timo)


def test_people_without_talks_have_an_empty_list(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\n')
    [entry] = community_page.build_page_data(2025)['people']['2025']
    assert entry['talks'] == []


def test_a_team_conference_talk_counts_the_organisation(repo):
    # No points, so kitconcept has no entry under data['organisations']; the history function shows the role count
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Conference 2025,global,Talk,Team talk,,kitconcept,,https://s/1,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['organisations'] == 2
    assert data['history']['2025']['people_active'] == 0
    registry = load_registry()
    history = community_page.organisation_history(2025, registry, roles(2025), events(2025))
    assert history['kitconcept GmbH']['roles'] == 1


def test_conference_talks_earn_no_points(repo):
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Conference 2025,global,Keynote,A keynote,timo,,https://v/1,https://s/2,\n')
    data = community_page.build_page_data(2025)
    assert 'kitconcept-gmbh' not in data['organisations']


def test_people_names_find_a_registered_person_by_login(repo):
    write(paths.IDENTITIES, 'person,kind,value,source\ntimo,login,tisto-work,https://r\n')
    names = community_page.build_page_data(2025)['people_names']
    assert names['tisto'] == 'timo'
    assert names[community_page.fold('tisto-work')] == 'timo'


def test_people_names_drop_an_ambiguous_name(repo):
    write(paths.PEOPLE, 'id,name,github,source\nana-1,Ana Silva,,https://r\nana-2,Ana Silva,,https://r\n'
                        'bob,Bob Jones,,https://r\n')
    assert community_page.build_page_data(2025)['people_names'] == {'bob jones': 'bob'}


def test_organiser_role_counts_for_the_persons_organisation(repo):
    # The entity that organised a sprint gets the event, the organising person's organisation gets the role
    write(paths.COMMUNITY / '2025-sprints.csv', SPRINTS + 'Sprint A,,,X,mauro,kitconcept,strategic,https://a,\n')
    organisations = community_page.build_page_data(2025)['organisations']
    # RedTurtle earns a level from the conference, kitconcept from the sprint
    assert organisations['redturtle']['history']['2025'] == {'commits': 0, 'pull_requests': 0, 'roles': 1,
                                                             'events': 1}  # the conference
    assert organisations['kitconcept-gmbh']['history']['2025'] == {'commits': 0, 'pull_requests': 0, 'roles': 0,
                                                                   'events': 1}


def test_unmapped_is_not_listed_as_an_event_organiser(repo):
    write(paths.COMMUNITY / '2025-plone-conference.csv', CONFERENCE + 'redturtle,,https://a,\n')
    write(paths.COMMUNITY / '2025-sprints.csv', SPRINTS + 'Sprint A,,,X,,kitconcept,strategic,https://a,\n')
    events = community_page.build_page_data(2025)['history']['2025']['events']
    assert [e['organisations'] for e in events] == [['RedTurtle'], ['kitconcept GmbH']]


def test_board_and_team_leads_carry_the_display_name_and_organisation(repo):
    write(paths.PEOPLE, 'id,name,github,source\ntimo,Timo Stollenwerk,tisto,https://r\nanna,Anna Board,,https://r\n')
    write(paths.COMMUNITY / '2025-board-of-directors.csv', BOARD + 'anna,voting,https://b,\n')
    write(paths.COMMUNITY / '2025-team-leaders.csv', TEAM_LEADERS + 'timo,Volto Team,https://c,\n')
    history = community_page.build_page_data(2025)['history']['2025']
    assert history['board'] == [{'name': 'Anna Board', 'organisation': 'Unmapped', 'source': 'https://b'}]
    assert history['team_leads'] == [{'name': 'Timo Stollenwerk', 'team': 'Volto Team',
                                      'organisation': 'kitconcept GmbH', 'source': 'https://c'}]


def test_pull_request_contributions_link_the_row_of_each_year(repo):
    for year in range(2021, 2026):
        write(paths.organisation_contributors_file(year), ORGANISATIONS + 'RedTurtle,1,150,1\n')
    [prs] = community_page.build_page_data(2025)['organisations']['redturtle']['categories'][
        'PR Contributions']['contributions']
    assert prs['rows'] == [[str(year), str(paths.organisation_contributors_file(year)), 2]
                           for year in range(2021, 2026)]


def test_equal_contributions_are_merged(repo):
    write(paths.COMMUNITY / '2025-plone-conference-trainings.csv', TRAININGS + 'Volto,timo;robert,https://t,\n')
    [training] = community_page.build_page_data(2025)['organisations']['kitconcept-gmbh']['categories'][
        'Training Session']['contributions']
    assert training['points'] == 4


def test_names_of_the_register_are_in_the_data(repo):
    # The people search finds a person by name or by another name of the person
    write(paths.PEOPLE, 'id,name,github,source\ndavid-glick,David Glick,davisagli,https://r\n')
    write(paths.IDENTITIES, 'person,kind,value,source\ndavid-glick,name,D. Glick,https://r\n')
    assert community_page.build_page_data(2025)['people_names'] == {'david glick': 'david-glick',
                                                                    'd glick': 'david-glick',
                                                                    'davisagli': 'david-glick'}


def test_people_names_are_keyed_by_fold(repo):
    # The page computes the same key in site.js; lower case, not casefold: ß stays ß
    write(paths.PEOPLE, 'id,name,github,source\n'
                        'tamara-eer,Tamara Eßer,,https://r\nvictor,Víctor  Fernández,,https://r\n')
    names = community_page.build_page_data(2025)['people_names']
    assert names == {community_page.fold('Tamara Eßer'): 'tamara-eer',
                     community_page.fold('Víctor  Fernández'): 'victor'}
    assert set(names) == {'tamara eßer', 'victor fernandez'}


def test_people_carry_the_organisation_of_the_year(repo):
    # The person card names the organisation the affiliations give the person for the year
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\nzed,1,1\n')
    write(paths.COMMUNITY / '2025-board-of-directors.csv', BOARD + 'anna,voting,https://b,\n')
    people = {p['id']: p['organisation'] for p in community_page.build_page_data(2025)['people']['2025']}
    # anna has no affiliation, zed is a login outside the register
    assert people == {'timo': 'kitconcept GmbH', 'anna': 'Unmapped', 'zed': 'Unmapped'}


def test_the_organisation_of_a_person_follows_the_years_of_the_affiliation(repo):
    # timo left kitconcept after 2023 and joined RedTurtle in 2025: each year's entry says where he was
    write(paths.AFFILIATIONS, 'person,organisation,from,to,source,checked,notes\n'
                              'timo,kitconcept,2000,2023,https://r,,\ntimo,redturtle,2025,,https://r,,\n')
    for year in (2023, 2024, 2025):
        write(paths.contributors_file(year), CONTRIBUTORS + 'tisto,1,0\n')
    data = community_page.build_page_data(2025)
    organisation = {year: data['people'][year][0]['organisation'] for year in ('2023', '2024', '2025')}
    assert organisation == {'2023': 'kitconcept GmbH', '2024': 'Unmapped', '2025': 'RedTurtle'}
