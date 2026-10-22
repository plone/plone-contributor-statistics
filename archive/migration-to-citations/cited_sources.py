#!/usr/bin/env python3
"""The work list of the sources the mapping files cite, for `python -m scripts.tools.capture --batch`.

Migration code for plan 2c, which turns the free-text `source` cells of the mapping files into citations of the
source register: it is archived to archive/ after its last use, as scripts/tools/migrate_data_structure.py was.

It reads every cell that cites sources (people.source, identities.source, affiliations.source and .notes,
rejected_proposals.source and .reason) of the registers as they were before plan 2c, with plain csv, since their
schemas went away with the switch (`load_old_registers`), and splits it into segments at "; " outside quotes.
Every address gets the quotes in front of the first address of its segment (a live address and its archived
copy alike), then every other quote of its cell: the capture keeps only the quotes it finds in a source, so its
results tell which quote belongs to which address. The work list has one line per distinct address with its
quotes, the names to look for when no quote is found (the person's names, and the organisation's for an
affiliation or a rejected proposal; a name with a trailing bracket also without it), and a kind hinted by the
label. A GitHub commit search is no source: the
first three commits it finds are, with the names of the person whose cell cites the search. The review file
lists the segments with quotes but no address and the addresses that got their quotes only from elsewhere in
their cell.

Needs GITHUB_TOKEN in the environment for searches that are not in the cache yet; the search allows 30 requests
a minute.
"""

import argparse
import csv
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

from scripts.lib import paths
from scripts.lib.capture import CaptureError, github_session
from scripts.lib.capture.fetch import cache_dir
from scripts.lib.github_api import GitHubAPIError, github_get
from scripts.lib.model import split_set

URL = re.compile(r'https?://[^\s;"<>]+')
QUOTE_MARK = re.compile(r'(?<!\\)"')  # a backslash-escaped quote mark is part of the quote
SEGMENT_END = re.compile(r';\s')
CUT_SHORT = '…:'  # the migration cut long labels with "…:", which leaves a quote without its end
SEARCH_API = 'https://api.github.com/search/commits'
SEARCH_CACHE = 'github-search'
SEARCH_COMMITS = 3
PACE = 2.5  # seconds between searches: the search allows 30 requests a minute
TRAILING_BRACKET = re.compile(r'^(.*\S)\s*\([^()]*\)$')  # "Rocky Burt (sprint leaders)"


