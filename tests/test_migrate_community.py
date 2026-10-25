"""The migration of the yearly community files to one file per kind (plan 3b): offline, on fixtures."""

import csv
import hashlib

import pytest

from scripts.lib import paths
from scripts.lib.model.sources import source_id
from scripts.tools import migrate_community
from scripts.tools.migrate_community import migrate, short_reason

PAGE = 'https://plone.org/events/sprint-report'
MINUTES = 'https://plone.org/foundation/minutes'
VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'
GONE = 'https://example.org/gone'
EMPTY = 'https://example.org/empty'
ARCHIVED = 'https://web.archive.org/web/20090101000000/http://plone.org/old'
SPRINT_FIELDS = 'sprint,start,end,location,organisers,organisations,level,source,notes'
WPD_FIELDS = 'date,location,format,organisations,organisers,source,notes'
WPD_TALK_FIELDS = 'title,speakers,organisations,type,location,source,notes'
TALK_FIELDS = 'event,scope,type,title,speakers,organisations,video,source,notes'


def row(fields, *values):
    names = fields.split(',')
    assert len(names) == len(values)
    return dict(zip(names, values))


def sprint(name, start='2014-01-01', end='2014-01-05', organisers='', organisations='', level='', source=PAGE,
           notes=''):
    return row(SPRINT_FIELDS, name, start, end, 'Here', organisers, organisations, level, source, notes)


def wpd(date, location, fmt='in person', organisations='', organisers='', source=PAGE, notes=''):
    return row(WPD_FIELDS, date, location, fmt, organisations, organisers, source, notes)


def wpd_talk(title, location='Online', kind='Talk', speakers='', source=VIDEO, notes=''):
    return row(WPD_TALK_FIELDS, title, speakers, '', kind, location, source, notes)


def talk(title, event='Plone Conference 2014', scope='global', kind='Talk', speakers='', video='', source=PAGE,
         notes=''):
    return row(TALK_FIELDS, event, scope, kind, title, speakers, '', video, source, notes)


def captured(*urls):
    """The capture results and the register for addresses that were all captured."""
    results = [{'url': url, 'source_id': source_id(url), 'error': None} for url in urls]
    return results, {source_id(url): {'id': source_id(url), 'kind': 'page'} for url in urls}


def run(old, results=None, sources=None, **kwargs):
    if results is None:
        urls = {PAGE, MINUTES, VIDEO}
        results, sources = captured(*sorted(urls))
    return migrate(old, results, sources, **kwargs)


def by(rows, key):
    return {r[key]: r for r in rows}


def hex8(text):
    return hashlib.sha1(text.encode()).hexdigest()[:8]


# Decision 2: sources and cited_as


def test_sources_are_the_ids_of_the_cell_in_order_and_cited_as_is_the_cell():
    cell = f'Board: {MINUTES}; report: {PAGE}; again {MINUTES}'
    migrated = run({'release-managers': {2020: [row('person,source,notes', 'jane-doe', cell, '')]}})
    [manager] = migrated.roles['release-managers']
    assert manager == {'year': '2020', 'person': 'jane-doe', 'sources': f'{source_id(MINUTES)};{source_id(PAGE)}',
                       'cited_as': cell, 'notes': ''}


def test_a_cell_without_an_address_keeps_its_text_and_has_no_sources():
    migrated = run({'release-managers': {2020: [row('person,source,notes', 'jane-doe', 'the minutes', ''),
                                                row('person,source,notes', 'john-roe', '', '')]}})
    first, second = migrated.roles['release-managers']
    assert (first['sources'], first['cited_as']) == ('', 'the minutes')
    assert (second['sources'], second['cited_as']) == ('', '')


