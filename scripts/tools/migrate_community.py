#!/usr/bin/env python3
"""Turn the yearly community files into one file per kind: events, talks, trainings, organisers and the roles.

Migration code for plan 3b, archived to archive/migration-to-events/ after its one use, as the migrations of plan
2c were. It reads the old files with plain csv, since their schemas go away with the switch, and the capture
results of plan 3a in archive/migration-to-events/.

The rules (the decisions of plan 3b):

- Every new row has `sources`, the distinct source ids of the addresses of the old `source` cell in the order
  of the cell (scripts.lib.cells), and `cited_as`, the old cell verbatim. A cell with text but no address has no
  sources. An address is resolved through its capture result; an address the capture did not record becomes an
  uncaptured source: kind by the work list's hint, else by the capture adapter of the address (else `pdf` for a
  PDF address, else `page`), its address as title, the capture day as date, and `not captured on <day>: ` and
  the reason in its notes and its excerpt (`nothing found` when the capture found nothing, else the error,
  shortened by `short_reason`).
- Events (`events.csv`) have a kind: `conference` for the Plone Conference of a year, which exists for every
  year with a `plone-conference` file, conference talks of `global` scope or trainings, named `Plone Conference
  <year>`, without dates or location; `symposium` for every other conference (`regional` talks), one per year and
  name; `wpd` for each World Plone Day row, and for the online edition of a year that its talks point to;
  `sprint` for each sprint row. Every event has the year of its file, since many have no start date.
- Ids are opaque slugs, given once: `plone-conference-<year>`, `wpd-<year>-online`, `wpd-<date>-<location>`, the
  slugified name of a symposium or sprint; a slug that is taken gets `-2`, `-3`, in the order of the years and
  files.
- Talks (`talks.csv`) are the conference talks (the `scope` goes: the event's kind says it) and the World Plone
  Day talks. A World Plone Day talk belongs to the event of its year whose city and country it names
  (`Italy (Bologna)` is `Bologna, Italy`, accents and case aside), or to the only event of its country when it
  names no city; else, as for `Online`, to the online edition of its year. Its `video` is the first address of
  its source on a video host, as the model reads it today. Id `t` and eight hex digits of SHA-1 over
  `event|title|type`, with `-2` for a second talk of the same event, title and type.
- Trainings (`trainings.csv`) belong to the Plone Conference of their year. Id `r` and eight hex digits over
  `event|title`.
- Organisers (`organisers.csv`): one row per person and per organisation of the `organisers` and
  `organisations` cells of sprints and World Plone Day rows, and of the `organisation` and `organisers` cells of
  the `plone-conference` rows. An organiser row cites what its old row cites; the notes of a conference row stay
  on its organiser rows, those of a sprint or World Plone Day row on the event.
- Roles (`board-of-directors.csv`, `team-leaders.csv`, `release-managers.csv`, `podcasts.csv`) get a `year`.
- Order: events by year, start and id; talks by event, type, title and id; trainings by event and title;
  organisers by event, person and organisation; roles by year and their line in the old file.

Run `python -m scripts.tools.migrate_community` for a summary of what it would write, `--write` to write
curated/community/ and the new sources, and to remove curated/community-contributions/ (the two recognition files
move to the new folder).
"""

import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.lib import paths
from scripts.lib.capture import KIND_BY_ADAPTER
from scripts.lib.capture.extract import adapter_for
from scripts.lib.cells import parse_segment, split_segments
from scripts.lib.model import load_sources
from scripts.lib.model.community import VIDEO_HOSTS
from scripts.lib.model.names import fold, unique_slug
from scripts.lib.model.schema import split_set
from scripts.lib.model.sources import (Source, add_passage, archive_url_of, source_id, split_archive_url,
                                       write_source)