def _old_rows(path):
    try:
        with open(path, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def load_old_registers(mappings_dir=paths.MAPPINGS_DIR):
    """(registry, rejections) of the registers as they were before plan 2c, read with plain csv.

    The registry has `people` ({id: person with id, name, source}), `identities` (person, kind, value, source),
    `affiliations` (person, organisation, source, notes) and `organisations` ({id: organisation with name and
    aliases}); the rejections are the rows of rejected_proposals.csv, [] without the file.
    """
    mappings_dir = Path(mappings_dir)
    people = {row['id']: SimpleNamespace(id=row['id'], name=row['name'], source=row['source'] or None)
              for row in _old_rows(mappings_dir / 'people.csv')}
    identities = [SimpleNamespace(person=row['person'], kind=row['kind'], value=row['value'],
                                  source=row['source'] or None) for row in _old_rows(mappings_dir / 'identities.csv')]
    affiliations = [SimpleNamespace(person=row['person'], organisation=row['organisation'],
                                    source=row['source'] or None, notes=row['notes'] or None)
                    for row in _old_rows(mappings_dir / 'affiliations.csv')]
    organisations = {row['id']: SimpleNamespace(id=row['id'], name=row['name'], aliases=split_set(row['aliases']))
                     for row in _old_rows(mappings_dir / 'organisations.csv')}
    registry = SimpleNamespace(people=people, identities=identities, affiliations=affiliations,
                               organisations=organisations)
    return registry, _old_rows(mappings_dir / 'rejected_proposals.csv')


@dataclasses.dataclass(frozen=True)
class Cited:
    """An address cited in a segment, with the quotes in front of the segment's first address and its label."""
    url: str
    quotes: tuple[str, ...]
    label: str


def _quote_spans(text):
    """(start, end, quote) of each quoted passage of the text; the span includes the quote marks.

    A quote mark pairs with the next one, unless the text up to there holds "…:": then the migration cut the
    quote short, and the quote is its text up to the "…", the span ending with it. A last unpaired quote mark
    that is not cut short is no quote mark.
    """
    marks = [match.start() for match in QUOTE_MARK.finditer(text)]
    spans, index = [], 0
    while index < len(marks):
        start = marks[index]
        end = marks[index + 1] if index + 1 < len(marks) else len(text)
        cut = text.find(CUT_SHORT, start, end)
        if cut != -1:
            spans.append((start, cut + 1, _clean(text[start + 1:cut]).rstrip(' .…')))
            index += 1
        elif index + 1 < len(marks):
            spans.append((start, end + 1, _clean(text[start + 1:end])))
            index += 2
        else:
            break
    return spans


def _clean(quote):
    return quote.replace('\\"', '"').strip()


def _inside(position, spans):
    return any(start <= position < end for start, end, _ in spans)


def quotes_of(text):
    """Every quote of the text, distinct, in order."""
    quotes = []
    _add(quotes, [quote for _, _, quote in _quote_spans(text) if quote])
    return quotes


def split_segments(cell: str) -> list[str]:
    """The segments of a cell: its parts between a semicolon and whitespace, outside double quotes."""
    spans = _quote_spans(cell)
    segments, start = [], 0
    for match in SEGMENT_END.finditer(cell):
        if not _inside(match.start(), spans):
            segments.append(cell[start:match.start()])
            start = match.end()
    segments.append(cell[start:])
    return [segment.strip() for segment in segments if segment.strip()]


def _trim(url):
    """The address without the punctuation of the sentence around it."""
    while url and (url[-1] in '.,:' or (url[-1] == ')' and url.count('(') < url.count(')'))):
        url = url[:-1]
    return url


def parse_segment(segment: str) -> list[Cited]:
    """Every address of the segment that stands outside quotes, each with the segment's quotes and label.

    The quotes are those that end before the first address; the label is the rest of the text before it.
    """
    spans = _quote_spans(segment)
    found = [(match.start(), _trim(match.group())) for match in URL.finditer(segment)
             if not _inside(match.start(), spans)]
    if not found:
        return []
    first = found[0][0]
    quotes = []
    _add(quotes, [quote for _, end, quote in spans if end <= first and quote])
    outside, position = [], 0
    for start, end, _ in spans:
        if end <= first:
            outside.append(segment[position:start])
            position = end
    outside.append(segment[position:first])
    label = re.sub(r'\s+', ' ', ' '.join(outside)).strip(' :,;').rstrip(' (:,;').lstrip(' ):,;')
    return [Cited(url, tuple(quotes), label) for _, url in found]


def kind_hint(url: str, label: str) -> str | None:
    """The kind of source the label names, or None: the capture adapters decide then."""
    label = label.casefold()
    if 'speaker page' in label:
        return 'speaker-page'
    if 'github profile' in label:
        return 'profile'
    return None


def is_search(url):
    """True for a GitHub commit search, such as https://github.com/search?q=author%3Ax&type=commits."""
    parts = urllib.parse.urlsplit(url)
    return ((parts.hostname or '').lower() == 'github.com' and parts.path.rstrip('/') == '/search'
            and urllib.parse.parse_qs(parts.query).get('type') == ['commits'])


def _add(values, new):
    for value in new:
        if value not in values:
            values.append(value)


def _with_bare_names(names):
    """The names, each followed by its form without a trailing bracket, such as a role, when it has one."""
    result = []
    for name in names:
        bare = TRAILING_BRACKET.match(name)
        _add(result, [name, bare.group(1)] if bare else [name])
    return result


def _collect(registry, rejections):
    """({address: work-list item}, {search address: [person names]}, [review entries]) of the cells that cite.

    An address gets the quotes of its own segment first, then every other quote of its cell: the capture keeps
    only the quotes it finds in the source, so the results show which quote belongs to which address.
    """
    name_identities = {}
    for identity in registry.identities:
        if identity.kind == 'name':
            name_identities.setdefault(identity.person, []).append(identity.value)

    def person_names(person_id):
        person = registry.people.get(person_id)
        names = [person.name] if person else []
        _add(names, name_identities.get(person_id, []))
        return _with_bare_names(names)

    def organisation_names(org_id):
        organisation = registry.organisations.get(org_id)
        return _with_bare_names([organisation.name, *organisation.aliases]) if organisation else []

    cells = []  # (cell, file, column, person id, organisation id or None)
    cells += [(p.source, 'people.csv', 'source', p.id, None) for p in registry.people.values()]
    cells += [(i.source, 'identities.csv', 'source', i.person, None) for i in registry.identities]
    cells += [(getattr(a, column), 'affiliations.csv', column, a.person, a.organisation)
              for a in registry.affiliations for column in ('source', 'notes')]
    cells += [(row[column], 'rejected_proposals.csv', column, row['person'], row['organisation'])
              for row in rejections for column in ('source', 'reason')]
    items, searches, review, reviewed = {}, {}, [], set()

    def note(entry):
        key = json.dumps(entry, sort_keys=True)
        if key not in reviewed:
            reviewed.add(key)
            review.append(entry)

    for cell, file, column, person_id, org_id in cells:
        if not cell:
            continue
        own = person_names(person_id)
        names = own + [name for name in organisation_names(org_id) if name not in own] if org_id else own
        where = {'file': file, 'column': column, 'person': person_id, 'organisation': org_id}
        pool = quotes_of(cell)
        for segment in split_segments(cell):
            cited_urls = parse_segment(segment)
            if not cited_urls and quotes_of(segment):
                note({'problem': 'quotes without address', **where, 'segment': segment,
                      'quotes': quotes_of(segment)})
            for cited in cited_urls:
                if is_search(cited.url):
                    _add(searches.setdefault(cited.url, []), own)
                    continue
                quotes = list(cited.quotes)
                _add(quotes, pool)
                if quotes and not cited.quotes:
                    note({'problem': 'quotes from elsewhere in the cell', **where, 'url': cited.url,
                          'segment': segment, 'quotes': quotes})
                item = items.setdefault(cited.url, {'url': cited.url, 'quotes': [], 'names': [], 'kind': None})
                _add(item['quotes'], quotes)
                _add(item['names'], names)
                item['kind'] = item['kind'] or kind_hint(cited.url, cited.label)
    return items, searches, review


def search_urls(registry, rejections) -> list[str]:
    """The GitHub commit searches the cells cite, sorted."""
    return sorted(_collect(registry, rejections)[1])


def work_list(registry, rejections, searches: dict[str, list[str]] | None = None) -> list[dict]:
    """One item {url, quotes, names, kind} per distinct cited address, sorted by address.

    `rejections` are the rows of rejected_proposals.csv (load_old_registers). `searches` maps each commit search
    to its commits (resolve_searches): they become items with the names of the person whose cell cites the
    search; the searches themselves are no items.
    """
    items, cited_searches, _ = _collect(registry, rejections)
    for search, names in cited_searches.items():
        for url in (searches or {}).get(search, []):
            item = items.setdefault(url, {'url': url, 'quotes': [], 'names': [], 'kind': None})
            _add(item['names'], names)
    return [items[url] for url in sorted(items)]


def review(registry, rejections) -> list[dict]:
    """What plan 2c reviews by hand: segments with quotes but no address, and addresses whose own segment has no
    quote but which got quotes from elsewhere in their cell; each with its file, column, person and organisation.
    """
    return _collect(registry, rejections)[2]


def resolve_searches(urls, session, sleep=None) -> dict[str, list[str]]:
    """{search address: the addresses of its first three commits}, each search asked once and cached as JSON."""
    sleep = sleep or time.sleep  # looked up at call time, so tests can replace it
    resolved = {}
    for url in urls:
        path = os.path.join(cache_dir(SEARCH_CACHE), hashlib.sha1(url.encode('utf-8')).hexdigest() + '.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        else:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('q', [''])[0]
            data = github_get(session, SEARCH_API, {'q': query, 'per_page': SEARCH_COMMITS}, sleep=sleep).json()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=1)
            os.replace(path + '.tmp', path)
            sleep(PACE)
        resolved[url] = [item['html_url'] for item in data.get('items', [])[:SEARCH_COMMITS]]
        if not resolved[url]:
            print(f'no commits found: {url}', file=sys.stderr)
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description='Write the work list of the sources the mapping files cite.')
    parser.add_argument('--worklist', required=True, metavar='PATH', help='JSON lines file of the work list')
    parser.add_argument('--searches', required=True, metavar='PATH',
                        help='JSON file mapping each cited commit search to the commits it found')
    parser.add_argument('--review', metavar='PATH',
                        help='JSON lines file of the quotes without an address and the addresses with quotes '
                             'from elsewhere in their cell')
    args = parser.parse_args(argv)
    registry, rejections = load_old_registers()
    try:
        resolved = resolve_searches(search_urls(registry, rejections), github_session())
    except (CaptureError, GitHubAPIError) as error:
        print(f'! {error}', file=sys.stderr)
        return 1
    items = work_list(registry, rejections, resolved)
    with open(args.worklist, 'w', encoding='utf-8') as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + '\n' for item in items)
    with open(args.searches, 'w', encoding='utf-8') as f:
        json.dump(resolved, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    entries = review(registry, rejections)
    if args.review:
        with open(args.review, 'w', encoding='utf-8') as f:
            f.writelines(json.dumps(entry, ensure_ascii=False) + '\n' for entry in entries)
    commits = sum(len(found) for found in resolved.values())
    print(f'{len(items)} items, {sum(bool(item["quotes"]) for item in items)} with quotes, '
          f'{sum(item["kind"] is not None for item in items)} with a kind hint; '
          f'{len(resolved)} searches resolved to {commits} commits, '
          f'{sum(not found for found in resolved.values())} without results', file=sys.stderr)
    print(f'to review: {sum(e["problem"] == "quotes without address" for e in entries)} segments with quotes '
          f'but no address, {sum(e["problem"] == "quotes from elsewhere in the cell" for e in entries)} '
          f'addresses with quotes from elsewhere in their cell', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
