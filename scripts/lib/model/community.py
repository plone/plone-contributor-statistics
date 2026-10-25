"""Community roles, events and rows from the curated community files, read in one place.

The community data is one file per kind in curated/community/: the events (conferences, symposia, World Plone Day
events, sprints), the talks, trainings and organisers that point to them, and the roles with their year.

A role is one person in one role, with the row it comes from and its public record. An event is a gathering:
see EVENT_KINDS for what counts as one. An item is a row as such, for code that needs more than the roles. The
readers present the rows of a year by the kinds of the yearly files the data had before the events (#139):
`items(2025, 'sprints')` gives the sprints of 2025 with the columns of a sprints file, its organisers from the
organisers file. People and organisations are ids from the registers.

The rows of a year come in the order of the files, and the organisers of an event in the order of the organisers
file. The order decides credit: of the strategic sprints of a year, the first one that names an organisation counts
for it, with that sprint's split, and only the first four World Plone Day talks of an organisation count (see
scripts/report/generate_community_recognition_report.py). Reordering the rows of a year can change the points.
"""

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.schema import read_rows, split_set

# File kind -> (label, detail column): the people of a row are those of its item
ROLE_KINDS = {
    'board-of-directors': ('Board', None),
    'team-leaders': ('Team lead', 'team'),
    'release-managers': ('Release manager', None),
    'plone-conference-trainings': ('Trainer', 'title'),
    'world-plone-day-talks': ('Speaker', 'title'),
    'conference-talks': ('Speaker', 'title'),
    'sprints': ('Sprint organiser', 'sprint'),
    'podcasts': ('Podcast', 'series'),
    'plone-conference': ('Conference organiser', None),
}
# The column that names a row of a roles file other than `person`
KEY_COLUMNS = {'podcasts': 'series'}
# Only these World Plone Day videos are talks (#119)
TALK_TYPES = ('Talk',)
# World Plone Day events count when they were held in person (#118)
IN_PERSON = ('in person', 'hybrid')
# A podcast host counts for recognition from this many episodes on
MIN_EPISODES = 5

# The files of the community folder, by what they hold
EVENTS = paths.EVENTS.name
TALKS = paths.TALKS.name
TRAININGS = paths.TRAININGS.name
ORGANISERS = paths.ORGANISERS.name
# The kinds of the roles files, each a file of its own with a `year` column
ROLE_FILES = {kind: f'{kind}.csv' for kind in ('board-of-directors', 'team-leaders', 'release-managers', 'podcasts')}
# The online edition of a World Plone Day year that holds the online talks; it was no row of a yearly file
ONLINE_EDITION = 'wpd-{year}-online'


def recognition_levels(path=None):
    """The rows of the recognition levels file (default: the curated one), typed by its schema."""
    return read_rows(paths.RECOGNITION_LEVELS if path is None else path)


@dataclass(frozen=True)
class Role:
    kind: str
    year: int
    person: str
    label: str
    detail: str
    file: str
    line: int
    source: str
    notes: str


@dataclass(frozen=True)
class Talk:
    kind: str
    year: int
    person: str
    title: str
    event: str
    video: str | None
    file: str
    line: int
    source: str


@dataclass(frozen=True)
class Event:
    kind: str
    year: int
    name: str
    organisations: tuple
    organisers: tuple
    sources: tuple
    level: str
    file: str
    line: int


@dataclass(frozen=True)
class Item:
    kind: str
    year: int
    key: str
    people: tuple
    organisations: tuple
    file: str
    line: int
    source: str
    notes: str
    fields: dict


@dataclass(frozen=True)
class _Row:
    file: str
    line: int
    cells: dict


# Tables already read: (path, content) -> rows; every year reads the same files
_TABLES = {}


def _table(folder, name):
    """The rows of a file of the folder as _Row, typed by its schema; none when the file is missing.

    A column of the schema that the file lacks is a KeyError naming the file. The header is line 1.
    """
    path = Path(folder) / name
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return []
    key = (str(path), content)
    if key not in _TABLES:
        header = next(csv.reader(io.StringIO(content.decode('utf-8'))), [])
        rows = read_rows(path)
        if rows:
            missing = [column for column in rows[0] if column not in header]
            if missing:
                raise KeyError(f'{path}: column {missing[0]} is missing')
        _TABLES[key] = [_Row(str(path), line, row) for line, row in enumerate(rows, start=2)]
    return _TABLES[key]


def _text(value):
    return (value or '').strip()


def _unique(values):
    return tuple(dict.fromkeys(value for value in values if value))


def _joined(values):
    return ';'.join(values) or None


def community_folder(community_dir=None):
    """The folder of the community files: the given one, else the curated folder."""
    return Path(community_dir) if community_dir is not None else paths.COMMUNITY


def _events(folder, year, kind):
    """The rows of the events file of a kind and year, in the order of the file."""
    return [row for row in _table(folder, EVENTS) if row.cells['kind'] == kind and row.cells['year'] == year]


