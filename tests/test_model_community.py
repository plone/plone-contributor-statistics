"""Reading roles, events and items from community files in the new shape."""

import shutil
from pathlib import Path

import pytest

from scripts.lib import paths
from scripts.lib.model import events, items, roles, talks

REPO = Path(__file__).resolve().parent.parent
SRC = 'https://example.org/record'
TALKS = 'event,scope,type,title,speakers,organisations,video,source,notes\n'


@pytest.fixture
def community(tmp_repo):
    shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)

    def write(name, text):
        (paths.COMMUNITY / name).write_text(text, encoding='utf-8')

    return write


def test_roles_split_set_columns(community):
    community('2023-plone-conference-trainings.csv',
              f'title,trainers,source,notes\nTraining A,pbauer;tschorr,{SRC},\nTraining B,pbauer,{SRC},\n')
    found = roles(2023)
    assert [(r.person, r.label, r.detail, r.line) for r in found] == [
        ('pbauer', 'Trainer', 'Training A', 2), ('tschorr', 'Trainer', 'Training A', 2),
        ('pbauer', 'Trainer', 'Training B', 3)]
    assert found[0].source == SRC and found[0].kind == 'plone-conference-trainings'


def test_roles_skip_non_talks(community):
    community('2023-world-plone-day-talks.csv',
              'title,speakers,organisations,type,location,source,notes\n'
              f'A talk,pbauer,,Talk,,{SRC},\n'
              f'A teaser,tschorr,,Teaser,,{SRC},\n'
              f'Company talk,,starzel,Talk,,{SRC},\n')
    assert [(r.person, r.label, r.detail) for r in roles(2023)] == [('pbauer', 'Speaker', 'A talk')]
    # the recognition script gets every row, whatever the type, and the organisation-only row too
    found = items(2023, 'world-plone-day-talks')
    assert [i.key for i in found] == ['A talk', 'A teaser', 'Company talk']
    assert found[2].people == () and found[2].organisations == ('starzel',)


def test_events_sprint_level_and_organisations(community):
    community('2023-sprints.csv',
              'sprint,start,end,location,organisers,organisations,level,source,notes\n'
              f'Alpine City Sprint,2023-03-01,2023-03-05,Innsbruck,pbauer;tschorr,starzel;syslab,strategic,{SRC},\n'
              f'Old Sprint,,,,,,,{SRC},\n')
    community('2023-plone-conference.csv',
              f'organisation,organisers,source,notes\nstarzel,pbauer,{SRC},\nsyslab,tschorr,https://example.org/2,\n'
              f'starzel,,{SRC},\n')
    found = events(2023)
    assert [(e.kind, e.name, e.level) for e in found] == [
        ('plone-conference', 'Plone Conference 2023', ''),
        ('sprints', 'Alpine City Sprint', 'strategic'), ('sprints', 'Old Sprint', '')]
    conference, sprint = found[0], found[1]
    assert conference.organisations == ('starzel', 'syslab')
    assert conference.organisers == ('pbauer', 'tschorr')
    assert conference.sources == (SRC, 'https://example.org/2')
    assert sprint.organisations == ('starzel', 'syslab') and sprint.organisers == ('pbauer', 'tschorr')
    assert sprint.line == 2 and sprint.file.endswith('2023-sprints.csv')
    assert [r.label for r in roles(2023)] == ['Sprint organiser', 'Sprint organiser', 'Conference organiser',
                                              'Conference organiser']


def test_events_wpd_online_is_no_event(community):
    community('2023-world-plone-day-event.csv',
              'date,location,format,organisations,organisers,source,notes\n'
              f'2023-04-20,Vienna,in person,starzel,pbauer,{SRC},\n'
              f'2023-04-20,Graz,hybrid,,,{SRC},\n'
              f'2023-04-20,Internet,online,,,{SRC},\n')
    assert [e.name for e in events(2023)] == ['World Plone Day 2023, Vienna', 'World Plone Day 2023, Graz']
    assert events(2023)[0].organisations == ('starzel',)


