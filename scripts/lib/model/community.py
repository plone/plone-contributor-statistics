"""Community roles, events and rows from the curated community files, read in one place.

A role is one person in one role, with the row it comes from and its public record. An event is a gathering:
see EVENT_KINDS for what counts as one. An item is a row as such, for code that needs more than the roles.
People and organisations are ids from the registers.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.schema import read_rows, split_set

# File kind -> (label, person column or set column, detail column)
ROLE_KINDS = {
    'board-of-directors': ('Board', 'person', None),
    'team-leaders': ('Team lead', 'person', 'team'),
    'release-managers': ('Release manager', 'person', None),
    'plone-conference-trainings': ('Trainer', 'trainers', 'title'),
    'world-plone-day-talks': ('Talk', 'speakers', 'title'),
    'sprints': ('Sprint organiser', 'organisers', 'sprint'),
    'podcasts': ('Podcast', 'person', 'series'),
    'plone-conference': ('Conference organiser', 'organisers', None),
}
# Columns that hold a set of ids; the others hold a single id
SET_COLUMNS = ('trainers', 'speakers', 'organisers')
# The column that names the people of a kind that is no role kind
EXTRA_PEOPLE_COLUMNS = {'world-plone-day-event': 'organisers'}
# The column that names a row of a kind; the per-person kinds are named by `person`
KEY_COLUMNS = {
    'plone-conference-trainings': 'title',
    'world-plone-day-talks': 'title',
    'sprints': 'sprint',
    'podcasts': 'series',
    'plone-conference': 'organisation',
    'world-plone-day-event': 'location',
}
# Only these World Plone Day videos are talks (#119)
TALK_TYPES = ('Talk',)
# World Plone Day events count when they were held in person (#118)
IN_PERSON = ('in person', 'hybrid')
# A podcast host counts for recognition from this many episodes on
MIN_EPISODES = 5


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


def _rows(community_dir, year, kind):
    """(path, [(line, row)]) of a file; no rows when the file is missing, KeyError for a missing column."""
    path = Path(community_dir) / f'{year}-{kind}.csv'
    if not path.is_file():
        return path, []
    with open(path, newline='', encoding='utf-8') as f:
        header = next(csv.reader(f), [])
    rows = read_rows(path)
    if rows:
        missing = [name for name in rows[0] if name not in header]
        if missing:
            raise KeyError(f'{path}: column {missing[0]} is missing')
    return path, list(enumerate(rows, start=2))  # the header is line 1


def _text(value):
    return (value or '').strip()


def _unique(values):
    return tuple(dict.fromkeys(value for value in values if value))


def _people(kind, row):
    column = ROLE_KINDS[kind][1] if kind in ROLE_KINDS else EXTRA_PEOPLE_COLUMNS.get(kind, 'person')
    if column in SET_COLUMNS:
        return split_set(row[column])
    return (row[column],) if row[column] else ()


def community_folder(community_dir=None):
    """The folder of the community files: the given one, else the curated folder."""
    return Path(community_dir) if community_dir is not None else paths.COMMUNITY


def items(year, kind, community_dir=paths.COMMUNITY):
    """Every row of a kind and year, with the sets split; talks of every type are included."""
    path, rows = _rows(community_dir, year, kind)
    key_column = KEY_COLUMNS.get(kind, 'person')
    found = []
    for line, row in rows:
        if kind == 'plone-conference':
            organisations = (row['organisation'],)
        else:
            organisations = split_set(row['organisations']) if 'organisations' in row else ()
        found.append(Item(kind=kind, year=year, key=_text(row[key_column]), people=_people(kind, row),
                          organisations=organisations, file=str(path), line=line,
                          source=_text(row['source']), notes=_text(row['notes']), fields=row))
    return found


def roles(year, community_dir=paths.COMMUNITY):
    """One Role per person and role in the curated files of the year."""
    found = []
    for kind, (label, _, detail_column) in ROLE_KINDS.items():
        for item in items(year, kind, community_dir):
            if kind == 'world-plone-day-talks' and item.fields['type'] not in TALK_TYPES:
                continue
            detail = _text(item.fields[detail_column]) if detail_column else ''
            found.extend(Role(kind=kind, year=year, person=person, label=label, detail=detail, file=item.file,
                              line=item.line, source=item.source, notes=item.notes) for person in item.people)
    return found


def _conference(year, rows):
    if not rows:
        return []
    return [Event('plone-conference', year, f'Plone Conference {year}',
                  _unique(i.organisations[0] for i in rows), _unique(p for i in rows for p in i.people),
                  _unique(i.source for i in rows), '', rows[0].file, rows[0].line)]


def _sprints(year, rows):
    # One row per sprint: strategic, community, or without a level (before 2011)
    return [Event('sprints', year, i.key, i.organisations, i.people, _unique([i.source]),
                  _text(i.fields['level']), i.file, i.line) for i in rows]


def _world_plone_day(year, rows):
    # One row per local event; online editions are recorded but are no gatherings
    return [Event('world-plone-day-event', year, f'World Plone Day {year}, {i.key}', i.organisations, i.people,
                  _unique([i.source]), '', i.file, i.line)
            for i in rows if _text(i.fields['format']) in IN_PERSON]


# What counts as an event, per file kind. Add new kinds here, for example community sprints.
EVENT_RULES = {
    'plone-conference': _conference,
    'sprints': _sprints,
    'world-plone-day-event': _world_plone_day,
}
EVENT_KINDS = tuple(EVENT_RULES)


def events(year, community_dir=paths.COMMUNITY):
    """The events of the year, in the order of EVENT_KINDS."""
    found = []
    for kind, rule in EVENT_RULES.items():
        found.extend(rule(year, items(year, kind, community_dir)))
    return found