CAPTURE_DAY = '2026-10-25'
UNCAPTURED = f'not captured on {CAPTURE_DAY}: '
NOTHING_FOUND = 'nothing found'
BYTES = re.compile(r'''(?<![A-Za-z0-9_])b(["'])(.*?)(?<!\\)\1''', re.S)
ARCHIVE = Path('archive/migration-to-events')
RESULT_FILES = ('capture-results.jsonl', 'videos-capture-results.jsonl')
WORKLIST_FILES = ('worklist.jsonl', 'videos-worklist.jsonl')
NEW_FOLDER = paths.COMMUNITY.parent / 'community'
KEPT_FILES = ('community-recognition-levels.csv', 'community-recognition-points.csv')
OLD_FILE = re.compile(r'^(\d{4})-(.+)\.csv$')

CITED = ('sources', 'cited_as')
EVENT_FIELDS = ('id', 'kind', 'name', 'year', 'start', 'end', 'location', 'format', 'level', *CITED, 'notes')
TALK_FIELDS = ('id', 'event', 'type', 'title', 'speakers', 'organisations', 'video', *CITED, 'notes')
TRAINING_FIELDS = ('id', 'event', 'title', 'trainers', *CITED, 'notes')
ORGANISER_FIELDS = ('event', 'person', 'organisation', *CITED, 'notes')
# Old kind -> the columns of its new file, after `year`
ROLE_FIELDS = {
    'board-of-directors': ('person', 'role'),
    'team-leaders': ('person', 'team'),
    'release-managers': ('person',),
    'podcasts': ('series', 'person', 'episodes'),
}
GLOBAL, REGIONAL = 'global', 'regional'
ONLINE = 'Online'
LEADING_ADDRESS = re.compile(r'^https?://\S+:\s+')  # the address an error names first: the cited one or its id_ form
ADDRESS = re.compile(r'https?://\S+')
TALK_PLACE = re.compile(r'^(?P<country>[^()]+?)\s*(?:\((?P<city>[^()]+)\))?$')


@dataclass
class Migrated:
    """The rows of the new files, the sources to add with their excerpts, and the talks to look at."""
    events: list = field(default_factory=list)
    talks: list = field(default_factory=list)
    trainings: list = field(default_factory=list)
    organisers: list = field(default_factory=list)
    roles: dict = field(default_factory=dict)  # old kind -> rows
    new_sources: list = field(default_factory=list)
    new_excerpts: dict = field(default_factory=dict)
    unmatched_talks: list = field(default_factory=list)  # World Plone Day talks that went online for want of an event
    by_country_only: list = field(default_factory=list)  # World Plone Day talks matched by their country alone

    def files(self):
        """{file name: (columns, rows)} of the new files, in a fixed order."""
        found = {'events.csv': (EVENT_FIELDS, self.events), 'talks.csv': (TALK_FIELDS, self.talks),
                 'trainings.csv': (TRAINING_FIELDS, self.trainings),
                 'organisers.csv': (ORGANISER_FIELDS, self.organisers)}
        for kind, columns in ROLE_FIELDS.items():
            found[f'{kind}.csv'] = (('year', *columns, *CITED, 'notes'), self.roles.get(kind, []))
        return found


def _kind_of(url):
    """The kind the capture would give the address: by its adapter, else pdf or page by the address."""
    kind = KIND_BY_ADAPTER.get(adapter_for(url))
    if kind and kind != 'page':
        return kind
    return 'pdf' if url.lower().split('?')[0].split('#')[0].endswith('.pdf') else 'page'


def _decoded(text):
    """The text with its first quoted byte string (`b"..."`, as Python prints bytes) decoded."""
    match = BYTES.search(text)
    if match is None:
        return text
    try:
        decoded = ast.literal_eval(match.group(0)).decode('utf-8', 'replace')
    except (ValueError, SyntaxError):
        return text
    return text[:match.start()] + decoded + text[match.end():]


