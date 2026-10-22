#!/usr/bin/env python3
"""Turn the old registers into people, identities, affiliations and citations of the source register.

Migration code for plan 2c, archived to archive/ after its one use, as scripts/tools/migrate_data_structure.py
was. It reads the old files with plain csv, since their schemas go away with the switch, and the files that the
capture of plan 2a left in archive/migration-to-sources/.

The rules (the decisions of plan 2c):

- people.csv keeps id and name. Its `github` becomes an identity of kind `github`; a person without one gets an
  identity of kind `name` with the display name. Either cites the source of the old `source` cell.
- A `login` identity becomes `github-alias`; email and name identities keep their kind.
- An identity cites one source: the first captured address of its old cell. Its snippet is the first quote of the
  cell that the source's excerpt holds (for an email address: the address itself when the excerpt holds it), and
  its notes keep the old cell as it was.
- An affiliation gets an opaque id (`affiliation_id`) and a status: `assumed` when its notes say `not verified`,
  else `stated`. A rejected proposal becomes a `denied` affiliation whose notes are the reason.
- Every address of an affiliation's `source` cell (of a rejection's `source` cell) is cited: one citation per
  quote of the cell that the source's excerpt holds (for a rejection also its reason), else one without a
  snippet. The citation's notes are `cited as: ` and the segment of the cell that cites the address, verbatim,
  with its label, quotes and address as written; a segment without an address joins the nearest segment
  before it that has one (else the one after it), and the segments that cite one source are joined with `; `
  in the order of the cell. The old `notes` cell is not cited: it stays the affiliation's notes, as it was.
- A GitHub commit search is cited through the commits it found; a search that found nothing is cited as an
  uncaptured source.
- An address the capture did not record becomes an uncaptured source: kind by the work list's hint, else by
  the capture adapter of the address (else `pdf` for a PDF address, else `page`), its address as title, the
  capture day as date, and the reason in its notes and its excerpt.
- A comment on a pull request or issue of this repository (`#issuecomment-…`) that a rejection cites becomes a
  source of kind `decision`.

Run `python -m scripts.tools.migrate_registers` for a summary of what it would write, `--write` to write it.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.lib import paths
from scripts.lib.capture import KIND_BY_ADAPTER
from scripts.lib.capture.extract import adapter_for
from scripts.lib.capture.passages import find_quote
from scripts.lib.model import load_sources, read_excerpt
from scripts.lib.model.sources import (Source, add_passage, archive_url_of, source_id, split_archive_url,
                                       write_source)
from scripts.tools.cited_sources import is_search, parse_segment, quotes_of, split_segments

CAPTURE_DAY = '2026-10-22'
UNCAPTURED = f'not captured on {CAPTURE_DAY}: '
NOTHING_FOUND = 'nothing found'
DECISION_URL = re.compile(r'^https://github\.com/plone/plone-contributor-statistics/(?:pull|issues)/\d+'
                          r'#issuecomment-\d+$')
CITED_AS = 'cited as: '
ARCHIVE = Path('archive/migration-to-sources')

PEOPLE_FIELDS = ('id', 'name')
IDENTITY_FIELDS = ('person', 'kind', 'value', 'source', 'snippet', 'notes')
AFFILIATION_FIELDS = ('id', 'person', 'organisation', 'from', 'to', 'status', 'checked', 'notes')
CITATION_FIELDS = ('affiliation', 'source', 'snippet', 'supersedes', 'notes')
SOURCE_FIELDS = ('id', 'kind', 'title', 'date', 'url', 'archive_url', 'fetched', 'notes')
OLD_FILES = ('people.csv', 'identities.csv', 'affiliations.csv', 'rejected_proposals.csv')
PROPOSAL_FILES = ('affiliation_proposals.csv', 'rejected_proposals.csv')


@dataclass
class Migrated:
    """The rows of the new registers, the sources to add, the kinds to change and the excerpts of new sources."""
    people: list = field(default_factory=list)
    identities: list = field(default_factory=list)
    affiliations: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    new_sources: list = field(default_factory=list)
    new_excerpts: dict = field(default_factory=dict)
    kind_updates: dict = field(default_factory=dict)


def affiliation_id(person, organisation, start, end):
    """The opaque id of an affiliation: `a` and eight hex digits of a hash over its person, organisation and
    years at creation; it is never recomputed when the row changes later."""
    return 'a' + hashlib.sha1(f'{person}|{organisation}|{start}|{end}'.encode()).hexdigest()[:8]


def _add(values, new):
    for value in new:
        if value not in values:
            values.append(value)


def _kind_of(url):
    """The kind the capture would give the address: by its adapter, else pdf or page by the address."""
    kind = KIND_BY_ADAPTER.get(adapter_for(url))
    if kind and kind != 'page':
        return kind
    return 'pdf' if url.lower().split('?')[0].split('#')[0].endswith('.pdf') else 'page'


class _Sources:
    """Finds the source of a cited address and creates a source for each address the capture did not record."""

    def __init__(self, results, worklist, sources, excerpt, now):
        self.results = {line['url']: line for line in results}
        self.hints = {item['url']: item.get('kind') for item in worklist}
        self.sources = sources
        self._excerpt = excerpt
        self.fetched = now.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.new = {}  # id -> row
        self.excerpts = {}
        self._texts = {}

    def _result(self, url):
        if url not in self.results:
            raise ValueError(f'no capture result for {url}')
        return self.results[url]

    def captured(self, url):
        """The id of the source the capture recorded for the address, else None."""
        return self._result(url)['source_id']

    def resolve(self, url, kind=None):
        """The id of the address's source; an uncaptured source when the capture recorded none."""
        found = self.captured(url)
        if found:
            if found not in self.sources:
                raise ValueError(f'the capture result of {url} names {found}, which is not in the register')
            return found
        error = self._result(url)['error']
        reason = error.splitlines()[0].removeprefix(f'{url}: ') if error else NOTHING_FOUND
        return self.uncaptured(url, reason, kind)

    def uncaptured(self, url, reason, kind=None):
        """A source for an address without a capture: its id, deterministic as any source id."""
        archived = split_archive_url(url)
        original, timestamp = archived if archived else (url, None)
        sid = source_id(original, timestamp)
        if sid in self.sources:
            return sid
        if sid not in self.new:
            note = UNCAPTURED + reason
            self.new[sid] = {'id': sid, 'kind': kind or self.hints.get(url) or _kind_of(url), 'title': url,
                             'date': CAPTURE_DAY, 'url': original,
                             'archive_url': archive_url_of(original, timestamp) if archived else '',
                             'fetched': self.fetched, 'notes': note}
            self.excerpts[sid] = note
        elif kind:
            self.new[sid]['kind'] = kind
        return sid

    def kind(self, sid):
        return self.new[sid]['kind'] if sid in self.new else self.sources[sid]['kind']

    def holds(self, sid, quote):
        """Whether the excerpt of the source holds the quote."""
        if sid not in self._texts:
            self._texts[sid] = self.excerpts.get(sid) if sid in self.new else self._excerpt(sid)
        return bool(quote) and find_quote(self._texts[sid] or '', quote) is not None


