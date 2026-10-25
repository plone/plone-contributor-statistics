#!/usr/bin/env python3
"""Prove that the migration of the community files (plan 3b) loses nothing.

Migration code for plan 3b, archived to archive/migration-to-events/ after its one use, with
scripts/tools/migrate_community.py. It reads the old yearly files at a git commit (the base of the plan) with plain
csv, since their schemas go away with the switch, and compares them with the new rows: from the migration in
memory (the default, before the switch) or from the written curated/community/ files (`--written`, after it).

Per kind (sprints, World Plone Day events, Plone Conference organisers, conference talks, World Plone Day talks,
trainings and the four roles) every cell of every old row must be in the new rows: titles, types, videos, levels,
dates, locations, speakers, notes, `cited_as` equal to the old `source` cell verbatim, and the sets of people and
organisations equal to the `organisers` and `organisations` cells, one organiser row per element. Beyond that:
ids are unique, an organiser row has exactly one of person and organisation, and cites what its event cites,
every address of every `cited_as` resolves to an id in the row's `sources`, and every such id is in the register
or among the new sources.

Run `python -m scripts.tools.audit_community`; it prints the counts per kind and the losses, and exits with 1
when there is any loss.
"""

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime

from scripts.lib.model import load_sources
from scripts.lib.model.schema import split_set
from scripts.lib.model.sources import source_id, split_archive_url
from scripts.tools import migrate_community
from scripts.tools.migrate_community import ROLE_FIELDS, Migrated

BASE = '122a213'
OLD_FOLDER = 'curated/community-contributions'
ADDRESS = re.compile(r'https?://[^\s;"<>]+')
VIDEO_SITE = re.compile(r'youtu|vimeo|plone\.tv')
# Every column of every old kind: a column that is not listed here is not audited, which is itself a loss
OLD_COLUMNS = {
    'sprints': {'sprint', 'start', 'end', 'location', 'organisers', 'organisations', 'level', 'source', 'notes'},
    'world-plone-day-event': {'date', 'location', 'format', 'organisations', 'organisers', 'source', 'notes'},
    'world-plone-day-talks': {'title', 'speakers', 'organisations', 'type', 'location', 'source', 'notes'},
    'conference-talks': {'event', 'scope', 'type', 'title', 'speakers', 'organisations', 'video', 'source',
                         'notes'},
    'plone-conference': {'organisation', 'organisers', 'source', 'notes'},
    'plone-conference-trainings': {'title', 'trainers', 'source', 'notes'},
    **{kind: {*columns, 'source', 'notes'} for kind, columns in ROLE_FIELDS.items()},
}
SCOPE_OF = {'conference': 'global', 'symposium': 'regional'}


def _git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True, text=True, encoding='utf-8').stdout


def read_old_at(commit):
    """{kind: {year: rows}} of the yearly community files at the commit, read from git with plain csv."""
    old = {}
    for name in _git('ls-tree', '--name-only', commit, f'{OLD_FOLDER}/').split('\n'):
        match = migrate_community.OLD_FILE.match(name.rpartition('/')[2])
        if match:
            text = _git('show', f'{commit}:{name}')
            old.setdefault(match.group(2), {})[int(match.group(1))] = list(csv.DictReader(io.StringIO(text)))
    return old