def test_an_uncaptured_address_gets_a_deterministic_source_with_the_reason():
    results, sources = captured(PAGE)
    results += [{'url': GONE, 'source_id': None, 'error': f'{GONE}: a new source needs at least one quote or name'},
                {'url': EMPTY, 'source_id': None, 'error': None},
                {'url': ARCHIVED, 'source_id': None,
                 'error': f'{ARCHIVED}: {ARCHIVED.replace("000/", "000id_/")} ContentDecodingError: bad\nmore'},
                {'url': VIDEO, 'source_id': None, 'error': None}]
    cell = f'{PAGE}; {GONE}; {EMPTY}; {ARCHIVED}; {VIDEO}'
    migrated = run({'release-managers': {2020: [row('person,source,notes', 'jane-doe', cell, '')]}}, results, sources,
                   worklist=[{'url': VIDEO, 'kind': 'video'}])
    gone, empty, archived, video = source_id(GONE), source_id(EMPTY), source_id('http://plone.org/old',
                                                                                  '20090101000000'), source_id(VIDEO)
    assert migrated.roles['release-managers'][0]['sources'] == ';'.join([source_id(PAGE), gone, empty, archived, video])
    new = by(migrated.new_sources, 'id')
    assert [r['id'] for r in migrated.new_sources] == sorted([gone, empty, archived, video])
    assert new[gone]['notes'] == 'not captured on 2026-10-25: a new source needs at least one quote or name'
    assert new[empty]['notes'] == 'not captured on 2026-10-25: nothing found'
    assert new[archived] | {'fetched': None} == {
        'id': archived, 'kind': 'page', 'title': ARCHIVED, 'date': '2026-10-25', 'url': 'http://plone.org/old',
        'archive_url': 'https://web.archive.org/web/20090101000000/http://plone.org/old', 'fetched': None,
        'notes': 'not captured on 2026-10-25: ContentDecodingError: bad'}
    assert new[video]['kind'] == 'video'
    assert migrated.new_excerpts[gone] == new[gone]['notes']


def test_the_reason_of_an_uncaptured_address_holds_no_address():
    results = [{'url': VIDEO, 'source_id': None, 'error': f'{VIDEO}: {VIDEO} has no captions'}]
    migrated = run({'release-managers': {2020: [row('person,source,notes', 'jane-doe', VIDEO, '')]}}, results, {})
    assert migrated.new_sources[0]['notes'] == 'not captured on 2026-10-25: has no captions'


def test_an_uncaptured_address_that_the_register_holds_keeps_its_source():
    results = [{'url': GONE, 'source_id': None, 'error': None}]
    migrated = run({'release-managers': {2020: [row('person,source,notes', 'jane-doe', GONE, '')]}}, results,
                   {source_id(GONE): {'id': source_id(GONE), 'kind': 'page'}})
    assert migrated.roles['release-managers'][0]['sources'] == source_id(GONE)
    assert migrated.new_sources == []


def test_an_address_without_a_capture_result_is_found_in_the_register():
    old = {'release-managers': {2020: [row('person,source,notes', 'jane-doe', f'{VIDEO}; {ARCHIVED}', '')]}}
    archived = source_id('http://plone.org/old', '20090101000000')
    register = {source_id(VIDEO): {'id': source_id(VIDEO), 'kind': 'video'}, archived: {'id': archived}}
    assert run(old, [], register).roles['release-managers'][0]['sources'] == f'{source_id(VIDEO)};{archived}'


def test_an_address_without_a_capture_result_or_with_an_unknown_source_is_an_error():
    old = {'release-managers': {2020: [row('person,source,notes', 'jane-doe', GONE, '')]}}
    with pytest.raises(ValueError, match='no capture result'):
        run(old, [], {})
    with pytest.raises(ValueError, match='not in the register'):
        run(old, [{'url': GONE, 'source_id': 'abc', 'error': None}], {})


def test_short_reason():
    assert short_reason('first line\nsecond') == 'first line'
    assert short_reason('yt-dlp failed\nERROR: HTTP Error 429: Too Many Requests') == 'rate limited (HTTP 429)'
    assert short_reason('yt-dlp failed\nWARNING: x\nERROR: [youtube] abc: Video unavailable') == (
        '[youtube] abc: Video unavailable')


# Decision 3: events