def _event_kinds(folder):
    """{event id: (kind, year, name)} of the events file."""
    return {row.cells['id']: (row.cells['kind'], row.cells['year'], row.cells['name'])
            for row in _table(folder, EVENTS)}


def _organisers(folder, event_id):
    """The rows of the organisers file of an event, in the order of the file."""
    return [row for row in _table(folder, ORGANISERS) if row.cells['event'] == event_id]


def _item(kind, year, row, key, people, organisations, fields):
    """An Item of a row; its source is the old source cell, `cited_as`, and its fields those of the old kind."""
    source = _text(row.cells['cited_as'])
    notes = _text(row.cells['notes'])
    return Item(kind=kind, year=year, key=_text(key), people=tuple(people), organisations=tuple(organisations),
                file=row.file, line=row.line, source=source, notes=notes,
                fields={**fields, 'source': row.cells['cited_as'], 'notes': row.cells['notes']})


def _role_items(folder, year, kind):
    key_column = KEY_COLUMNS.get(kind, 'person')
    found = []
    for row in _table(folder, ROLE_FILES[kind]):
        if row.cells['year'] != year:
            continue
        fields = {name: value for name, value in row.cells.items()
                  if name not in ('year', 'sources', 'cited_as', 'notes')}
        people = (row.cells['person'],) if row.cells['person'] else ()
        found.append(_item(kind, year, row, row.cells[key_column], people, (), fields))
    return found


def _talk_rows(folder, year, event_kinds):
    """The rows of the talks file whose event is of one of the kinds and of the year, in the order of the file."""
    events = _event_kinds(folder)
    return [(row, events[row.cells['event']]) for row in _table(folder, TALKS)
            if row.cells['event'] in events and events[row.cells['event']][0] in event_kinds
            and events[row.cells['event']][1] == year]


def _conference_talk_items(folder, year):
    found = []
    for row, (kind, _, name) in _talk_rows(folder, year, ('conference', 'symposium')):
        c = row.cells
        fields = {'event': name, 'scope': 'global' if kind == 'conference' else 'regional', 'type': c['type'],
                  'title': c['title'], 'speakers': c['speakers'], 'organisations': c['organisations'],
                  'video': c['video']}
        found.append(_item('conference-talks', year, row, c['title'], split_set(c['speakers']),
                           split_set(c['organisations']), fields))
    return found


def _world_plone_day_talk_items(folder, year):
    found = []
    for row, _ in _talk_rows(folder, year, ('wpd',)):
        c = row.cells
        fields = {'title': c['title'], 'speakers': c['speakers'], 'organisations': c['organisations'],
                  'type': c['type'], 'location': c['location'], 'video': c['video']}
        found.append(_item('world-plone-day-talks', year, row, c['title'], split_set(c['speakers']),
                           split_set(c['organisations']), fields))
    return found


def _training_items(folder, year):
    events = _event_kinds(folder)
    found = []
    for row in _table(folder, TRAININGS):
        kind, event_year, _ = events.get(row.cells['event'], (None, None, None))
        if kind != 'conference' or event_year != year:
            continue
        c = row.cells
        fields = {'title': c['title'], 'trainers': c['trainers']}
        found.append(_item('plone-conference-trainings', year, row, c['title'], split_set(c['trainers']), (), fields))
    return found


def _event_organisers(folder, event_id):
    """(people, organisations) of an event, each in the order of the organisers file."""
    rows = _organisers(folder, event_id)
    return (tuple(r.cells['person'] for r in rows if r.cells['person']),
            tuple(r.cells['organisation'] for r in rows if r.cells['organisation']))


def _sprint_items(folder, year):
    found = []
    for row in _events(folder, year, 'sprint'):
        c = row.cells
        people, organisations = _event_organisers(folder, c['id'])
        fields = {'sprint': c['name'], 'start': c['start'], 'end': c['end'], 'location': c['location'],
                  'organisers': _joined(people), 'organisations': _joined(organisations), 'level': c['level']}
        found.append(_item('sprints', year, row, c['name'], people, organisations, fields))
    return found


def _day(row):
    """The start of a World Plone Day event as a date; ValueError naming the event when it is no full day."""
    start = row.cells['start']
    if not start:
        return None
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start):
            raise ValueError(start)
        return date.fromisoformat(start)
    except ValueError:
        raise ValueError(f'{row.file}:{row.line}: the World Plone Day event {row.cells["id"]} starts on "{start}", '
                         f'not on a day (YYYY-MM-DD)') from None


def _world_plone_day_event_items(folder, year):
    found = []
    for row in _events(folder, year, 'wpd'):
        c = row.cells
        if c['id'] == ONLINE_EDITION.format(year=year):
            continue  # it holds the online talks of the year; the yearly files had no row for it
        people, organisations = _event_organisers(folder, c['id'])
        fields = {'date': _day(row), 'location': c['location'],
                  'format': c['format'], 'organisations': _joined(organisations), 'organisers': _joined(people)}
        found.append(_item('world-plone-day-event', year, row, c['location'], people, organisations, fields))
    return found


