"""Community roles and events from the curated community files, read in one place.

A record is one person in one role, with the row it comes from and its public
record. An event is a gathering: see EVENT_KINDS for what counts as one.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from scripts.lib import paths

# File kind -> (label, person column, handle column, detail column)
ROLE_KINDS = {
    'board-of-directors': ('Board', 'Name', None, None),
    'team-leaders': ('Team lead', 'Name', None, 'Team'),
    'release-managers': ('Release manager', 'Name', 'Github', None),
    'plone-conference-trainings': ('Trainer', 'Trainer(s)', 'GitHub Handle(s)', 'Title'),
    'world-plone-day-talks': ('Talk', 'Speaker(s)', None, 'Video Title'),
    'strategic-sprints': ('Sprint organiser', 'Organiser/Host', None, 'Sprint'),
    'podcasts': ('Podcast', 'Name', None, None),
    'plone-conference': ('Conference organiser', 'Organiser(s)', None, None),
}
# Only these World Plone Day videos are talks (#119)
TALK_TYPES = ('Talk',)


@dataclass(frozen=True)
class Record:
    kind: str
    year: int
    person: str
    handle: str
    organisation: str
    label: str
    detail: str
    file: str
    line: int
    source: str


@dataclass(frozen=True)
class Event:
    kind: str
    year: int
    name: str
    organisations: tuple
    sources: tuple


def split(value):
    return [part.strip() for part in (value or '').split(';') if part.strip()]


def _rows(community_dir, year, kind):
    path = Path(community_dir) / f'{year}-{kind}.csv'
    if not path.exists():
        return path, []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return path, [(reader.line_num, row) for row in reader]


def _source(kind, row):
    if kind == 'world-plone-day-talks':
        video = (row.get('YouTube ID') or '').strip()
        return f'https://www.youtube.com/watch?v={video}' if video else ''
    return (row.get('Source') or row.get('Reference') or '').strip()


def community_records(year, community_dir=paths.COMMUNITY):
    """One Record per person and role in the curated files of the year."""
    records = []
    for kind, (label, person_column, handle_column, detail_column) in ROLE_KINDS.items():
        path, rows = _rows(community_dir, year, kind)
        for line, row in rows:
            if person_column not in row:
                continue
            if kind == 'world-plone-day-talks' and row.get('Type', '').strip() not in TALK_TYPES:
                continue
            persons = split(row[person_column])
            handles = split(row.get(handle_column, '')) if handle_column else []
            organisations = split(row.get('Organisation', ''))
            if not persons and organisations:
                # Work of an organisation without a named person: counts for the organisation only
                persons = ['']
            for index, person in enumerate(persons):
                records.append(Record(
                    kind=kind, year=year, person=person,
                    handle=handles[index] if len(handles) == len(persons) else '',
                    organisation=(organisations[index] if len(organisations) == len(persons)
                                  else ';'.join(organisations)),
                    label=label,
                    detail=(row.get(detail_column) or '').strip() if detail_column else '',
                    file=str(path), line=line, source=_source(kind, row)))
    return records


def _unique(values):
    return tuple(dict.fromkeys(value for value in values if value))


def _conference(year, rows):
    if not rows:
        return []
    return [Event('plone-conference', year, f'Plone Conference {year}',
                  _unique(o for _, row in rows for o in split(row['Organisation'])),
                  _unique(_source('plone-conference', row) for _, row in rows))]


def _strategic_sprints(year, rows):
    sprints = {}
    for _, row in rows:
        sprints.setdefault(row['Sprint'].strip(), []).append(row)
    return [Event('strategic-sprints', year, name,
                  _unique(o for row in group for o in split(row['Organisation'])),
                  _unique(_source('strategic-sprints', row) for row in group))
            for name, group in sprints.items()]


def _world_plone_day(year, rows):
    if not rows:
        return []
    return [Event('world-plone-day-event', year, f'World Plone Day {year}',
                  _unique(o for _, row in rows for o in split(row['Organisation'])),
                  _unique(_source('world-plone-day-event', row) for _, row in rows))]


# What counts as an event, per file kind. Add new kinds here, for example community sprints.
EVENT_RULES = {
    'plone-conference': _conference,
    'strategic-sprints': _strategic_sprints,
    'world-plone-day-event': _world_plone_day,
}
EVENT_KINDS = tuple(EVENT_RULES)


def events(year, community_dir=paths.COMMUNITY):
    """The events of the year, in the order of EVENT_KINDS."""
    found = []
    for kind, rule in EVENT_RULES.items():
        found.extend(rule(year, _rows(community_dir, year, kind)[1]))
    return found