def test_the_plone_conference_event_of_every_year_with_a_conference_file_talks_or_trainings():
    old = {'plone-conference': {2010: []},
           'conference-talks': {2011: [talk('A', event='Plone Conference 2011')]},
           'plone-conference-trainings': {2012: [row('title,trainers,source,notes', 'T', 'ann-lee', PAGE, '')]},
           'sprints': {2013: [sprint('Sprint 2013', start='2013-01-01')]}}
    events = by(run(old).events, 'id')
    assert sorted(i for i in events if i.startswith('plone-conference')) == [
        'plone-conference-2010', 'plone-conference-2011', 'plone-conference-2012']
    assert events['plone-conference-2011'] == {
        'id': 'plone-conference-2011', 'kind': 'conference', 'name': 'Plone Conference 2011', 'year': '2011',
        'start': '', 'end': '', 'location': '', 'format': '', 'level': '', 'sources': '', 'cited_as': '',
        'notes': ''}


def test_a_global_talk_of_another_event_is_an_error():
    with pytest.raises(ValueError, match='Plone Conference 2014'):
        run({'conference-talks': {2014: [talk('A', event='Plone Konferenz 2014')]}})


def test_regional_talks_make_one_symposium_per_year_and_name():
    old = {'conference-talks': {
        2013: [talk('A', event='Plone Symposium East', scope='regional'),
               talk('B', event='Plone Symposium East', scope='regional'),
               talk('C', event='Plone Tagung 2013', scope='regional')],
        2014: [talk('D', event='Plone Symposium East', scope='regional')]}}
    migrated = run(old)
    events = by(migrated.events, 'id')
    assert sorted(events) == ['plone-symposium-east', 'plone-symposium-east-2', 'plone-tagung-2013']
    assert events['plone-symposium-east-2'] == {
        'id': 'plone-symposium-east-2', 'kind': 'symposium', 'name': 'Plone Symposium East', 'year': '2014',
        'start': '', 'end': '', 'location': '', 'format': '', 'level': '', 'sources': '', 'cited_as': '',
        'notes': ''}
    assert by(migrated.talks, 'title')['D']['event'] == 'plone-symposium-east-2'
    assert by(migrated.talks, 'title')['B']['event'] == 'plone-symposium-east'


def test_world_plone_day_events_keep_date_location_format_and_notes():
    old = {'world-plone-day-event': {2025: [wpd('2025-04-10', 'Bologna, Italy', organisations='redturtle',
                                                 source=f'"hosted" {PAGE}', notes='hosted by the region')]}}
    [event] = run(old).events
    assert event == {
        'id': 'wpd-2025-04-10-bologna-italy', 'kind': 'wpd', 'name': 'World Plone Day 2025, Bologna, Italy',
        'year': '2025', 'start': '2025-04-10', 'end': '', 'location': 'Bologna, Italy', 'format': 'in person',
        'level': '', 'sources': source_id(PAGE), 'cited_as': f'"hosted" {PAGE}', 'notes': 'hosted by the region'}


def test_wpd_events_on_one_day_stay_apart():
    old = {'world-plone-day-event': {2013: [wpd('2013-04-24', 'Berlin, Germany', organisations='a'),
                                            wpd('2013-04-24', 'Berlin, Germany', organisations='b'),
                                            wpd('2013-04-25', 'Berlin, Germany')]}}
    migrated = run(old)
    assert [e['id'] for e in migrated.events] == [
        'wpd-2013-04-24-berlin-germany', 'wpd-2013-04-24-berlin-germany-2', 'wpd-2013-04-25-berlin-germany']
    organisers = [(o['event'], o['organisation']) for o in migrated.organisers]
    assert organisers == [('wpd-2013-04-24-berlin-germany', 'a'), ('wpd-2013-04-24-berlin-germany-2', 'b')]


