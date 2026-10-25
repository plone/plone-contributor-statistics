"""The audit of the community migration (plan 3b): offline, on a small fixture, with one mutation per loss."""

import copy

import pytest

from scripts.lib.model.sources import source_id
from scripts.tools import audit_community, migrate_community
from scripts.tools.audit_community import audit_migration, read_old_at, read_written, report
from scripts.tools.migrate_community import migrate

PAGE = 'https://plone.org/events/sprint-report'
MINUTES = 'https://plone.org/foundation/minutes'
VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'
URLS = (PAGE, MINUTES, VIDEO)


def row(fields, *values):
    return dict(zip(fields.split(','), values))


OLD = {
    'sprints': {2014: [row('sprint,start,end,location,organisers,organisations,level,source,notes',
                           'Alpine City Sprint', '2014-01-01', '2014-01-05', 'Innsbruck', 'jane-doe;john-roe',
                           'Acme', 'strategic', PAGE, 'a note')]},
    'world-plone-day-event': {2014: [row('date,location,format,organisations,organisers,source,notes',
                                         '2014-04-12', 'Bologna, Italy', 'in person', 'Acme', 'jane-doe', PAGE,
                                         '')]},
    'world-plone-day-talks': {2014: [row('title,speakers,organisations,type,location,source,notes',
                                         'Plone in Bologna', 'Jane Doe', 'Acme', 'Talk', 'Italy (Bologna)',
                                         f'{VIDEO} and {PAGE}', ''),
                                     row('title,speakers,organisations,type,location,source,notes',
                                         'Online talk', 'John Roe', '', 'Talk', 'Online', 'no address', '')]},
    'conference-talks': {2014: [row('event,scope,type,title,speakers,organisations,video,source,notes',
                                    'Plone Conference 2014', 'global', 'Keynote', 'The Keynote', 'Jane Doe', 'Acme',
                                    VIDEO, PAGE, 'n'),
                                row('event,scope,type,title,speakers,organisations,video,source,notes',
                                    'Plone Symposium', 'regional', 'Talk', 'Regional', 'John Roe', '', '', PAGE,
                                    '')]},
    'plone-conference': {2014: [row('organisation,organisers,source,notes', 'Acme', 'jane-doe;john-roe', MINUTES,
                                    'file note')]},
    'plone-conference-trainings': {2014: [row('title,trainers,source,notes', 'Training', 'Jane Doe', PAGE, '')]},
    'board-of-directors': {2014: [row('person,role,source,notes', 'jane-doe', 'President', MINUTES, ''),
                                  row('person,role,source,notes', 'john-roe', 'Member', MINUTES, '')]},
    'team-leaders': {2014: [row('person,team,source,notes', 'jane-doe', 'Docs', PAGE, '')]},
    'release-managers': {2014: [row('person,source,notes', 'jane-doe', PAGE, '')]},
    'podcasts': {2014: [row('series,person,episodes,source,notes', 'Show', 'jane-doe', '3', PAGE, '')]},
}
RESULTS = [{'url': url, 'source_id': source_id(url), 'error': None} for url in URLS]
KNOWN = {source_id(url) for url in URLS}
REGISTER = {sid: {'id': sid, 'kind': 'page'} for sid in KNOWN}


def migrated(old=None):
    return migrate(copy.deepcopy(old or OLD), RESULTS, REGISTER)


def losses(old=None, new=None, known=KNOWN):
    return audit_migration(old or copy.deepcopy(OLD), new or migrated(), RESULTS, known)


def test_a_lossless_migration_has_no_losses_and_counts_the_rows():
    audit = losses()
    assert audit.losses == []
    assert audit.counts['sprints'] == (1, 1)
    assert audit.counts['world-plone-day-talks'] == (2, 2)
    assert audit.counts['organisers'] == (8, 8)  # sprint 3, World Plone Day 2, conference 3
    assert audit.counts['board-of-directors'] == (2, 2)
    assert 'losses: 0' in report(audit)


@pytest.mark.parametrize('field', ['events', 'talks', 'trainings', 'organisers'])
def test_a_dropped_row_is_a_loss(field):
    new = migrated()
    getattr(new, field).pop(0)
    assert losses(new=new).losses


def test_a_dropped_role_is_a_loss():
    new = migrated()
    new.roles['board-of-directors'].pop()
    assert any(loss.startswith('board-of-directors: lost') for loss in losses(new=new).losses)


@pytest.mark.parametrize('field,kind', [('title', 'conference-talks'), ('video', 'conference-talks'),
                                        ('cited_as', 'conference-talks'), ('notes', 'conference-talks'),
                                        ('speakers', 'conference-talks')])
def test_a_changed_cell_of_a_talk_is_a_loss(field, kind):
    new = migrated()
    talk = next(t for t in new.talks if t['type'] == 'Keynote')
    talk[field] = talk[field] + ' changed'
    assert any(loss.startswith(f'{kind}:') for loss in losses(new=new).losses)


