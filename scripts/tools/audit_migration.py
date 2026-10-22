#!/usr/bin/env python3
"""Audit the migration to citations (plan 2c): nothing of the old registers is lost in the new ones.

Migration code, archived to archive/ with scripts/tools/migrate_registers.py after its one use. It reads the old
registers and the files of the capture (plan 2a) from git, at the commit before the migration, and the new
registers through the model, and checks, per old row:

- people: the person keeps the id and the name; the old `github` is an identity of kind `github` (else the name
  an identity of kind `name`) whose notes are the old `source` cell, unchanged.
- identities: each row is an identity of the same person and value (kind `login` became `github-alias`) whose
  notes are the old `source` cell, unchanged.
- An identity with addresses in its old cell cites the source of one of them (a commit search through its
  commits).
- affiliations and rejected proposals: the row has the affiliation of its id (`affiliation_id`) with the same
  person, organisation, years and `checked`, the status the migration gives it (`denied` for a rejection,
  `assumed` for notes that say `not verified`, else `stated`), and its `notes` (a rejection's `reason`)
  unchanged. Of its `source` cell:
  - every segment (`split_segments`) is in the notes of one of the affiliation's citations, ignoring
    whitespace, and the segments hold all of the cell's text;
  - every address, also one inside a quote, is in those notes or is the address or archived address of a source
    the affiliation cites (the only normalisation: `http://web.archive.org` read as `https://`);
  - every cited address (outside quotes) is the address of a source the affiliation cites: the source the
    capture recorded for it, or one with that address; a commit search through each of its commits;
  - every quote is a snippet of the affiliation's citations or in their notes, and every label (the words
    before an address) is in their notes.
- open proposals: each is a `proposed` affiliation.

It prints the counts and every loss, and exits 1 when there is a loss.

Run `python -m scripts.tools.audit_migration` (`--rev` names the commit of the old files).
"""

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field

from scripts.lib import paths
from scripts.lib.model import affiliation_id, load_citations, load_registry, load_sources, normalize_url
from scripts.tools.cited_sources import (URL, _quote_spans, _trim, is_search, parse_segment, quotes_of,
                                         split_segments)

REV = 'ab0d416'  # main before the migration: the old registers and the files of the capture
OLD_FILES = {'people': 'people.csv', 'identities': 'identities.csv', 'affiliations': 'affiliations.csv',
             'rejections': 'rejected_proposals.csv', 'proposals': 'affiliation_proposals.csv'}
CAPTURE = 'archive/migration-to-sources'
HTTP_ARCHIVE = re.compile(r'http://web\.archive\.org')
WHITESPACE = re.compile(r'\s+')


@dataclass
class Report:
    """What the audit compared (`counts`) and what it found lost: (kind, row, what)."""
    counts: Counter = field(default_factory=Counter)
    losses: list = field(default_factory=list)


def _archive_https(text):
    return HTTP_ARCHIVE.sub('https://web.archive.org', text or '')


def _squash(text):
    """The text without whitespace and with Wayback addresses in https."""
    return WHITESPACE.sub('', _archive_https(text))


def _unquoted(text):
    """The text without its quotes, as a label is made of the words around them."""
    for start, end, _ in sorted(_quote_spans(text or ''), reverse=True):
        text = text[:start] + text[end:]
    return text or ''


def _text(value):
    """A cell of the new registers as the old files wrote it."""
    if value is None:
        return ''
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


class _Matcher:
    """Whether a source stands for a cited address: the source the capture recorded for it, or a source with
    that address or archived address; a commit search through its commits (or itself, when it found none)."""

    def __init__(self, results, searches, sources):
        self.recorded = {line['url']: line.get('source_id') for line in results}
        self.searches = searches
        self.sources = sources

    def is_source_of(self, url, sid):
        if self.recorded.get(url) == sid:
            return True
        source = self.sources.get(sid)
        if source is None:
            return False
        key = normalize_url(_archive_https(url))
        return any(normalize_url(_archive_https(address)) == key
                   for address in (source.url, source.archive_url) if address)

    def targets(self, url):
        """The addresses that stand for the address: a search's commits, else the address."""
        return (self.searches.get(url) or [url]) if is_search(url) else [url]

    def cited(self, url, sids):
        """Whether the sources cite the address: each of its targets by one of them."""
        return all(any(self.is_source_of(target, sid) for sid in sids) for target in self.targets(url))