def short_reason(reason):
    """The reason why an address was not captured, in one line: a rate limit of yt-dlp as `rate limited (HTTP
    429)`, another failure of yt-dlp as its `ERROR:` line without the prefix, any other reason as its first
    line; a byte string in it decoded. As in plan 2c."""
    text = _decoded(reason)
    lines = [line.strip() for line in text.splitlines() if line.strip()] or ['']
    if 'yt-dlp' in reason:
        if 'HTTP Error 429' in text:
            return 'rate limited (HTTP 429)'
        error = next((line for line in lines if line.startswith('ERROR:')), None)
        if error is not None:
            return error.removeprefix('ERROR:').strip()
    return lines[0]


def _id_of(url):
    """The source id of an address; a Wayback address names the copy of its original."""
    return source_id(*(split_archive_url(url) or (url, None)))


class _Sources:
    """Finds the source of a cited address and creates a source for each address the capture did not record."""

    def __init__(self, results, worklist, sources, now):
        self.results = {line['url']: line for line in results}
        self.hints = {item['url']: item.get('kind') for item in worklist}
        self.sources = sources
        self.fetched = now.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.new = {}  # id -> row

    def resolve(self, url):
        """The id of the address's source: by its capture result, else by the register (the video work list left
        out the videos it held); an uncaptured source when the capture recorded none."""
        if url not in self.results:
            sid = _id_of(url)
            if sid in self.sources:
                return sid
            raise ValueError(f'no capture result for {url}, and the register does not hold it')
        result = self.results[url]
        found = result.get('source_id')
        if found:
            if found not in self.sources:
                raise ValueError(f'the capture result of {url} names {found}, which is not in the register')
            return found
        error = result.get('error')
        return self._uncaptured(url, short_reason(LEADING_ADDRESS.sub('', error)) if error else NOTHING_FOUND)

    def _uncaptured(self, url, reason):
        original, timestamp = split_archive_url(url) or (url, None)
        sid = _id_of(url)
        if sid in self.sources:
            return sid
        if sid not in self.new:
            self.new[sid] = {'id': sid, 'kind': self.hints.get(url) or _kind_of(url), 'title': url,
                             'date': CAPTURE_DAY, 'url': original,
                             'archive_url': archive_url_of(original, timestamp) if timestamp else '',
                             'fetched': self.fetched, 'notes': UNCAPTURED + reason}
        return sid

    def cite(self, cell):
        """{sources, cited_as} of a source cell."""
        cell = cell or ''
        ids = []
        for segment in split_segments(cell):
            for cited in parse_segment(segment):
                sid = self.resolve(cited.url)
                if sid not in ids:
                    ids.append(sid)
        return {'sources': ';'.join(ids), 'cited_as': cell}


def _text(value):
    return (value or '').strip()


def _hashed(prefix, text, taken):
    """`prefix` and eight hex digits of SHA-1 over the text, with -2, -3 when taken."""
    base = prefix + hashlib.sha1(text.encode()).hexdigest()[:8]
    candidate, number = base, 1
    while candidate in taken:
        number += 1
        candidate = f'{base}-{number}'
    taken.add(candidate)
    return candidate


def _video_link(text):
    """The first address of the text on a video host, else '' (the model's rule for World Plone Day talks)."""
    for link in ADDRESS.findall(text or ''):
        host = link.split('/')[2].lower()
        if any(host == h or host.endswith('.' + h) for h in VIDEO_HOSTS):
            return link.rstrip(';,')
    return ''


def _event_place(location):
    """(city, country) of a World Plone Day location such as `Bologna, Italy`, folded for comparison."""
    parts = [part.strip() for part in location.split(',')]
    city = re.sub(r'\s*\([^()]*\)', '', parts[0])
    return fold(city), fold(parts[1] if len(parts) > 1 else parts[0])


def _talk_place(location):
    """(city or None, country) of a World Plone Day talk location such as `Italy (Bologna)`, folded."""
    match = TALK_PLACE.match(location.strip())
    if not match:
        return None, fold(location)
    city = match.group('city')
    return (fold(city) if city else None), fold(match.group('country'))