class _Citations:
    """The citations of the affiliations: per affiliation and source, its snippets and the segments citing it."""

    def __init__(self):
        self.entries = {}  # (affiliation, source) -> {'snippets': [...], 'segments': [...]}

    def add(self, affiliation, sid, snippets=(), segments=()):
        entry = self.entries.setdefault((affiliation, sid), {'snippets': [], 'segments': []})
        _add(entry['snippets'], snippets)
        _add(entry['segments'], segments)

    def rows(self):
        rows = []
        for (affiliation, sid), entry in self.entries.items():
            notes = CITED_AS + '; '.join(entry['segments']) if entry['segments'] else ''
            for snippet in entry['snippets'] or ['']:
                rows.append({'affiliation': affiliation, 'source': sid, 'snippet': snippet, 'supersedes': '',
                             'notes': notes})
        return sorted(rows, key=lambda row: (row['affiliation'], row['source'], row['snippet']))


def _groups(cell):
    """[(segments, cited addresses)] of the cell: each segment with addresses, with the segments without an
    address that follow it (those before the first segment with addresses join that one), in the order of the
    cell. ValueError for a cell with text but no address, whose text would be lost."""
    groups, leading = [], []
    for segment in split_segments(cell):
        cited = parse_segment(segment)
        if cited:
            groups.append(([*leading, segment], cited))
            leading = []
        elif groups:
            groups[-1][0].append(segment)
        else:
            leading.append(segment)
    if leading:
        raise ValueError(f'a cell without an address: {cell}')
    return groups


