#!/usr/bin/env python3
"""Propose affiliations from the GitHub commit search (see docs/how-to/add-an-affiliation.md).

The migration to the registers kept today's organisation for every year of a person's activity, as rows marked
"not verified". This looks for dated evidence for those years, with two queries of the GitHub commit search for
each person and year:

1. the commits of the person in the year, in all public repositories: a company address in them is evidence for
   the organisation it belongs to, as in the commits of the cached clones (see address_proposals);
2. when that finds no organisation: commits of the person in the year in the GitHub organisation of an
   organisation of the person (the `github` column of organisations.csv).

The people are those with a login and an `assumed` affiliation, or those given with --person. The
years are those of the rows in which the person has commits or pull requests in the collected data. Every
response is cached, so that an interrupted run resumes. The proposals go to curated/mappings/affiliations.csv as
`proposed` rows (with --write); a reviewer turns them into stated rows.

Needs a GitHub token in the environment variable GITHUB_TOKEN. The search allows 30 requests a minute.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from urllib.parse import quote

import requests

from scripts.lib import paths
from scripts.lib.github_api import github_get
from scripts.lib.model import MAPPINGS_DIR, append_proposals, load_registry, load_rejections
from scripts.lib.model.attribution import ASSUMED, COUNTING
from scripts.tools.address_proposals import _runs, _years, is_company_domain, is_own_domain

SEARCH_URL = 'https://api.github.com/search/commits'
CACHE_DIR = os.path.join('.cache', 'github-search')
LAST_YEAR = 2025  # the years before 2026 are the guessed ones
PACE = 2.5  # seconds between requests: the search allows 30 a minute, and a secondary limit watches bursts
PER_PAGE = 100
CONTRIBUTORS_FILE = re.compile(r'^(\d{4})-plone-contributors\.csv$')


def make_session():
    """A session with the token from GITHUB_TOKEN, as the collectors use it; stops without a token."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise SystemExit('Set GITHUB_TOKEN in the environment: the commit search needs a token.')
    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'})
    return session


class Searcher:
    """Commit searches that are paced, and cached as JSON files."""

    def __init__(self, cache, session=None, sleep=None, refresh=False):
        # Look up time.sleep at call time, so tests can replace it
        self.cache, self.refresh, self.sleep = cache, refresh, time.sleep if sleep is None else sleep
        self._session = session
        self.requests = 0

    def search(self, name, query, **params):
        """The JSON of a search, from the cache file `name` or from the API."""
        path = os.path.join(self.cache, name)
        if not self.refresh and os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        if self._session is None:
            self._session = make_session()
        print(f'  search {self.requests + 1}: {query}', file=sys.stderr)
        response = github_get(self._session, SEARCH_URL, {'q': query, **params}, sleep=self.sleep)
        data = response.json()
        self.requests += 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=1)
        self.sleep(PACE)
        return data


def active_years(contributors_dir=paths.CONTRIBUTORS_DIR):
    """{year: {username in lower case}} of the logins with commits or pull requests in the collected files."""
    result = {}
    for name in sorted(os.listdir(contributors_dir)):
        found = CONTRIBUTORS_FILE.match(name)
        if not found:
            continue
        with open(os.path.join(contributors_dir, name), newline='', encoding='utf-8') as f:
            result[int(found.group(1))] = {
                row['username'].casefold() for row in csv.DictReader(f)
                if int(row['total_commits'] or 0) + int(row['total_pull_requests'] or 0) > 0}
    return result


def is_guess(affiliation):
    """Whether the row is a guess: an `assumed` range (the migration's "not verified" rows)."""
    return affiliation.status == ASSUMED


def _counting(registry, person_id):
    """The stated and assumed affiliations of the person."""
    return [a for a in registry.affiliations if a.person == person_id and a.status in COUNTING]


def targets(registry, people, all_years, activity, last_year=LAST_YEAR):
    """{person id: [years]} to query: years of the assumed rows (of all rows for given people)."""
    result = {}
    for person in registry.people.values():
        login = registry.github_of(person.id)
        if not login or (people and person.id not in people):
            continue
        rows = [a for a in _counting(registry, person.id) if people or is_guess(a)]
        years = {y for a in rows for y in range(a.from_year, min(a.to_year or last_year, last_year) + 1)}
        if not all_years:
            years = {y for y in years if login.casefold() in activity.get(y, set())}
        if years:
            result[person.id] = sorted(years)
    return result


def candidates(registry, person, year):
    """The organisations of the person in the year and the neighbouring years: the guess and recorded ones."""
    found = []
    for affiliation in _counting(registry, person):
        if any(affiliation.covers(y) for y in (year - 1, year, year + 1)):
            organisation = registry.organisations[affiliation.organisation]
            if organisation.kind == 'organisation' and organisation not in found:
                found.append(organisation)
    return found