def test_sprint_ids():
    old = {'sprints': {
        2009: [sprint('Baarn sprint (Plone 4 UI)', start='', end=''), sprint('Jarn sprint', start='2009', end=''),
               sprint('Castle Sprint', start='2009-09', end='')],
        2016: [sprint('Castle Sprint', start='2016-09-15', end='2016-09-19', level='community'),
               sprint('Castle sprint!', start='2016-10-01', end='')],
        2017: [sprint('Midsummer Sprint Jyväskylä 2017', start='2017-07-03', end='2017-07-07', level='strategic')]}}
    events = run(old).events
    assert [(e['id'], e['year'], e['start'], e['end']) for e in events] == [
        ('baarn-sprint-plone-4-ui', '2009', '', ''), ('jarn-sprint', '2009', '2009', ''),
        ('castle-sprint', '2009', '2009-09', ''),
        ('castle-sprint-2', '2016', '2016-09-15', '2016-09-19'), ('castle-sprint-3', '2016', '2016-10-01', ''),
        ('midsummer-sprint-jyvaskyla-2017', '2017', '2017-07-03', '2017-07-07')]
    midsummer = events[-1]
    assert (midsummer['kind'], midsummer['name'], midsummer['level'], midsummer['location'], midsummer['format']) == (
        'sprint', 'Midsummer Sprint Jyväskylä 2017', 'strategic', 'Here', '')


def test_the_ids_do_not_depend_on_the_order_of_the_input():
    old = {'sprints': {2016: [sprint('Castle Sprint', start='2016-09-15')], 2009: [sprint('Castle Sprint')]},
           'plone-conference': {2016: [], 2009: []}}
    reordered = {'plone-conference': {2009: [], 2016: []},
                 'sprints': {2009: [sprint('Castle Sprint')], 2016: [sprint('Castle Sprint', start='2016-09-15')]}}
    assert run(old) == run(reordered)
    assert by(run(old).events, 'id')['castle-sprint']['year'] == '2009'


def test_events_are_ordered_by_year_start_and_id():
    old = {'sprints': {2014: [sprint('Z sprint', start='2014-03-01'), sprint('A sprint', start='2014-05-01'),
                              sprint('B sprint', start='')]},
           'plone-conference': {2014: []},
           'world-plone-day-event': {2014: [wpd('2014-04-30', 'Bonn, Germany')]}}
    assert [e['id'] for e in run(old).events] == [
        'b-sprint', 'plone-conference-2014', 'z-sprint', 'wpd-2014-04-30-bonn-germany', 'a-sprint']


# Decision 4: talks


def test_conference_talks_keep_their_columns_and_lose_the_scope():
    old = {'conference-talks': {2014: [talk('Keynote', kind='Keynote', speakers='ann-lee;jane-doe', video=VIDEO,
                                            source=f'"quote" {PAGE}', notes='a note')]}}
    [result] = run(old).talks
    assert result == {
        'id': 't' + hex8('plone-conference-2014|Keynote|Keynote'), 'event': 'plone-conference-2014',
        'type': 'Keynote', 'title': 'Keynote', 'speakers': 'ann-lee;jane-doe', 'organisations': '', 'location': '',
        'video': VIDEO,
        'sources': source_id(PAGE), 'cited_as': f'"quote" {PAGE}', 'notes': 'a note'}


def test_talks_with_the_same_event_title_and_type_get_distinct_ids():
    old = {'world-plone-day-talks': {2022: [wpd_talk('Plone 6', speakers='a'), wpd_talk('Plone 6', speakers='b'),
                                            wpd_talk('Plone 6', kind='Duplicate')]}}
    talks = run(old).talks
    base = 't' + hex8('wpd-2022-online|Plone 6|Talk')
    assert [(t['id'], t['speakers']) for t in talks] == [
        ('t' + hex8('wpd-2022-online|Plone 6|Duplicate'), ''), (base, 'a'), (base + '-2', 'b')]


def test_world_plone_day_talks_get_their_video_from_the_source():
    old = {'world-plone-day-talks': {2021: [wpd_talk('A', source=f'Recording: {VIDEO}'),
                                            wpd_talk('B', source=f'agenda: {PAGE}')]}}
    talks = by(run(old).talks, 'title')
    assert (talks['A']['video'], talks['B']['video']) == (VIDEO, '')
    assert talks['A']['cited_as'] == f'Recording: {VIDEO}'