def _conference_items(folder, year):
    """One item per organiser row of the Plone Conference of the year: an organisation or a person."""
    found = []
    for event in _events(folder, year, 'conference'):
        for row in _organisers(folder, event.cells['id']):
            person, organisation = row.cells['person'], row.cells['organisation']
            fields = {'organisation': organisation, 'organisers': person}
            found.append(_item('plone-conference', year, row, organisation, (person,) if person else (),
                               (organisation,) if organisation else (), fields))
    return found


# How the rows of an old file kind are found in the new files
_ITEM_READERS = {
    'conference-talks': _conference_talk_items,
    'world-plone-day-talks': _world_plone_day_talk_items,
    'plone-conference-trainings': _training_items,
    'sprints': _sprint_items,
    'world-plone-day-event': _world_plone_day_event_items,
    'plone-conference': _conference_items,
}


def items(year, kind, community_dir=paths.COMMUNITY):
    """Every row of a kind and year, with the sets split; talks of every type are included.

    The kind is that of the yearly files: board-of-directors, team-leaders, release-managers, podcasts,
    plone-conference-trainings, world-plone-day-talks, conference-talks, sprints, plone-conference,
    world-plone-day-event. An unknown kind is a KeyError.
    """
    if kind in ROLE_FILES:
        return _role_items(community_dir, year, kind)
    return _ITEM_READERS[kind](community_dir, year)


def community_years(community_dir=paths.COMMUNITY):
    """The years that have community rows of any kind, sorted."""
    found = {row.cells['year'] for name in (EVENTS, *ROLE_FILES.values()) for row in _table(community_dir, name)}
    return sorted(found)


def roles(year, community_dir=paths.COMMUNITY):
    """One Role per person and role in the curated files of the year."""
    found = []
    for kind, (label, detail_column) in ROLE_KINDS.items():
        for item in items(year, kind, community_dir):
            if kind == 'world-plone-day-talks' and item.fields['type'] not in TALK_TYPES:
                continue
            detail = _text(item.fields[detail_column]) if detail_column else ''
            found.extend(Role(kind=kind, year=year, person=person, label=label, detail=detail, file=item.file,
                              line=item.line, source=item.source, notes=item.notes) for person in item.people)
    return found


def talks(year, community_dir=paths.COMMUNITY):
    """One Talk per speaker and talk of the year: the conference talks, then the World Plone Day talks."""
    found = []
    for item in items(year, 'conference-talks', community_dir):
        found.extend(Talk(kind=item.kind, year=year, person=person, title=item.key, event=_text(item.fields['event']),
                          video=_text(item.fields['video']) or None, file=item.file, line=item.line,
                          source=item.source) for person in item.people)
    for item in items(year, 'world-plone-day-talks', community_dir):
        if item.fields['type'] not in TALK_TYPES:
            continue
        found.extend(Talk(kind=item.kind, year=year, person=person, title=item.key, event=f'World Plone Day {year}',
                          video=_text(item.fields['video']) or None, file=item.file, line=item.line,
                          source=item.source) for person in item.people)
    return found


def _conference(folder, year):
    # A Plone Conference is an event of the year when its organisers are recorded
    found = []
    for event in _events(folder, year, 'conference'):
        rows = _organisers(folder, event.cells['id'])
        if rows:
            found.append(Event('plone-conference', year, event.cells['name'],
                               _unique(r.cells['organisation'] for r in rows), _unique(r.cells['person'] for r in rows),
                               _unique(_text(r.cells['cited_as']) for r in rows), '', event.file, event.line))
    return found


def _sprints(folder, year):
    # One row per sprint: strategic, community, or without a level (before 2011)
    return [Event('sprints', year, i.key, i.organisations, i.people, _unique([i.source]), _text(i.fields['level']),
                  i.file, i.line) for i in _sprint_items(folder, year)]


def _world_plone_day(folder, year):
    # One row per local event; online editions are recorded but are no gatherings
    return [Event('world-plone-day-event', year, f'World Plone Day {year}, {i.key}', i.organisations, i.people,
                  _unique([i.source]), '', i.file, i.line)
            for i in _world_plone_day_event_items(folder, year) if _text(i.fields['format']) in IN_PERSON]


# What counts as an event, by the kind of the yearly file. Add new kinds here, for example community sprints.
EVENT_RULES = {
    'plone-conference': _conference,
    'sprints': _sprints,
    'world-plone-day-event': _world_plone_day,
}
EVENT_KINDS = tuple(EVENT_RULES)


def events(year, community_dir=paths.COMMUNITY):
    """The events of the year, in the order of EVENT_KINDS."""
    found = []
    for rule in EVENT_RULES.values():
        found.extend(rule(community_dir, year))
    return found
