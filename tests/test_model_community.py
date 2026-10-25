"""Reading roles, events and items from the community files: one file per kind, rows of every year (#139)."""

import pytest

from tests.conftest import community_event, community_rows
from scripts.lib import paths
from scripts.lib.model import community_years, events, items, roles, talks

SRC = 'https://example.org/record'
EVENTS = 'curated/community/events.csv'


@pytest.fixture
def community(tmp_repo):
    return tmp_repo


def test_roles_split_set_columns(community):
    community_event('plone-conference-2023', 'conference', 2023)
    community_rows('trainings', {'event': 'plone-conference-2023', 'title': 'Training A', 'trainers': 'pbauer;tschorr',
                                 'cited_as': SRC},
                   {'event': 'plone-conference-2023', 'title': 'Training B', 'trainers': 'pbauer', 'cited_as': SRC})
    found = roles(2023)
    assert [(r.person, r.label, r.detail, r.line) for r in found] == [
        ('pbauer', 'Trainer', 'Training A', 2), ('tschorr', 'Trainer', 'Training A', 2),
        ('pbauer', 'Trainer', 'Training B', 3)]
    assert found[0].source == SRC and found[0].kind == 'plone-conference-trainings'
    assert found[0].file == 'curated/community/trainings.csv'


def test_roles_skip_non_talks(community):
    community_event('wpd-2023-online', 'wpd', 2023, format='online')
    community_rows('talks', {'event': 'wpd-2023-online', 'type': 'Talk', 'title': 'A talk', 'speakers': 'pbauer',
                             'cited_as': SRC},
                   {'event': 'wpd-2023-online', 'type': 'Teaser', 'title': 'A teaser', 'speakers': 'tschorr',
                    'cited_as': SRC},
                   {'event': 'wpd-2023-online', 'type': 'Talk', 'title': 'Company talk', 'organisations': 'starzel',
                    'cited_as': SRC})
    assert [(r.person, r.label, r.detail) for r in roles(2023)] == [('pbauer', 'Speaker', 'A talk')]
    # the recognition script gets every row, whatever the type, and the organisation-only row too
    found = items(2023, 'world-plone-day-talks')
    assert [i.key for i in found] == ['A talk', 'A teaser', 'Company talk']
    assert found[2].people == () and found[2].organisations == ('starzel',)


def test_items_carry_the_columns_of_the_old_kind_and_the_row_of_the_new_file(community):
    community_event('alpine-city-sprint', 'sprint', 2023, ('pbauer', 'tschorr'), ('starzel', 'syslab'),
                    cited_as=f'report: {SRC}', name='Alpine City Sprint', start='2023-03-01', end='2023-03-05',
                    location='Innsbruck', level='strategic', sources='abcdef012345', notes='a note')
    [item] = items(2023, 'sprints')
    assert (item.kind, item.year, item.key, item.file, item.line) == (
        'sprints', 2023, 'Alpine City Sprint', EVENTS, 2)
    # The source is the old source cell: the row's citation, verbatim
    assert item.source == f'report: {SRC}' and item.notes == 'a note'
    assert item.people == ('pbauer', 'tschorr') and item.organisations == ('starzel', 'syslab')
    assert item.fields == {'sprint': 'Alpine City Sprint', 'start': '2023-03-01', 'end': '2023-03-05',
                           'location': 'Innsbruck', 'organisers': 'pbauer;tschorr', 'organisations': 'starzel;syslab',
                           'level': 'strategic', 'source': f'report: {SRC}', 'notes': 'a note'}


def test_items_of_a_year_keep_the_order_of_the_files(community):
    # The page and the points follow it: a strategic sprint counts once per organisation, the first one
    community_event('z-sprint', 'sprint', 2023, organisations=('beta', 'acme'), name='Z sprint')
    community_event('other-year', 'sprint', 2022, name='Other year')
    community_event('a-sprint', 'sprint', 2023, organisations=('acme',), name='A sprint')
    assert [(i.key, i.organisations, i.line) for i in items(2023, 'sprints')] == [
        ('Z sprint', ('beta', 'acme'), 2), ('A sprint', ('acme',), 4)]