def test_wpd_talk_without_event_row_goes_online():
    old = {'world-plone-day-event': {2025: [wpd('2025-04-10', 'Online, Italian edition', fmt='online')]},
           'world-plone-day-talks': {2025: [wpd_talk('A'), wpd_talk('B', location='Italy (Bologna)')]}}
    migrated = run(old)
    talks = by(migrated.talks, 'title')
    assert talks['A']['event'] == talks['B']['event'] == 'wpd-2025-online'
    assert (talks['A']['location'], talks['B']['location']) == ('Online', 'Italy (Bologna)')
    assert by(migrated.events, 'id')['wpd-2025-online'] == {
        'id': 'wpd-2025-online', 'kind': 'wpd', 'name': 'World Plone Day 2025, Online', 'year': '2025', 'start': '',
        'end': '', 'location': 'Online', 'format': 'online', 'level': '', 'sources': '', 'cited_as': '', 'notes': ''}
    assert migrated.unmatched_talks == [
        {'year': 2025, 'line': 3, 'title': 'B', 'location': 'Italy (Bologna)', 'event': 'wpd-2025-online'}]


def test_wpd_talks_find_the_event_of_their_city_and_country():
    old = {'world-plone-day-event': {2025: [wpd('2025-04-10', 'Bologna, Italy'), wpd('2025-04-10', 'Brasília, Brazil'),
                                            wpd('2025-04-10', 'São Paulo, Brazil')]},
           'world-plone-day-talks': {2025: [wpd_talk('A', location='Italy (Bologna)'),
                                            wpd_talk('B', location='Brazil (Brasilia)'),
                                            wpd_talk('C', location='Italy')]},
           'plone-conference': {2024: []}}
    migrated = run(old)
    talks = by(migrated.talks, 'title')
    assert talks['A']['event'] == 'wpd-2025-04-10-bologna-italy'
    assert talks['B']['event'] == 'wpd-2025-04-10-brasilia-brazil'
    assert talks['C']['event'] == 'wpd-2025-04-10-bologna-italy'  # the only event of the country
    assert [talks[t]['location'] for t in 'ABC'] == ['Italy (Bologna)', 'Brazil (Brasilia)', 'Italy']
    assert migrated.by_country_only == [
        {'year': 2025, 'line': 4, 'title': 'C', 'location': 'Italy', 'event': 'wpd-2025-04-10-bologna-italy'}]
    assert migrated.unmatched_talks == []
    assert 'wpd-2025-online' not in by(migrated.events, 'id')


def test_a_wpd_talk_of_a_country_without_an_event_goes_online():
    old = {'world-plone-day-event': {2025: [wpd('2025-04-10', 'Bologna, Italy')]},
           'world-plone-day-talks': {2025: [wpd_talk('A', location='France')]}}
    migrated = run(old)
    [result] = migrated.talks
    assert (result['event'], result['location']) == ('wpd-2025-online', 'France')
    assert migrated.unmatched_talks == [
        {'year': 2025, 'line': 2, 'title': 'A', 'location': 'France', 'event': 'wpd-2025-online'}]
    assert migrated.by_country_only == []


def test_a_wpd_talk_that_matches_two_events_is_an_error():
    berlin = wpd('2013-04-24', 'Berlin, Germany')
    old = {'world-plone-day-event': {2013: [berlin, berlin]},
           'world-plone-day-talks': {2013: [wpd_talk('A', location='Germany (Berlin)')]}}
    with pytest.raises(ValueError, match='two events'):
        run(old)


# Decision 5: trainings


def test_trainings_belong_to_the_conference_of_their_year():
    old = {'plone-conference-trainings': {2025: [
        row('title,trainers,source,notes', 'Mastering Plone', 'philip-bauer;ann-lee', PAGE, 'a note')]}}
    migrated = run(old)
    assert migrated.trainings == [{
        'id': 'r' + hex8('plone-conference-2025|Mastering Plone'), 'event': 'plone-conference-2025',
        'title': 'Mastering Plone', 'trainers': 'philip-bauer;ann-lee', 'sources': source_id(PAGE), 'cited_as': PAGE,
        'notes': 'a note'}]
    assert [e['id'] for e in migrated.events] == ['plone-conference-2025']


# Decision 6: organisers