def _event(eid, kind, name, year, start='', end='', location='', fmt='', level='', cited=None, notes=''):
    return {'id': eid, 'kind': kind, 'name': name, 'year': str(year), 'start': start, 'end': end,
            'location': location, 'format': fmt, 'level': level, **(cited or {'sources': '', 'cited_as': ''}),
            'notes': notes}


def _lines(rows):
    """[(line, row)] of the rows of a file; the header is line 1."""
    return list(enumerate(rows, start=2))


def migrate(old, results, sources, worklist=(), now=None):
    """The new files from the old rows.

    `old` maps each old kind to {year: rows} (as csv.DictReader reads them; a year with an empty file has no
    rows); `results` are the lines of the capture results of plan 3a, `worklist` the lines of its work lists (for
    the kind hints of uncaptured addresses), and `sources` maps the ids of the source register to their rows.
    """
    found = _Sources(results, worklist, sources, now or datetime.now(UTC))
    old = {kind: dict(sorted(by_year.items())) for kind, by_year in old.items()}

    def of(kind):
        return old.get(kind, {})

    migrated = Migrated()
    events = {}  # id -> row
    taken = set()

    # The ids of a fixed form first, so that no slug takes them
    conference_years = sorted({*of('plone-conference'), *of('plone-conference-trainings'),
                               *(year for year, rows in of('conference-talks').items()
                                 if any(_text(r['scope']) == GLOBAL for r in rows))})
    conference = {}
    for year in conference_years:
        conference[year] = f'plone-conference-{year}'
        events[conference[year]] = _event(conference[year], 'conference', f'Plone Conference {year}', year)
    online_years = sorted({*of('world-plone-day-talks'), *of('world-plone-day-event')})
    taken |= set(events) | {f'wpd-{year}-online' for year in online_years}

    # World Plone Day events, one per row
    wpd_rows = {}  # year -> [(id, row)]
    for year, rows in of('world-plone-day-event').items():
        for r in rows:
            location = _text(r['location'])
            eid = unique_slug(f'wpd-{_text(r["date"])}-{location}', taken)
            taken.add(eid)
            events[eid] = _event(eid, 'wpd', f'World Plone Day {year}, {location}', year, start=_text(r['date']),
                                 location=location, fmt=_text(r['format']), cited=found.cite(r['source']),
                                 notes=r['notes'] or '')
            wpd_rows.setdefault(year, []).append((eid, r))

    # Symposia, one per year and name, in the order of their first talk
    symposium = {}  # (year, name) -> id
    for year, rows in of('conference-talks').items():
        for r in rows:
            name, scope = _text(r['event']), _text(r['scope'])
            if scope == GLOBAL:
                if name != f'Plone Conference {year}':
                    raise ValueError(f'a global talk of {year} at "{name}", not at Plone Conference {year}')
            elif scope == REGIONAL:
                if (year, name) not in symposium:
                    eid = unique_slug(name, taken)
                    taken.add(eid)
                    symposium[year, name] = eid
                    events[eid] = _event(eid, 'symposium', name, year)
            else:
                raise ValueError(f'a talk of {year} with the scope "{scope}"')

    sprint_rows = {}  # year -> [(id, row)]
    for year, rows in of('sprints').items():
        for r in rows:
            name = _text(r['sprint'])
            eid = unique_slug(name, taken)
            taken.add(eid)
            events[eid] = _event(eid, 'sprint', name, year, start=_text(r['start']), end=_text(r['end']),
                                 location=_text(r['location']), level=_text(r['level']),
                                 cited=found.cite(r['source']), notes=r['notes'] or '')
            sprint_rows.setdefault(year, []).append((eid, r))

    # Talks
    talk_ids = set()

    def add_talk(eid, r, video):
        title, kind = _text(r['title']), _text(r['type'])
        tid = _hashed('t', f'{eid}|{title}|{kind}', talk_ids)
        migrated.talks.append({'id': tid, 'event': eid, 'type': kind, 'title': title,
                               'speakers': _text(r['speakers']), 'organisations': _text(r['organisations']),
                               'video': video, **found.cite(r['source']), 'notes': r['notes'] or ''})

    for year, rows in of('conference-talks').items():
        for r in rows:
            scope = _text(r['scope'])
            eid = conference[year] if scope == GLOBAL else symposium[year, _text(r['event'])]
            add_talk(eid, r, _text(r['video']))

    for year, rows in of('world-plone-day-talks').items():
        places = [(eid, _event_place(_text(r['location']))) for eid, r in wpd_rows.get(year, [])]
        online = f'wpd-{year}-online'
        for line, r in _lines(rows):
            location = _text(r['location'])
            eid = None
            if location != ONLINE:
                city, country = _talk_place(location)
                matches = [e for e, (c, k) in places if k == country and (city is None or c == city)]
                if len(matches) > 1:
                    raise ValueError(f'the World Plone Day talk of {year} at line {line} ({location}) matches two '
                                     f'events: {", ".join(matches)}')
                eid = matches[0] if matches else None
                entry = {'year': year, 'line': line, 'title': _text(r['title']), 'location': location}
                if eid is None:
                    migrated.unmatched_talks.append({**entry, 'event': online})
                elif city is None:
                    migrated.by_country_only.append({**entry, 'event': eid})
            if eid is None:
                eid = online
                if online not in events:
                    events[online] = _event(online, 'wpd', f'World Plone Day {year}, {ONLINE}', year,
                                            location=ONLINE, fmt='online')
            add_talk(eid, r, _video_link(r['source']))

    # Trainings
    training_ids = set()
    for year, rows in of('plone-conference-trainings').items():
        for r in rows:
            eid, title = conference[year], _text(r['title'])
            migrated.trainings.append({'id': _hashed('r', f'{eid}|{title}', training_ids), 'event': eid,
                                       'title': title, 'trainers': _text(r['trainers']), **found.cite(r['source']),
                                       'notes': r['notes'] or ''})

    # Organisers
    organisers = {}  # (event, person, organisation) -> row

    def add_organisers(eid, people, organisations, cited, notes, where):
        named = [(person, '') for person in people] + [('', organisation) for organisation in organisations]
        if not named:
            raise ValueError(f'{where} names no organiser')
        for person, organisation in named:
            key = (eid, person, organisation)
            if key in organisers:
                raise ValueError(f'{where}: {person or organisation} is an organiser of {eid} twice')
            organisers[key] = {'event': eid, 'person': person, 'organisation': organisation, **cited, 'notes': notes}

    for year, rows in of('plone-conference').items():
        for line, r in _lines(rows):
            organisation = _text(r['organisation'])
            add_organisers(conference[year], split_set(r['organisers']), [organisation] if organisation else [],
                           found.cite(r['source']), r['notes'] or '', f'{year}-plone-conference.csv line {line}')
    for kind, by_year in (('sprints', sprint_rows), ('world-plone-day-event', wpd_rows)):
        for year, pairs in by_year.items():
            for line, (eid, r) in _lines(pairs):
                people, organisations = split_set(r['organisers']), split_set(r['organisations'])
                if people or organisations:
                    add_organisers(eid, people, organisations, {key: events[eid][key] for key in CITED}, '',
                                   f'{year}-{kind}.csv line {line}')

    # Roles
    for kind, columns in ROLE_FIELDS.items():
        migrated.roles[kind] = [{'year': str(year), **{column: _text(r[column]) for column in columns},
                                 **found.cite(r['source']), 'notes': r['notes'] or ''}
                                for year, rows in of(kind).items() for r in rows]

    migrated.events = sorted(events.values(), key=lambda e: (e['year'], e['start'], e['id']))
    migrated.talks.sort(key=lambda t: (t['event'], t['type'], t['title'], t['id']))
    migrated.trainings.sort(key=lambda t: (t['event'], t['title'], t['id']))
    migrated.organisers = [organisers[key] for key in sorted(organisers)]
    migrated.new_sources = [found.new[sid] for sid in sorted(found.new)]
    migrated.new_excerpts = {sid: found.new[sid]['notes'] for sid in sorted(found.new)}
    return migrated