def _status(row, rejected):
    if rejected:
        return 'denied'
    return 'assumed' if 'not verified' in (row['notes'] or '').casefold() else 'stated'


def _audit_cell(report, where, cell, citations, matcher):
    """Every segment, address, quote and label of the cell in the citations."""
    def lose(kind, what):
        report.losses.append((kind, where, what))

    notes = [_squash(citation.notes) for citation in citations]
    unquoted = [_squash(_unquoted(citation.notes)) for citation in citations]
    snippets = {_squash(citation.snippet) for citation in citations if citation.snippet}
    addresses = {_squash(address) for citation in citations for address in
                 (matcher.sources[citation.source].url, matcher.sources[citation.source].archive_url)
                 if citation.source in matcher.sources and address}
    sids = [citation.source for citation in citations]

    def in_notes(text):
        return any(_squash(text) in note for note in notes)

    segments = split_segments(cell)
    if _squash(';'.join(segments)) != _squash(cell):
        lose('segment', f'text outside the segments of: {cell}')
    for segment in segments:
        report.counts['segments'] += 1
        if not in_notes(segment):
            lose('segment', segment)
        for item in parse_segment(segment):
            report.counts['cited addresses'] += 1
            if not matcher.cited(item.url, sids):
                lose('cited', item.url)
            if item.label:
                report.counts['labels'] += 1
                if not in_notes(item.label) and not any(_squash(item.label) in note for note in unquoted):
                    lose('label', item.label)
    for match in URL.finditer(cell):
        url = _trim(match.group())
        report.counts['addresses'] += 1
        if not in_notes(url) and _squash(url) not in addresses:
            lose('url', url)
    for quote in quotes_of(cell):
        report.counts['quotes'] += 1
        if _squash(quote) not in snippets and not in_notes(quote) and not in_notes(quote.replace('"', '\\"')):
            lose('quote', quote)