def test_one_organiser_row_per_person_and_organisation():
    cell = f'report: {PAGE}'
    old = {'sprints': {2014: [sprint('Sprint', organisers='jane-doe;ann-lee', organisations='acme;beta',
                                     source=cell, notes='sprint note')]},
           'world-plone-day-event': {2014: [wpd('2014-04-30', 'Bonn, Germany', organisations='acme',
                                                organisers='john-roe')]},
           'plone-conference': {2014: [
               row('organisation,organisers,source,notes', 'netsight', 'matt-hamilton', MINUTES, 'conf note'),
               row('organisation,organisers,source,notes', '', 'alan-runyan;andy-mckay', PAGE, '')]}}
    migrated = run(old)
    assert [(o['event'], o['person'], o['organisation']) for o in migrated.organisers] == [
        ('plone-conference-2014', '', 'netsight'), ('plone-conference-2014', 'alan-runyan', ''),
        ('plone-conference-2014', 'andy-mckay', ''), ('plone-conference-2014', 'matt-hamilton', ''),
        ('sprint', '', 'acme'), ('sprint', '', 'beta'), ('sprint', 'ann-lee', ''), ('sprint', 'jane-doe', ''),
        ('wpd-2014-04-30-bonn-germany', '', 'acme'), ('wpd-2014-04-30-bonn-germany', 'john-roe', '')]
    rows = {(o['event'], o['person'] or o['organisation']): o for o in migrated.organisers}
    # A conference row's notes stay on its organisers; a sprint's notes stay on the sprint
    assert rows['plone-conference-2014', 'netsight'] == {
        'event': 'plone-conference-2014', 'person': '', 'organisation': 'netsight', 'sources': source_id(MINUTES),
        'cited_as': MINUTES, 'notes': 'conf note'}
    assert rows['plone-conference-2014', 'matt-hamilton']['notes'] == 'conf note'
    assert rows['sprint', 'acme'] == {'event': 'sprint', 'person': '', 'organisation': 'acme',
                                      'sources': source_id(PAGE), 'cited_as': cell, 'notes': ''}
    assert by(migrated.events, 'id')['sprint']['notes'] == 'sprint note'


def test_a_conference_row_without_organisers_is_an_error():
    with pytest.raises(ValueError, match='no organiser'):
        run({'plone-conference': {2014: [row('organisation,organisers,source,notes', '', '', PAGE, 'lost')]}})


def test_an_organiser_named_twice_for_one_event_is_an_error():
    with pytest.raises(ValueError, match='twice'):
        run({'plone-conference': {2014: [row('organisation,organisers,source,notes', 'acme', '', PAGE, ''),
                                         row('organisation,organisers,source,notes', 'acme', '', MINUTES, '')]}})


# Decision 7: roles


def test_roles_get_a_year_and_keep_the_order_of_their_files():
    old = {'board-of-directors': {2021: [row('person,role,source,notes', 'zoe', 'voting', PAGE, '')],
                                  2020: [row('person,role,source,notes', 'zoe', 'voting', PAGE, 'chair'),
                                         row('person,role,source,notes', 'ann', 'non-voting', PAGE, '')]},
           'team-leaders': {2020: [row('person,team,source,notes', 'ann', 'Classic UI Team', PAGE, '')]},
           'podcasts': {2025: [row('series,person,episodes,source,notes', 'Hands-On', 'victor', '3',
                                   f'episodes: {VIDEO} {PAGE}', '')]}}
    migrated = run(old)
    assert [(r['year'], r['person'], r['role'], r['notes']) for r in migrated.roles['board-of-directors']] == [
        ('2020', 'zoe', 'voting', 'chair'), ('2020', 'ann', 'non-voting', ''), ('2021', 'zoe', 'voting', '')]
    assert migrated.roles['team-leaders'] == [{'year': '2020', 'person': 'ann', 'team': 'Classic UI Team',
                                               'sources': source_id(PAGE), 'cited_as': PAGE, 'notes': ''}]
    assert migrated.roles['podcasts'] == [{'year': '2025', 'series': 'Hands-On', 'person': 'victor', 'episodes': '3',
                                           'sources': f'{source_id(VIDEO)};{source_id(PAGE)}',
                                           'cited_as': f'episodes: {VIDEO} {PAGE}', 'notes': ''}]
    assert migrated.roles['release-managers'] == []