def _counts(values):
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return ', '.join(f'{value} {count}' for value, count in sorted(counts.items()))


def summary(migrated):
    """What the migration writes, in a few lines."""
    lines = [f'{name}: {len(rows)}' for name, (_, rows) in migrated.files().items()]
    lines.append(f'events: {_counts(e["kind"] for e in migrated.events)}')
    lines.append(f'World Plone Day talks without an event of their place, put online: {len(migrated.unmatched_talks)}')
    lines += [f'  {t["year"]} line {t["line"]}: "{t["title"]}" at {t["location"]} -> {t["event"]}'
              for t in migrated.unmatched_talks]
    lines.append(f'World Plone Day talks matched by their country alone: {len(migrated.by_country_only)}')
    lines += [f'  {t["year"]} line {t["line"]}: "{t["title"]}" at {t["location"]} -> {t["event"]}'
              for t in migrated.by_country_only]
    reasons = _counts(ADDRESS.sub('<address>', row['notes'].removeprefix(UNCAPTURED)) for row in migrated.new_sources)
    lines.append(f'uncaptured sources created: {len(migrated.new_sources)}' + (f' ({reasons})' if reasons else ''))
    return '\n'.join(lines)


def read_old(folder):
    """{kind: {year: rows}} of the yearly files of the folder, read with plain csv."""
    old = {}
    for path in sorted(Path(folder).iterdir()):
        match = OLD_FILE.match(path.name)
        if match:
            with open(path, newline='', encoding='utf-8') as f:
                old.setdefault(match.group(2), {})[int(match.group(1))] = list(csv.DictReader(f))
    return old