def test_events_sprint_level_and_organisations(community):
    community_event('alpine-city-sprint', 'sprint', 2023, ('pbauer', 'tschorr'), ('starzel', 'syslab'),
                    name='Alpine City Sprint', start='2023-03-01', level='strategic')
    community_event('old-sprint', 'sprint', 2023, name='Old Sprint')
    community_event('plone-conference-2023', 'conference', 2023, name='Plone Conference 2023', cited_as='')
    community_rows('organisers', {'event': 'plone-conference-2023', 'person': 'pbauer', 'cited_as': SRC},
                   {'event': 'plone-conference-2023', 'organisation': 'starzel', 'cited_as': SRC},
                   {'event': 'plone-conference-2023', 'organisation': 'syslab', 'cited_as': 'https://example.org/2'},
                   {'event': 'plone-conference-2023', 'person': 'tschorr', 'cited_as': 'https://example.org/2'})
    found = events(2023)
    assert [(e.kind, e.name, e.level) for e in found] == [
        ('plone-conference', 'Plone Conference 2023', ''),
        ('sprints', 'Alpine City Sprint', 'strategic'), ('sprints', 'Old Sprint', '')]
    conference, sprint = found[0], found[1]
    assert conference.organisations == ('starzel', 'syslab')
    assert conference.organisers == ('pbauer', 'tschorr')
    assert conference.sources == (SRC, 'https://example.org/2')
    assert (conference.file, conference.line) == (EVENTS, 4)
    assert sprint.organisations == ('starzel', 'syslab') and sprint.organisers == ('pbauer', 'tschorr')
    assert sprint.sources == (SRC,)
    assert (sprint.file, sprint.line) == (EVENTS, 2)
    assert [r.label for r in roles(2023)] == ['Sprint organiser', 'Sprint organiser', 'Conference organiser',
                                              'Conference organiser']


def test_the_conference_items_are_its_organiser_rows(community):
    community_event('plone-conference-2023', 'conference', 2023, cited_as='')
    community_rows('organisers', {'event': 'plone-conference-2023', 'person': 'pbauer', 'cited_as': SRC},
                   {'event': 'plone-conference-2023', 'organisation': 'starzel', 'cited_as': SRC, 'notes': 'host'})
    found = items(2023, 'plone-conference')
    assert [(i.key, i.people, i.organisations, i.notes, i.file, i.line) for i in found] == [
        ('', ('pbauer',), (), '', 'curated/community/organisers.csv', 2),
        ('starzel', (), ('starzel',), 'host', 'curated/community/organisers.csv', 3)]
    assert found[1].fields == {'organisation': 'starzel', 'organisers': None, 'source': SRC, 'notes': 'host'}


def test_a_conference_without_organisers_is_no_event(community):
    # The conference of a year with talks or trainings only: its organisers are not recorded
    community_event('plone-conference-2023', 'conference', 2023, cited_as='')
    community_rows('trainings', {'event': 'plone-conference-2023', 'title': 'A training', 'cited_as': SRC})
    assert events(2023) == [] and items(2023, 'plone-conference') == []


def test_events_wpd_online_is_no_event(community):
    community_event('wpd-2023-04-20-vienna', 'wpd', 2023, ('pbauer',), ('starzel',), location='Vienna',
                    start='2023-04-20', format='in person')
    community_event('wpd-2023-04-20-graz', 'wpd', 2023, location='Graz', start='2023-04-20', format='hybrid')
    community_event('wpd-2023-04-20-internet', 'wpd', 2023, location='Internet', start='2023-04-20', format='online')
    assert [e.name for e in events(2023)] == ['World Plone Day 2023, Vienna', 'World Plone Day 2023, Graz']
    assert events(2023)[0].organisations == ('starzel',) and events(2023)[0].organisers == ('pbauer',)
    found = items(2023, 'world-plone-day-event')
    assert [i.key for i in found] == ['Vienna', 'Graz', 'Internet']
    assert found[0].fields['format'] == 'in person' and str(found[0].fields['date']) == '2023-04-20'


def test_the_online_edition_that_holds_the_online_talks_is_no_wpd_row(community):
    # The yearly files had no row for it: it holds the talks given online
    community_event('wpd-2023-online', 'wpd', 2023, cited_as='', name='World Plone Day 2023, Online',
                    location='Online', format='online')
    assert items(2023, 'world-plone-day-event') == []