def test_files_name_every_new_file_with_its_columns():
    files = run({}).files()
    assert list(files) == ['events.csv', 'talks.csv', 'trainings.csv', 'organisers.csv', 'board-of-directors.csv',
                           'team-leaders.csv', 'release-managers.csv', 'podcasts.csv']
    assert files['events.csv'][0] == ('id', 'kind', 'name', 'year', 'start', 'end', 'location', 'format', 'level',
                                      'sources', 'cited_as', 'notes')
    assert files['organisers.csv'][0] == ('event', 'person', 'organisation', 'sources', 'cited_as', 'notes')


# The command


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields.split(','), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def repo(tmp_repo):
    community = paths.COMMUNITY
    write_csv(community / '2014-sprints.csv', SPRINT_FIELDS, [sprint('Sprint', organisers='ann-lee')])
    write_csv(community / '2025-world-plone-day-talks.csv', WPD_TALK_FIELDS,
              [wpd_talk('A', location='Italy (Bologna)', source=GONE)])
    (community / 'community-recognition-levels.csv').write_text('levels\n', encoding='utf-8')
    (community / 'community-recognition-points.csv').write_text('points\n', encoding='utf-8')
    archive = tmp_repo / migrate_community.ARCHIVE
    archive.mkdir(parents=True)
    page = source_id(PAGE)
    paths.SOURCES.write_text('id,kind,title,date,url,archive_url,fetched,notes\n'
                             f'{page},page,Report,2026-10-25,{PAGE},,2026-10-25T10:00:00Z,\n', encoding='utf-8')
    (paths.EXCERPTS_DIR / f'{page}.md').write_text('A report.\n', encoding='utf-8')
    (archive / 'capture-results.jsonl').write_text(
        f'{{"url": "{PAGE}", "source_id": "{page}", "error": null}}\n', encoding='utf-8')
    (archive / 'videos-capture-results.jsonl').write_text(
        f'{{"url": "{GONE}", "source_id": null, "error": null}}\n', encoding='utf-8')
    (archive / 'worklist.jsonl').write_text(f'{{"url": "{PAGE}", "kind": null}}\n', encoding='utf-8')
    (archive / 'videos-worklist.jsonl').write_text(f'{{"url": "{GONE}", "kind": "video"}}\n', encoding='utf-8')
    return tmp_repo


def test_the_dry_run_prints_a_summary_and_writes_nothing(repo, capsys):
    before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*'))
    assert migrate_community.main([]) == 0
    out = capsys.readouterr().out
    assert 'events.csv: 2' in out  # the sprint and the online World Plone Day of 2025
    assert 'events: sprint 1, wpd 1' in out
    assert '2025 line 2: "A" at Italy (Bologna) -> wpd-2025-online' in out
    assert 'uncaptured sources created: 1 (nothing found 1)' in out
    assert sorted(p.relative_to(repo).as_posix() for p in repo.rglob('*')) == before


def test_write_replaces_the_old_folder(repo):
    assert migrate_community.main(['--write']) == 0
    new = migrate_community.NEW_FOLDER
    assert sorted(p.name for p in new.iterdir()) == [
        'board-of-directors.csv', 'community-recognition-levels.csv', 'community-recognition-points.csv',
        'events.csv', 'organisers.csv', 'podcasts.csv', 'release-managers.csv', 'talks.csv', 'team-leaders.csv',
        'trainings.csv']
    assert not paths.COMMUNITY.exists()
    assert (new / 'community-recognition-levels.csv').read_text(encoding='utf-8') == 'levels\n'
    with open(new / 'organisers.csv', newline='', encoding='utf-8') as f:
        assert list(csv.DictReader(f)) == [{'event': 'sprint', 'person': 'ann-lee', 'organisation': '',
                                            'sources': source_id(PAGE), 'cited_as': PAGE, 'notes': ''}]
    gone = source_id(GONE)
    assert f'{gone},video,{GONE},2026-10-25,{GONE},,' in paths.SOURCES.read_text(encoding='utf-8')
    assert (paths.EXCERPTS_DIR / f'{gone}.md').read_text(encoding='utf-8') == (
        'not captured on 2026-10-25: nothing found\n')