def classify(registry, person, data):
    """({organisation: {domain: [commits, earliest (date, url), how]}}, {domain: commits}) of a search response."""
    matched = defaultdict(dict)
    unmapped = defaultdict(int)
    for item in data.get('items', []):
        commit = item.get('commit', {})
        email = (commit.get('author') or {}).get('email') or ''
        if '@' not in email:
            continue
        domain = email.rsplit('@', 1)[1].lower().strip()
        if not is_company_domain(domain):
            continue
        match = registry.match_domain(domain)
        if match is None:
            if not is_own_domain(domain, person, registry.logins_of(person.id)):
                unmapped[domain] += 1
            continue
        organisation, how = match
        date = (commit.get('committer') or commit.get('author') or {}).get('date') or ''
        slot = matched[organisation].setdefault(domain, [0, None, how])
        slot[0] += 1
        if slot[1] is None or (date, item['html_url']) < slot[1]:
            slot[1] = (date, item['html_url'])
    return matched, unmapped


def search_url(login, handle, year):
    """The page of the commit search that shows what query 2 counted."""
    query = f'author:{login} org:{handle} committer-date:{year}-01-01..{year}-12-31'
    return 'https://github.com/search?q=' + quote(query, safe='.-').replace('%20', '+') + '&type=commits'


def gather(registry, searcher, wanted):
    """Run the queries; return (evidence, unmapped, open_guesses).

    evidence: {(person, organisation, kind): {year: detail}}; kind is 'address' (detail: {domain: [commits,
    (date, url), how]}) or 'organisation' (detail: commits). unmapped: {domain: {'commits', 'years', 'people'}}.
    open_guesses: {organisation: person-years} of the organisations without a handle that query 1 left open.
    """
    evidence = defaultdict(dict)
    unmapped = defaultdict(lambda: {'commits': 0, 'years': set(), 'people': set()})
    open_guesses = defaultdict(int)
    for person_id, years in sorted(wanted.items()):
        person = registry.people[person_id]
        login = registry.github_of(person_id)
        for year in years:
            span = f'committer-date:{year}-01-01..{year}-12-31'
            data = searcher.search(f'{login}/{year}.json', f'author:{login} {span}',
                                   sort='committer-date', order='asc', per_page=PER_PAGE)
            matched, others = classify(registry, person, data)
            for domain, commits in others.items():
                entry = unmapped[domain]
                entry['commits'] += commits
                entry['years'].add(year)
                entry['people'].add(person_id)
            for organisation, slots in matched.items():
                evidence[(person_id, organisation, 'address')][year] = slots
            if matched:
                continue
            for organisation in candidates(registry, person_id, year):
                handle = organisation.github
                if not handle:
                    open_guesses[organisation.id] += 1
                    continue
                data = searcher.search(f'{login}/{year}-org-{handle}.json',
                                       f'author:{login} org:{handle} {span}', per_page=1)
                if data.get('total_count', 0) > 0:
                    evidence[(person_id, organisation.id, 'organisation')][year] = data['total_count']
    return evidence, unmapped, open_guesses


def propose(registry, evidence, rejected=frozenset()):
    """(proposals, conflicts). A proposal is a dict with the keys `append_proposals` takes (person, organisation,
    from, to, sources, notes), plus evidence, found, commits and example.

    rejected: {(person, organisation, year)} that a reviewer turned down, the `denied` affiliations.
    """
    proposals, conflicts = [], []
    for (person, organisation, kind), by_year in sorted(evidence.items()):
        own = _counting(registry, person)
        # An affiliation of the same organisation covers a year, unless it is a guess: that is what this is for
        same = {y for y in by_year
                if any(a.organisation == organisation and a.covers(y) and not is_guess(a) for a in own)}
        turned_down = {y for y in by_year if (person, organisation, y) in rejected}
        login = registry.github_of(person)
        for first, last in _runs(set(by_year) - same - turned_down):
            years = range(first, last + 1)
            if kind == 'address':
                domain, (_, (_, url), how) = min(by_year[first].items(), key=lambda item: (item[1][1], item[0]))
                commits = sum(v[0] for y in years if y in by_year for v in by_year[y].values())
                evidence_text = (f'Company address @{domain} in commits {_years(first, last)} '
                                 f'found by the GitHub commit search (example: {url})')
                found, example = f'address @{domain} ({how})', url
            else:
                handle = registry.organisations[organisation].github
                commits = sum(by_year.get(y, 0) for y in years)
                url = search_url(login, handle, first)
                evidence_text = (f'Commits in the GitHub organisation @{handle} in {_years(first, last)} '
                                 f'({by_year[first]} in {first}; search: {url})')
                found, example = f'organisation @{handle}', url
            proposals.append({
                'person': person, 'organisation': organisation, 'from': first, 'to': last,
                'sources': [], 'notes': evidence_text,
                'evidence': evidence_text, 'found': found, 'commits': commits, 'example': example})
            for other in sorted({a.organisation for a in own if a.organisation != organisation}):
                overlap = [y for y in years if any(a.organisation == other and a.covers(y) for a in own)]
                for start, end in _runs(overlap):
                    guess = all(is_guess(a) for a in own if a.organisation == other
                                and any(a.covers(y) for y in range(start, end + 1)))
                    conflicts.append({'person': person, 'from': start, 'to': end, 'proposed': organisation,
                                      'existing': other, 'guess': guess})
    return proposals, conflicts