def audit(old, new, results, searches):
    """The report of the audit of the old rows (`old`: lists of dicts as csv.DictReader reads the old files,
    by the keys of OLD_FILES) against the new registers (`new`: people, identities, affiliations and citations
    of the model, and sources {id: Source}); `results` are the lines of capture-results.jsonl and `searches`
    the commits of each search, as the migration read them."""
    report = Report()
    for name in ('people', 'identities', 'affiliations', 'rejections', 'proposals'):
        report.counts[name] = 0
    matcher = _Matcher(results, searches, new['sources'])

    def lose(kind, where, what):
        report.losses.append((kind, where, what))

    people = {person.id: person for person in new['people']}
    for row in old['people']:
        report.counts['people'] += 1
        person = people.get(row['id'])
        if person is None:
            lose('row', f'person {row["id"]}', 'missing')
        elif person.name != row['name']:
            lose('field', f'person {row["id"]}', f'name: {row["name"]} -> {person.name}')

    identities = {(identity.person, identity.kind, identity.value): identity for identity in new['identities']}
    expected = [(row['id'], 'github', row['github']) if row['github'] else (row['id'], 'name', row['name'])
                for row in old['people']]
    cells = [row['source'] or '' for row in old['people']]
    for row in old['identities']:
        expected.append((row['person'], 'github-alias' if row['kind'] == 'login' else row['kind'], row['value']))
        cells.append(row['source'] or '')
    for key, cell in zip(expected, cells):
        report.counts['identities'] += 1
        where = 'identity ' + ' '.join(key)
        identity = identities.get(key)
        if identity is None:
            lose('row', where, 'missing')
            continue
        if _text(identity.notes) != cell:
            lose('notes', where, cell)
        urls = [item.url for segment in split_segments(cell) for item in parse_segment(segment)]
        if urls and not any(matcher.is_source_of(target, identity.source)
                            for url in urls for target in matcher.targets(url)):
            lose('cited', where, _text(identity.source))

    affiliations = {affiliation.id: affiliation for affiliation in new['affiliations']}
    citations = {}
    for citation in new['citations']:
        citations.setdefault(citation.affiliation, []).append(citation)
    for kind, rejected in (('affiliations', False), ('rejections', True)):
        for row in old[kind]:
            report.counts[kind] += 1
            where = f'{"rejection" if rejected else "affiliation"} {row["person"]} {row["organisation"]} ' \
                    f'{row["from"]}-{row["to"]}'
            aid = affiliation_id(row['person'], row['organisation'], row['from'], row['to'])
            affiliation = affiliations.get(aid)
            if affiliation is None:
                lose('row', where, f'no affiliation {aid}')
                continue
            fields = {'person': (row['person'], affiliation.person),
                      'organisation': (row['organisation'], affiliation.organisation),
                      'from': (row['from'], _text(affiliation.from_year)),
                      'to': (row['to'] or '', _text(affiliation.to_year)),
                      'checked': ('' if rejected else row['checked'] or '', _text(affiliation.checked)),
                      'status': (_status(row, rejected), affiliation.status)}
            for name, (before, after) in fields.items():
                if before != after:
                    lose('field', where, f'{name}: {before} -> {after}')
            before = row['reason'] if rejected else row['notes']
            if _text(affiliation.notes) != (before or ''):
                lose('notes', where, before or '')
            _audit_cell(report, where, row['source'] or '', citations.get(aid, []), matcher)

    proposed = {(a.person, a.organisation, _text(a.from_year), _text(a.to_year))
                for a in new['affiliations'] if a.status == 'proposed'}
    for row in old['proposals']:
        report.counts['proposals'] += 1
        if (row['person'], row['organisation'], row['from'], row['to'] or '') not in proposed:
            lose('row', f'proposal {row["person"]} {row["organisation"]} {row["from"]}-{row["to"]}',
                 'no proposed affiliation')
    return report


def git_show(rev, path):
    """The text of the file at the commit."""
    return subprocess.run(['git', 'show', f'{rev}:{path}'], check=True, capture_output=True,
                          text=True, encoding='utf-8').stdout


def read_old(rev):
    """The old registers, the capture results and the searches at the commit."""
    mappings = paths.MAPPINGS_DIR.as_posix()
    old = {key: list(csv.DictReader(io.StringIO(git_show(rev, f'{mappings}/{name}'))))
           for key, name in OLD_FILES.items()}
    results = [json.loads(line) for line in git_show(rev, f'{CAPTURE}/capture-results.jsonl').splitlines()
               if line.strip()]
    searches = json.loads(git_show(rev, f'{CAPTURE}/searches.json'))
    return old, results, searches


def read_new():
    """The new registers, through the model."""
    registry = load_registry()
    return {'people': list(registry.people.values()), 'identities': registry.identities,
            'affiliations': registry.affiliations, 'citations': load_citations(), 'sources': load_sources()}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit the migration to citations: list what the new registers '
                                                 'lost of the old ones.')
    parser.add_argument('--rev', default=REV, help=f'the commit of the old registers (default {REV})')
    args = parser.parse_args(argv)
    old, results, searches = read_old(args.rev)
    report = audit(old, read_new(), results, searches)
    for name, count in report.counts.items():
        print(f'{name}: {count}')
    print(f'losses: {len(report.losses)}')
    for kind, where, what in report.losses:
        print(f'{kind}\t{where}\t{what}')
    return 1 if report.losses else 0


if __name__ == '__main__':
    sys.exit(main())