def read_written(folder=migrate_community.NEW_FOLDER):
    """The new rows of the written files of the folder, read with plain csv."""
    def rows(name):
        with open(folder / name, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    found = Migrated(events=rows('events.csv'), talks=rows('talks.csv'), trainings=rows('trainings.csv'),
                     organisers=rows('organisers.csv'))
    found.roles = {kind: rows(f'{kind}.csv') for kind in ROLE_FIELDS}
    return found


class Audit:
    """The counts per kind and the losses of one comparison."""

    def __init__(self):
        self.counts = {}  # kind -> (old rows, new rows)
        self.losses = []

    def loss(self, kind, message):
        self.losses.append(f'{kind}: {message}')

    def compare(self, kind, before, after):
        """Compare two multisets of tuples: what is only in `before` is lost, what is only in `after` is extra."""
        before, after = Counter(before), Counter(after)
        self.counts[kind] = (sum(before.values()), sum(after.values()))
        for item, count in (before - after).items():
            self.loss(kind, f'lost x{count}: {item!r}')
        for item, count in (after - before).items():
            self.loss(kind, f'extra x{count}: {item!r}')


def _people(rows, event):
    return frozenset(o['person'] for o in rows.get(event, ()) if o['person'])


def _organisations(rows, event):
    return frozenset(o['organisation'] for o in rows.get(event, ()) if o['organisation'])


def _by_event(organisers):
    found = {}
    for organiser in organisers:
        found.setdefault(organiser['event'], []).append(organiser)
    return found


def _check_columns(audit, old):
    for kind, by_year in old.items():
        for year, rows in by_year.items():
            for line, row in enumerate(rows, start=2):
                if None in row or any(value is None for value in row.values()):
                    audit.loss(kind, f'{year} line {line} has a missing or an extra cell')
                audit_columns = OLD_COLUMNS.get(kind)
                if audit_columns is None:
                    audit.loss(kind, f'{year}: a kind of file that the audit does not know')
                    break
                if set(row) - {None} != audit_columns:
                    audit.loss(kind, f'{year}: columns {sorted(set(row) - {None})} are not audited')
                    break


def _check_ids(audit, new):
    for kind, rows in (('events', new.events), ('talks', new.talks), ('trainings', new.trainings)):
        ids = Counter(row['id'] for row in rows)
        for found, count in ids.items():
            if count > 1:
                audit.loss(kind, f'id {found} is used {count} times')


def _check_organisers(audit, new, events, by_event):
    for organiser in new.organisers:
        if bool(organiser['person']) == bool(organiser['organisation']):
            audit.loss('organisers', f'not exactly one of person and organisation: {organiser!r}')
        event = events.get(organiser['event'])
        if event is None:
            audit.loss('organisers', f'of an unknown event: {organiser!r}')
        elif event['kind'] in ('sprint', 'wpd'):
            got = (organiser['sources'], organiser['cited_as'], organiser['notes'])
            if got != (event['sources'], event['cited_as'], ''):
                audit.loss('organisers', f'cites differently than its event {event["id"]}: {organiser!r}')


def _check_kind_rows(audit, old, new, events, by_event):
    def of(kind):
        return [(year, row) for year, rows in old.get(kind, {}).items() for row in rows]

    # Sprints
    audit.compare('sprints', (
        (y, r['sprint'], r['start'], r['end'], r['location'], r['level'], r['source'], r['notes'],
         frozenset(split_set(r['organisers'])), frozenset(split_set(r['organisations'])))
        for y, r in of('sprints')),
        ((int(e['year']), e['name'], e['start'], e['end'], e['location'], e['level'], e['cited_as'], e['notes'],
          _people(by_event, e['id']), _organisations(by_event, e['id']))
         for e in new.events if e['kind'] == 'sprint'))

    # World Plone Day events; the online editions come with the talks
    audit.compare('world-plone-day-event', (
        (y, r['date'], r['location'], r['format'], r['source'], r['notes'],
         frozenset(split_set(r['organisers'])), frozenset(split_set(r['organisations'])))
        for y, r in of('world-plone-day-event')),
        ((int(e['year']), e['start'], e['location'], e['format'], e['cited_as'], e['notes'],
          _people(by_event, e['id']), _organisations(by_event, e['id']))
         for e in new.events if e['kind'] == 'wpd' and not e['id'].endswith('-online')))

    # Plone Conference organisers, element by element; the notes of the file row stay on each element
    audit.compare('plone-conference', (
        *((f'plone-conference-{y}', p, '', r['source'], r['notes']) for y, r in of('plone-conference')
          for p in split_set(r['organisers'])),
        *((f'plone-conference-{y}', '', r['organisation'], r['source'], r['notes']) for y, r in of('plone-conference')
          if r['organisation'].strip())),
        ((o['event'], o['person'], o['organisation'], o['cited_as'], o['notes'])
         for o in new.organisers if events.get(o['event'], {}).get('kind') == 'conference'))
    for year, row in of('plone-conference'):
        if ';' in row['organisation']:
            audit.loss('plone-conference', f'{year}: the organisation cell holds several values: {row["organisation"]!r}')

    # Conference talks
    def talk_event(talk):
        return events.get(talk['event'], {'kind': None, 'year': '0', 'name': ''})

    audit.compare('conference-talks', (
        (y, r['event'], r['scope'], r['type'], r['title'], r['speakers'], r['organisations'], r['video'],
         r['source'], r['notes']) for y, r in of('conference-talks')),
        ((int(talk_event(t)['year']), talk_event(t)['name'], SCOPE_OF[talk_event(t)['kind']], t['type'], t['title'],
          t['speakers'], t['organisations'], t['video'], t['cited_as'], t['notes'])
         for t in new.talks if talk_event(t)['kind'] in SCOPE_OF))

    # World Plone Day talks, with their location
    audit.compare('world-plone-day-talks', (
        (y, r['title'], r['speakers'], r['organisations'], r['type'], r['location'], r['source'], r['notes'])
        for y, r in of('world-plone-day-talks')),
        ((int(talk_event(t)['year']), t['title'], t['speakers'], t['organisations'], t['type'], t['location'],
          t['cited_as'], t['notes']) for t in new.talks if talk_event(t)['kind'] == 'wpd'))
    for talk in new.talks:
        if talk['event'] not in events:
            audit.loss('talks', f'of an unknown event: {talk["id"]}')
        elif events[talk['event']]['kind'] == 'wpd':
            if talk['video'] and talk['video'] not in talk['cited_as']:
                audit.loss('world-plone-day-talks', f'the video of {talk["id"]} is not in its source')
            if not talk['video'] and VIDEO_SITE.search(talk['cited_as']):
                audit.loss('world-plone-day-talks', f'a video of {talk["id"]} is missing')

    # Trainings
    audit.compare('plone-conference-trainings', (
        (y, r['title'], r['trainers'], r['source'], r['notes']) for y, r in of('plone-conference-trainings')),
        ((int(talk_event(t)['year']), t['title'], t['trainers'], t['cited_as'], t['notes']) for t in new.trainings))
    for training in new.trainings:
        if talk_event(training)['kind'] != 'conference':
            audit.loss('plone-conference-trainings', f'{training["id"]} is not at a Plone Conference')

    # Roles, in the order of the old files
    for kind, columns in ROLE_FIELDS.items():
        before = [(str(y), *(r[c] for c in columns), r['source'], r['notes']) for y, r in of(kind)]
        after = [(r['year'], *(r[c] for c in columns), r['cited_as'], r['notes']) for r in new.roles.get(kind, [])]
        audit.compare(kind, before, after)
        if Counter(before) == Counter(after) and before != after:
            audit.loss(kind, 'the rows are not in the order of the old files')

    # One organiser row per element of the set cells (the sprint and World Plone Day totals)
    expected = sum(len(split_set(r['organisers'])) + len(split_set(r['organisations']))
                   for kind in ('sprints', 'world-plone-day-event') for _, r in of(kind))
    expected += sum(len(split_set(r['organisers'])) + bool(r['organisation'].strip())
                    for _, r in of('plone-conference'))
    audit.counts['organisers'] = (expected, len(new.organisers))
    if expected != len(new.organisers):
        audit.loss('organisers', f'{len(new.organisers)} rows for {expected} elements of the old cells')


def _check_sources(audit, new, results, known):
    captured = {line['url']: line for line in results}
    rows = [*new.events, *new.talks, *new.trainings, *new.organisers, *(r for v in new.roles.values() for r in v)]
    checked = 0
    for row in rows:
        ids = split_set(row['sources'])
        where = row.get('id') or row.get('event') or f'{row.get("year")} {row.get("person")}'
        if len(set(ids)) != len(ids):
            audit.loss('sources', f'{where}: an id twice in {row["sources"]!r}')
        for sid in ids:
            if sid not in known:
                audit.loss('sources', f'{where}: {sid} is neither in the register nor a new source')
        for url in ADDRESS.findall(row['cited_as']):
            url = url.rstrip('.,:)')
            candidates = {source_id(*(split_archive_url(url) or (url, None)))}
            if captured.get(url, {}).get('source_id'):
                candidates.add(captured[url]['source_id'])
            checked += 1
            if not candidates & set(ids):
                audit.loss('sources', f'{where}: {url} has no id in {row["sources"]!r}')
        if ADDRESS.search(row['cited_as']) is None and ids:
            audit.loss('sources', f'{where}: ids but no address in the cited text')
    audit.counts['sources'] = (checked, checked)


def audit_migration(old, new, results, known):
    """The Audit of the new rows against the old ones; `known` is the set of the ids of the register and of the
    new sources."""
    audit = Audit()
    _check_columns(audit, old)
    _check_ids(audit, new)
    events = {e['id']: e for e in new.events}
    by_event = _by_event(new.organisers)
    _check_organisers(audit, new, events, by_event)
    _check_kind_rows(audit, old, new, events, by_event)
    _check_sources(audit, new, results, known)
    return audit


def report(audit):
    lines = [f'{kind}: {before} old, {after} new' for kind, (before, after) in audit.counts.items()]
    lines.append(f'losses: {len(audit.losses)}')
    lines += [f'  {loss}' for loss in audit.losses]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit the migration of the community files for losses.')
    parser.add_argument('--commit', default=BASE, help='the git commit that holds the old files (default: the base)')
    parser.add_argument('--written', action='store_true',
                        help='read the new rows from the written curated/community/ files, not from the migration')
    args = parser.parse_args(argv)
    results = [line for name in migrate_community.RESULT_FILES
               for line in migrate_community._read_jsonl(migrate_community.ARCHIVE / name)]
    worklist = [line for name in migrate_community.WORKLIST_FILES
                for line in migrate_community._read_jsonl(migrate_community.ARCHIVE / name)]
    register = {sid: asdict(source) for sid, source in load_sources().items()}
    old = read_old_at(args.commit)
    if args.written:
        new, known = read_written(), set(register)
    else:
        now = datetime.now(UTC)
        new = migrate_community.migrate(old, results, register, worklist, now=now)
        known = set(register) | {source['id'] for source in new.new_sources}
    audit = audit_migration(old, new, results, known)
    print(report(audit))
    return 1 if audit.losses else 0


if __name__ == '__main__':
    sys.exit(main())