def report(proposals, conflicts, unmapped, open_guesses):
    """The Markdown report."""
    lines = ['# Affiliations from the GitHub commit search', '', '## Proposals', '']
    if proposals:
        lines += ['| Person | Organisation | Years | Commits | Found by | Example |', '|---|---|---|---|---|---|']
        lines += [f"| {p['person']} | {p['organisation']} | {_years(p['from'], p['to'])} | {p['commits']} "
                  f"| {p['found']} | {p['example']} |" for p in proposals]
    else:
        lines.append('None.')
    lines += ['', '## Conflicts', '',
              'Proposed years that another organisation covers in affiliations.csv; a guess is an assumed row.',
              '']
    if conflicts:
        lines += ['| Person | Years | Proposed | Existing | Existing is a guess |', '|---|---|---|---|---|']
        lines += [f"| {c['person']} | {_years(c['from'], c['to'])} | {c['proposed']} | {c['existing']} "
                  f"| {'yes' if c['guess'] else 'no'} |" for c in conflicts]
    else:
        lines.append('None.')
    lines += ['', '## Unmapped domains', '',
              'Add a domain to the `aliases` of its organisation in organisations.csv to have it proposed.', '']
    if unmapped:
        lines += ['| Domain | Commits | Years | People |', '|---|---|---|---|']
        for domain, entry in sorted(unmapped.items(), key=lambda item: (-item[1]['commits'], item[0])):
            years = _years(min(entry['years']), max(entry['years']))
            lines.append(f"| {domain} | {entry['commits']} | {years} | {len(entry['people'])} |")
    else:
        lines.append('None.')
    lines += ['', '## Organisations without a handle', '',
              'Guessed organisations of the person-years that no address explained. '
              'Fill the `github` column of organisations.csv to have their GitHub organisation searched.', '']
    if open_guesses:
        lines += ['| Organisation | Person-years |', '|---|---|']
        lines += [f'| {organisation} | {count} |' for organisation, count in
                  sorted(open_guesses.items(), key=lambda item: (-item[1], item[0]))]
    else:
        lines.append('None.')
    return '\n'.join(lines) + '\n'


def run(people=(), all_years=False, write=False, refresh=False, cache=CACHE_DIR, mappings_dir=MAPPINGS_DIR,
        contributors_dir=paths.CONTRIBUTORS_DIR, session=None, sleep=None):
    """Query, propose, and (with write) add the proposed affiliations; return (report, proposals added)."""
    registry = load_registry(mappings_dir)
    unknown = [p for p in people if p not in registry.people]
    if unknown:
        raise SystemExit(f'Not in people.csv: {", ".join(unknown)}')
    without_login = [p for p in people if not registry.github_of(p)]
    if without_login:
        raise SystemExit(f'No GitHub login in identities.csv: {", ".join(without_login)}')
    wanted = targets(registry, set(people), all_years, active_years(contributors_dir))
    searcher = Searcher(cache, session, sleep, refresh)
    evidence, unmapped, open_guesses = gather(registry, searcher, wanted)
    proposals, conflicts = propose(registry, evidence, load_rejections(mappings_dir))
    text = report(proposals, conflicts, unmapped, open_guesses)
    added = append_proposals(proposals, mappings_dir) if write else []
    return text, added


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--person', action='append', default=[], metavar='ID',
                        help='only this person, with all rows (repeat for several)')
    parser.add_argument('--all-years', action='store_true',
                        help='query every year of the rows, not only those with commits or pull requests')
    parser.add_argument('--write', action='store_true', help='add the proposals to affiliations.csv as proposed rows')
    parser.add_argument('--refresh', action='store_true', help='ignore the cache and ask GitHub again')
    parser.add_argument('--cache', default=CACHE_DIR, help='directory of the cached responses')
    args = parser.parse_args(argv)
    text, added = run(args.person, args.all_years, args.write, args.refresh, args.cache)
    sys.stdout.write(text)
    if args.write:
        print(f'\nWrote {len(added)} new proposals to affiliations.csv.')


if __name__ == '__main__':
    main()