def _cite_cell(cell, aid, sources, searches, citations, extra_quotes=()):
    """Cite every address of the cell for the affiliation, with the cell's segments verbatim in the notes;
    the quotes of the cell and the `extra_quotes` are the candidate snippets."""
    if not cell:
        return
    pool = quotes_of(cell)
    _add(pool, [quote for quote in extra_quotes if quote])
    for segments, cited in _groups(cell):
        for item in cited:
            if not is_search(item.url):
                sids = [sources.resolve(item.url)]
            elif item.url not in searches:
                raise ValueError(f'the search {item.url} is not in searches.json')
            elif searches[item.url]:
                sids = [sources.resolve(commit) for commit in searches[item.url]]
            else:
                sids = [sources.uncaptured(item.url, NOTHING_FOUND)]
            for sid in sids:
                citations.add(aid, sid, [quote for quote in pool if sources.holds(sid, quote)], segments)


def _identity(person, kind, value, cell, sources, searches):
    """An identity citing the first captured address of its old cell, which its notes keep."""
    urls = []
    for segment in split_segments(cell or ''):
        for item in parse_segment(segment):
            # a search counts through its commits; a search without results stands for itself
            urls += (searches.get(item.url) or [item.url]) if is_search(item.url) else [item.url]
    first = next((url for url in urls if not is_search(url) and sources.captured(url)), None)
    if first:
        sid = sources.resolve(first)
    elif urls:
        sid = (sources.uncaptured(urls[0], NOTHING_FOUND) if is_search(urls[0]) else sources.resolve(urls[0]))
    else:
        sid = ''
    snippet = next((quote for quote in quotes_of(cell or '') if sid and sources.holds(sid, quote)), '')
    if not snippet and kind == 'email' and sid and sources.holds(sid, value):
        snippet = value
    return {'person': person, 'kind': kind, 'value': value, 'source': sid, 'snippet': snippet, 'notes': cell or ''}


def migrate(old_people, old_identities, old_affiliations, old_rejections, results, searches, worklist, sources,
            excerpt, now=None):
    """The new registers from the old rows (as csv.DictReader reads them) and the files of plan 2a.

    `results` are the lines of capture-results.jsonl, `searches` maps each commit search to its commits,
    `worklist` are the lines of worklist.jsonl, `sources` maps the ids of the source register to their rows,
    and `excerpt(id)` is the text of a source's excerpt.
    """
    found = _Sources(results, worklist, sources, excerpt, now or datetime.now(UTC))
    migrated = Migrated()
    migrated.people = sorted(({'id': row['id'], 'name': row['name']} for row in old_people),
                             key=lambda row: row['id'])
    identities = []
    for row in old_people:
        kind, value = ('github', row['github']) if row['github'] else ('name', row['name'])
        identities.append(_identity(row['id'], kind, value, row['source'], found, searches))
    for row in old_identities:
        kind = 'github-alias' if row['kind'] == 'login' else row['kind']
        identities.append(_identity(row['person'], kind, row['value'], row['source'], found, searches))
    keys = [(row['person'], row['kind'], row['value'].casefold()) for row in identities]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ValueError(f'identities twice: {duplicates}')
    migrated.identities = sorted(identities, key=lambda row: (row['person'], row['kind'], row['value']))

    citations = _Citations()
    affiliations = {}  # id -> row

    def affiliation(row, status, checked, notes):
        aid = affiliation_id(row['person'], row['organisation'], row['from'], row['to'])
        if aid in affiliations:
            raise ValueError(f'two affiliations with the id {aid}: {row["person"]}, {row["organisation"]}, '
                             f'{row["from"]}-{row["to"]}')
        affiliations[aid] = {'id': aid, 'person': row['person'], 'organisation': row['organisation'],
                             'from': row['from'], 'to': row['to'] or '', 'status': status,
                             'checked': checked or '', 'notes': notes or ''}
        return aid

    for row in old_affiliations:
        status = 'assumed' if 'not verified' in (row['notes'] or '').casefold() else 'stated'
        aid = affiliation(row, status, row['checked'], row['notes'])
        _cite_cell(row['source'], aid, found, searches, citations)
    for row in old_rejections:
        aid = affiliation(row, 'denied', '', row['reason'])
        _cite_cell(row['source'], aid, found, searches, citations, [(row['reason'] or '').strip()])
        for segment in split_segments(row['source'] or ''):
            for item in parse_segment(segment):
                if DECISION_URL.match(item.url):
                    sid = found.resolve(item.url, kind='decision')
                    if sid not in found.new and found.kind(sid) != 'decision':
                        migrated.kind_updates[sid] = 'decision'

    migrated.affiliations = sorted(affiliations.values(),
                                   key=lambda row: (row['person'], int(row['from']), row['organisation']))
    migrated.citations = citations.rows()
    migrated.new_sources = [found.new[sid] for sid in sorted(found.new)]
    migrated.new_excerpts = {sid: found.excerpts[sid] for sid in sorted(found.excerpts)}
    migrated.kind_updates = dict(sorted(migrated.kind_updates.items()))
    return migrated