def test_items_podcasts_episodes_int(community):
    community('2023-podcasts.csv', f'series,person,episodes,source,notes\nPlone Podcast,pbauer,7,{SRC},hi\n')
    (item,) = items(2023, 'podcasts')
    assert item.key == 'Plone Podcast' and item.people == ('pbauer',) and item.organisations == ()
    assert item.fields['episodes'] == 7 and item.notes == 'hi' and item.line == 2
    assert [(r.person, r.label, r.detail) for r in roles(2023)] == [('pbauer', 'Podcast', 'Plone Podcast')]


def test_missing_file_is_empty(community):
    assert roles(2023) == [] and events(2023) == [] and items(2023, 'podcasts') == []


def test_missing_column_names_the_file(community):
    community('2023-release-managers.csv', f'source,notes\n{SRC},\n')
    with pytest.raises(KeyError, match='2023-release-managers.csv'):
        roles(2023)


def test_conference_talks_are_speaker_roles_of_every_type(community):
    community('2021-conference-talks.csv', TALKS +
              f'Plone Conference 2021,global,Keynote,Opening keynote,pbauer,,https://v/1,{SRC},\n'
              f'Plone Conference 2021,global,Panel,The panel,pbauer;tschorr,,,{SRC},\n'
              f'Plone Tagung 2021,regional,Talk,Team talk,,starzel,,{SRC},\n'
              f'Plone Tagung 2021,regional,Talk,Nobody known,,,,{SRC},speaker without a public identity\n')
    assert [(r.person, r.label, r.detail, r.line) for r in roles(2021)] == [
        ('pbauer', 'Speaker', 'Opening keynote', 2), ('pbauer', 'Speaker', 'The panel', 3),
        ('tschorr', 'Speaker', 'The panel', 3)]
    found = items(2021, 'conference-talks')
    assert [i.key for i in found] == ['Opening keynote', 'The panel', 'Team talk', 'Nobody known']
    assert found[2].people == () and found[2].organisations == ('starzel',)
    assert found[3].people == () and found[3].organisations == ()


def test_world_plone_day_speakers_are_speakers_too(community):
    community('2023-world-plone-day-talks.csv',
              f'title,speakers,organisations,type,location,source,notes\nA talk,pbauer,,Talk,,{SRC},\n')
    assert [(r.person, r.label) for r in roles(2023)] == [('pbauer', 'Speaker')]


def test_talks_per_person_with_event_and_video(community):
    community('2021-conference-talks.csv', TALKS +
              f'Plone Tagung 2021,regional,Talk,Regional talk,pbauer,,,{SRC},\n'
              f'Plone Conference 2021,global,Talk,Global talk,pbauer;tschorr,,https://v/2,{SRC},\n')
    community('2021-world-plone-day-talks.csv',
              'title,speakers,organisations,type,location,source,notes\n'
              'WPD talk,pbauer,,Talk,,https://www.youtube.com/watch?v=abc; https://example.org/event,\n'
              f'A teaser,pbauer,,Teaser,,{SRC},\n')
    found = talks(2021)
    assert [(t.person, t.event, t.title, t.video) for t in found] == [
        ('pbauer', 'Plone Tagung 2021', 'Regional talk', None),
        ('pbauer', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('tschorr', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('pbauer', 'World Plone Day 2021', 'WPD talk', 'https://www.youtube.com/watch?v=abc')]
    assert found[0].kind == 'conference-talks' and found[3].kind == 'world-plone-day-talks'
    assert found[1].line == 3 and found[1].source == SRC


def test_talks_of_a_year_without_files(community):
    assert talks(2019) == []


def test_world_plone_day_video_is_only_a_link_to_a_video_host(community):
    # Four World Plone Day talks have an event page as their only source ("No video."): that is not a recording
    community('2025-world-plone-day-talks.csv',
              'title,speakers,organisations,type,location,source,notes\n'
              'Page only,pbauer,,Talk,,https://plone.org.br/novidades/eventos/2025/wpd-2025-brasilia,No video.\n'
              'Short link,pbauer,,Talk,,https://youtu.be/abc123; https://plone.org.br/event,\n'
              'Vimeo,tschorr,,Talk,,https://vimeo.com/12345,\n')
    assert [(t.title, t.video) for t in talks(2025)] == [
        ('Page only', None), ('Short link', 'https://youtu.be/abc123'), ('Vimeo', 'https://vimeo.com/12345')]