def test_items_podcasts_episodes_int(community):
    community_rows('podcasts', {'year': 2023, 'series': 'Plone Podcast', 'person': 'pbauer', 'episodes': 7,
                                'cited_as': SRC, 'notes': 'hi'},
                   {'year': 2024, 'series': 'Plone Podcast', 'person': 'pbauer', 'episodes': 2, 'cited_as': SRC})
    (item,) = items(2023, 'podcasts')
    assert item.key == 'Plone Podcast' and item.people == ('pbauer',) and item.organisations == ()
    assert item.fields == {'series': 'Plone Podcast', 'person': 'pbauer', 'episodes': 7, 'source': SRC, 'notes': 'hi'}
    assert item.notes == 'hi' and item.line == 2 and item.file == 'curated/community/podcasts.csv'
    assert [(r.person, r.label, r.detail) for r in roles(2023)] == [('pbauer', 'Podcast', 'Plone Podcast')]


def test_roles_of_the_roles_files_are_those_of_the_year(community):
    community_rows('board-of-directors', {'year': 2022, 'person': 'ann', 'role': 'voting', 'cited_as': SRC},
                   {'year': 2023, 'person': 'zoe', 'role': 'voting', 'cited_as': SRC, 'notes': 'chair'},
                   {'year': 2023, 'person': 'ann', 'role': 'non-voting', 'cited_as': SRC})
    community_rows('team-leaders', {'year': 2023, 'person': 'ann', 'team': 'Volto Team', 'cited_as': SRC})
    community_rows('release-managers', {'year': 2023, 'person': 'zoe', 'cited_as': SRC})
    assert [(r.kind, r.person, r.detail, r.line, r.notes) for r in roles(2023)] == [
        ('board-of-directors', 'zoe', '', 3, 'chair'), ('board-of-directors', 'ann', '', 4, ''),
        ('team-leaders', 'ann', 'Volto Team', 2, ''), ('release-managers', 'zoe', '', 2, '')]
    assert items(2023, 'board-of-directors')[0].fields == {'person': 'zoe', 'role': 'voting', 'source': SRC,
                                                           'notes': 'chair'}


def test_missing_file_is_empty(community):
    assert roles(2023) == [] and events(2023) == [] and items(2023, 'podcasts') == [] and talks(2023) == []
    assert community_years() == []


def test_an_unknown_kind_is_an_error(community):
    with pytest.raises(KeyError):
        items(2023, 'barbecues')


def test_missing_column_names_the_file(community):
    (paths.COMMUNITY / 'release-managers.csv').write_text(f'year,sources,cited_as,notes\n2023,,{SRC},\n',
                                                          encoding='utf-8')
    with pytest.raises(KeyError, match='release-managers.csv'):
        roles(2023)


def test_community_years_are_the_years_with_rows(community):
    community_event('a-sprint', 'sprint', 2014)
    community_rows('release-managers', {'year': 2023, 'person': 'zoe', 'cited_as': SRC})
    assert community_years() == [2014, 2023]


def test_conference_talks_are_speaker_roles_of_every_type(community):
    community_event('plone-conference-2021', 'conference', 2021, cited_as='', name='Plone Conference 2021')
    community_event('plone-tagung-2021', 'symposium', 2021, cited_as='', name='Plone Tagung 2021')
    community_rows('talks', {'event': 'plone-conference-2021', 'type': 'Keynote', 'title': 'Opening keynote',
                             'speakers': 'pbauer', 'video': 'https://v/1', 'cited_as': SRC},
                   {'event': 'plone-conference-2021', 'type': 'Panel', 'title': 'The panel',
                    'speakers': 'pbauer;tschorr', 'cited_as': SRC},
                   {'event': 'plone-tagung-2021', 'type': 'Talk', 'title': 'Team talk', 'organisations': 'starzel',
                    'cited_as': SRC},
                   {'event': 'plone-tagung-2021', 'type': 'Talk', 'title': 'Nobody known', 'cited_as': SRC,
                    'notes': 'speaker without a public identity'})
    assert [(r.person, r.label, r.detail, r.line) for r in roles(2021)] == [
        ('pbauer', 'Speaker', 'Opening keynote', 2), ('pbauer', 'Speaker', 'The panel', 3),
        ('tschorr', 'Speaker', 'The panel', 3)]
    found = items(2021, 'conference-talks')
    assert [i.key for i in found] == ['Opening keynote', 'The panel', 'Team talk', 'Nobody known']
    assert found[2].people == () and found[2].organisations == ('starzel',)
    assert found[3].people == () and found[3].organisations == ()
    assert [(i.fields['event'], i.fields['scope']) for i in found] == [
        ('Plone Conference 2021', 'global'), ('Plone Conference 2021', 'global'), ('Plone Tagung 2021', 'regional'),
        ('Plone Tagung 2021', 'regional')]