def summary(migrated):
    """What the migration writes, in a few lines."""
    with_snippet = sum(bool(row['snippet']) for row in migrated.citations)
    identities_with_snippet = sum(bool(row['snippet']) for row in migrated.identities)
    statuses = {}
    for row in migrated.affiliations:
        statuses[row['status']] = statuses.get(row['status'], 0) + 1
    return '\n'.join([
        f'people: {len(migrated.people)}',
        f'identities: {len(migrated.identities)} ({identities_with_snippet} with a snippet)',
        f'affiliations: {len(migrated.affiliations)} '
        f'({", ".join(f"{status} {count}" for status, count in sorted(statuses.items()))})',
        f'citations: {len(migrated.citations)}',
        f'citations with a snippet: {with_snippet}, without: {len(migrated.citations) - with_snippet}',
        f'uncaptured sources created: {len(migrated.new_sources)}',
        f'kind updates: {len(migrated.kind_updates)}',
    ])


def _read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Migrate the registers to citations of the source register.')
    parser.add_argument('--write', action='store_true',
                        help='write the new registers and sources, and delete the two proposal files')
    args = parser.parse_args(argv)
    mappings = paths.MAPPINGS_DIR
    people, identities, affiliations, rejections = (_read_csv(mappings / name) for name in OLD_FILES)
    with open(ARCHIVE / 'searches.json', encoding='utf-8') as f:
        searches = json.load(f)
    register = load_sources()
    migrated = migrate(people, identities, affiliations, rejections, _read_jsonl(ARCHIVE / 'capture-results.jsonl'),
                       searches, _read_jsonl(ARCHIVE / 'worklist.jsonl'),
                       {sid: asdict(source) for sid, source in register.items()}, read_excerpt)
    print(summary(migrated))
    if not args.write:
        return 0
    # The sources first: a failure part-way leaves extra sources, never registers citing missing ones
    for row in migrated.new_sources:
        write_source(Source(row['id'], row['kind'], row['title'], date.fromisoformat(row['date']), row['url'],
                            row['archive_url'] or None,
                            datetime.strptime(row['fetched'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC),
                            row['notes']))
        add_passage(row['id'], migrated.new_excerpts[row['id']])
    for sid, kind in migrated.kind_updates.items():
        write_source(replace(register[sid], kind=kind))
    _write_csv(mappings / 'people.csv', PEOPLE_FIELDS, migrated.people)
    _write_csv(mappings / 'identities.csv', IDENTITY_FIELDS, migrated.identities)
    _write_csv(mappings / 'affiliations.csv', AFFILIATION_FIELDS, migrated.affiliations)
    _write_csv(mappings / 'citations.csv', CITATION_FIELDS, migrated.citations)
    for name in PROPOSAL_FILES:
        (mappings / name).unlink(missing_ok=True)
    print('written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