def _read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write(migrated, old_folder=paths.COMMUNITY, new_folder=NEW_FOLDER):
    """Write the new sources and files, move the recognition files and remove the old folder."""
    # The sources first: a failure part-way leaves extra sources, never rows citing missing ones
    for row in migrated.new_sources:
        write_source(Source(row['id'], row['kind'], row['title'], date.fromisoformat(row['date']), row['url'],
                            row['archive_url'] or None,
                            datetime.strptime(row['fetched'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC),
                            row['notes']))
        add_passage(row['id'], migrated.new_excerpts[row['id']])
    new_folder = Path(new_folder)
    new_folder.mkdir(parents=True, exist_ok=True)
    for name, (fields, rows) in migrated.files().items():
        _write_csv(new_folder / name, fields, rows)
    old_folder = Path(old_folder)
    for name in KEPT_FILES:
        shutil.move(old_folder / name, new_folder / name)
    for path in sorted(old_folder.iterdir()):
        if OLD_FILE.match(path.name):
            path.unlink()
    old_folder.rmdir()  # fails, and so names it, when the old folder holds anything else


def main(argv=None):
    parser = argparse.ArgumentParser(description='Migrate the yearly community files to one file per kind.')
    parser.add_argument('--write', action='store_true',
                        help='write curated/community/ and the new sources, and remove the old folder')
    args = parser.parse_args(argv)
    results = [line for name in RESULT_FILES for line in _read_jsonl(ARCHIVE / name)]
    worklist = [line for name in WORKLIST_FILES for line in _read_jsonl(ARCHIVE / name)]
    register = {sid: asdict(source) for sid, source in load_sources().items()}
    migrated = migrate(read_old(paths.COMMUNITY), results, register, worklist)
    print(summary(migrated))
    if args.write:
        write(migrated)
        print('written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