def test_a_lost_location_of_a_world_plone_day_talk_is_a_loss():
    new = migrated()
    next(t for t in new.talks if t['title'] == 'Plone in Bologna')['location'] = ''
    assert any(loss.startswith('world-plone-day-talks:') for loss in losses(new=new).losses)


@pytest.mark.parametrize('field', ['name', 'start', 'end', 'location', 'level', 'notes', 'cited_as'])
def test_a_changed_cell_of_a_sprint_is_a_loss(field):
    new = migrated()
    next(e for e in new.events if e['kind'] == 'sprint')[field] += 'x'
    assert any(loss.startswith('sprints:') for loss in losses(new=new).losses)


def test_a_changed_cell_of_a_world_plone_day_event_is_a_loss():
    new = migrated()
    next(e for e in new.events if e['id'].startswith('wpd-2014-04'))['format'] = 'online'
    assert any(loss.startswith('world-plone-day-event:') for loss in losses(new=new).losses)


def test_a_changed_training_and_role_are_losses():
    new = migrated()
    new.trainings[0]['trainers'] = 'Someone else'
    new.roles['podcasts'][0]['episodes'] = '4'
    found = losses(new=new).losses
    assert any(loss.startswith('plone-conference-trainings:') for loss in found)
    assert any(loss.startswith('podcasts:') for loss in found)


def test_roles_in_another_order_are_a_loss():
    new = migrated()
    new.roles['board-of-directors'].reverse()
    assert any('order' in loss for loss in losses(new=new).losses)


def test_a_dropped_organiser_element_is_a_loss():
    new = migrated()
    sprint = next(e for e in new.events if e['kind'] == 'sprint')
    new.organisers.remove(next(o for o in new.organisers if o['event'] == sprint['id'] and o['person'] == 'john-roe'))
    found = losses(new=new).losses
    assert any(loss.startswith('sprints:') for loss in found)
    assert any(loss.startswith('organisers:') for loss in found)


def test_a_dropped_conference_organiser_is_a_loss():
    new = migrated()
    new.organisers.remove(next(o for o in new.organisers if o['organisation'] == 'Acme'
                               and o['event'] == 'plone-conference-2014'))
    assert any(loss.startswith('plone-conference:') for loss in losses(new=new).losses)


def test_an_organiser_row_with_both_person_and_organisation_is_reported():
    new = migrated()
    new.organisers[0]['person'], new.organisers[0]['organisation'] = 'jane-doe', 'Acme'
    assert any('not exactly one' in loss for loss in losses(new=new).losses)


def test_an_organiser_citing_differently_than_its_event_is_reported():
    new = migrated()
    sprint = next(e for e in new.events if e['kind'] == 'sprint')
    next(o for o in new.organisers if o['event'] == sprint['id'])['cited_as'] = 'other'
    assert any('cites differently' in loss for loss in losses(new=new).losses)


def test_a_dropped_url_id_is_a_loss():
    new = migrated()
    talk = next(t for t in new.talks if t['title'] == 'Plone in Bologna')
    talk['sources'] = source_id(VIDEO)
    assert any(loss.startswith('sources:') and PAGE in loss for loss in losses(new=new).losses)


def test_an_id_outside_the_register_is_a_loss():
    new = migrated()
    assert any('neither in the register' in loss for loss in losses(new=new, known=set()).losses)


def test_a_duplicate_id_is_a_loss():
    new = migrated()
    new.talks[1]['id'] = new.talks[0]['id']
    assert any('is used 2 times' in loss for loss in losses(new=new).losses)


def test_an_unknown_old_column_is_a_loss():
    old = copy.deepcopy(OLD)
    old['team-leaders'][2014][0]['extra'] = 'x'
    assert any('not audited' in loss for loss in losses(old=old).losses)


def test_the_main_exits_with_1_on_a_loss_and_0_without(monkeypatch, capsys):
    monkeypatch.setattr(audit_community, 'read_old_at', lambda commit: copy.deepcopy(OLD))
    monkeypatch.setattr(audit_community, 'load_sources', lambda: {})
    monkeypatch.setattr(migrate_community, '_read_jsonl', lambda path: [])
    monkeypatch.setattr(migrate_community, 'migrate', lambda *a, **k: migrated())
    monkeypatch.setattr(audit_community, 'audit_migration', lambda *a: losses(new=_dropped()))
    assert audit_community.main([]) == 1
    assert 'losses: 1' in capsys.readouterr().out
    monkeypatch.setattr(audit_community, 'audit_migration', lambda *a: losses())
    assert audit_community.main([]) == 0


def _dropped():
    new = migrated()
    new.talks.pop()
    return new


def test_the_written_files_are_read_back(tmp_path):
    new = migrated()
    for name, (fields, rows) in new.files().items():
        migrate_community._write_csv(tmp_path / name, fields, rows)
    assert losses(new=read_written(tmp_path)).losses == []


def test_the_old_files_are_read_from_git():
    old = read_old_at(audit_community.BASE)
    assert {'sprints', 'conference-talks', 'podcasts'} <= set(old)
    assert 'community-recognition-levels' not in old