def test_world_plone_day_speakers_are_speakers_too(community):
    community_event('wpd-2023-online', 'wpd', 2023, format='online')
    community_rows('talks', {'event': 'wpd-2023-online', 'type': 'Talk', 'title': 'A talk', 'speakers': 'pbauer',
                             'cited_as': SRC})
    assert [(r.person, r.label) for r in roles(2023)] == [('pbauer', 'Speaker')]


def test_talks_per_person_with_event_and_video(community):
    community_event('plone-conference-2021', 'conference', 2021, cited_as='', name='Plone Conference 2021')
    community_event('plone-tagung-2021', 'symposium', 2021, cited_as='', name='Plone Tagung 2021')
    community_event('wpd-2021-04-28-bonn', 'wpd', 2021, location='Bonn', format='in person')
    community_rows('talks', {'event': 'plone-tagung-2021', 'type': 'Talk', 'title': 'Regional talk',
                             'speakers': 'pbauer', 'cited_as': SRC},
                   {'event': 'wpd-2021-04-28-bonn', 'type': 'Talk', 'title': 'WPD talk', 'speakers': 'pbauer',
                    'video': 'https://www.youtube.com/watch?v=abc',
                    'cited_as': 'https://www.youtube.com/watch?v=abc; https://example.org/event'},
                   {'event': 'plone-conference-2021', 'type': 'Talk', 'title': 'Global talk',
                    'speakers': 'pbauer;tschorr', 'video': 'https://v/2', 'cited_as': SRC},
                   {'event': 'wpd-2021-04-28-bonn', 'type': 'Teaser', 'title': 'A teaser', 'speakers': 'pbauer',
                    'cited_as': SRC})
    found = talks(2021)
    assert [(t.person, t.event, t.title, t.video) for t in found] == [
        ('pbauer', 'Plone Tagung 2021', 'Regional talk', None),
        ('pbauer', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('tschorr', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('pbauer', 'World Plone Day 2021', 'WPD talk', 'https://www.youtube.com/watch?v=abc')]
    assert found[0].kind == 'conference-talks' and found[3].kind == 'world-plone-day-talks'
    assert found[1].line == 4 and found[1].source == SRC and found[1].file == 'curated/community/talks.csv'


def test_talks_of_a_year_without_files(community):
    assert talks(2019) == []


def test_talks_of_another_year_are_left_out(community):
    community_event('wpd-2024-online', 'wpd', 2024, format='online')
    community_rows('talks', {'event': 'wpd-2024-online', 'type': 'Talk', 'title': 'A talk', 'speakers': 'pbauer',
                             'cited_as': SRC})
    assert talks(2023) == [] and items(2023, 'world-plone-day-talks') == []
    assert [t.title for t in talks(2024)] == ['A talk']


def test_a_world_plone_day_talk_without_a_video_has_none(community):
    # Four World Plone Day talks have an event page as their only source ("No video."): that is not a recording
    community_event('wpd-2025-04-10-brasilia', 'wpd', 2025, format='in person')
    community_rows('talks', {'event': 'wpd-2025-04-10-brasilia', 'type': 'Talk', 'title': 'Page only',
                             'speakers': 'pbauer', 'cited_as': 'https://plone.org.br/novidades/eventos/2025/wpd',
                             'notes': 'No video.'},
                   {'event': 'wpd-2025-04-10-brasilia', 'type': 'Talk', 'title': 'Vimeo', 'speakers': 'tschorr',
                    'video': 'https://vimeo.com/12345', 'cited_as': 'https://vimeo.com/12345'})
    assert [(t.title, t.video) for t in talks(2025)] == [('Page only', None), ('Vimeo', 'https://vimeo.com/12345')]


def test_a_rewritten_file_is_read_again(community):
    community_rows('release-managers', {'year': 2023, 'person': 'zoe', 'cited_as': SRC})
    assert [r.person for r in roles(2023)] == ['zoe']
    (paths.COMMUNITY / 'release-managers.csv').write_text(f'year,person,sources,cited_as,notes\n2023,ann,,{SRC},\n',
                                                          encoding='utf-8')
    assert [r.person for r in roles(2023)] == ['ann']


def test_a_world_plone_day_event_without_its_day_names_the_event(community):
    # The check refuses it; if one gets through, the reader says which event
    community_event('wpd-2023-bonn', 'wpd', 2023, start='2023-04', location='Bonn', format='in person')
    with pytest.raises(ValueError, match='events.csv:2: the World Plone Day event wpd-2023-bonn starts on "2023-04"'):
        events(2023)
