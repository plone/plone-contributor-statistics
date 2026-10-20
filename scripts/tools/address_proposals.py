#!/usr/bin/env python3
"""Propose affiliations from the company email addresses in Git commits (see docs/how-to/add-an-affiliation.md).

The attribution rules accept a company address in the commits of a person as evidence for the years of those
commits, in commits made in Git only. This reads the author of every commit of the cached clones of the plone
repositories, leaves out the commits imported from Subversion, finds the person in the registers, keeps the
addresses of companies, and proposes the years as an affiliation. The proposals go to curated/mappings/affiliation_proposals.csv (with --write); a reviewer moves
them into affiliations.csv. Domains that belong to no organisation are listed, so that they can be added to the
`aliases` of the organisation.

Needs the clones: `make run-changelogs` fills the cache.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from scripts.collect.plone_changelogs import ORGANISATION, cached_repositories
from scripts.lib import git_history
from scripts.lib.changelogs import SVN_DOMAIN
from scripts.lib.model import MAPPINGS_DIR, append_proposals, load_bot_accounts, load_registry
from scripts.lib.model.names import fold

DEFAULT_SINCE = 2002
NOREPLY = re.compile(r'^(?:\d+\+)?(?P<login>[^@]+)@users\.noreply\.github\.com$', re.IGNORECASE)

# Domains that say nothing about an employer, see the attribution rules. A "*" stands for any top-level domain
# or part of the name: yahoo.* is yahoo.com and yahoo.co.uk. Subdomains count as well (lists.plone.org).
PERSONAL_DOMAINS = [
    'gmail.com', 'googlemail.com', 'yahoo.*', 'hotmail.*', 'outlook.*', 'live.*', 'msn.com', 'aol.com', 'gmx.*',
    'web.de', 'posteo.*', 'mailbox.org', 'protonmail.*', 'fastmail.*', 'me.com', 'mac.com', 'icloud.com',
    'free.fr', 'wanadoo.fr', 'laposte.net', 'users.noreply.github.com', 'localhost', 'localhost.localdomain',
    'plone.org', 'zope.org',
    # Mail services of internet providers: a mailbox there says nothing about an employer either
    'arcor.de', 't-online.de', 'freenet.de', 'aon.at', 'chello.at', 'bluewin.ch', 'orange.fr', 'libero.it',
    'tiscali.*', 'mail.ru', 'yandex.*',
    # Mail aliases that professional societies give their members
    'computer.org', 'acm.org', 'ieee.org',
]
_PERSONAL = re.compile(
    r'^(?:.+\.)?(?:' + '|'.join(re.escape(d).replace(r'\*', '.+') for d in PERSONAL_DOMAINS) + ')$')
MIN_NAME_PART = 4  # a name part shorter than this inside a domain label is no evidence that the domain is own
# Second-level labels under a two-letter country domain: foo.com.au, foo.co.uk, foo.ac.at
_SECOND_LEVEL = {'com', 'co', 'org', 'net', 'ac', 'gov', 'edu', 'or', 'ne', 'go', 'ltd', 'plc'}


def is_company_domain(domain):
    """Whether the domain may name an employer: not personal, not a local name, not Subversion-era."""
    domain = domain.lower().strip()
    return not (not domain or '.' not in domain or domain.endswith(('.local', '.lan', '(none)'))
                or _PERSONAL.match(domain) or SVN_DOMAIN.match(domain))


def registrable_label(domain):
    """The label that the owner of the domain chose: `foo` in foo.com, foo.com.au and mail.foo.co.uk."""
    labels = domain.lower().strip().split('.')
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return labels[-3]
    return labels[-2] if len(labels) >= 2 else labels[0]


def is_own_domain(domain, person):
    """Whether the domain looks like the person's own, which says nothing about an employer.

    Its registrable label equals the login or a whole part of the folded name, or contains a part of at
    least four letters (`leeb` in andersonleeb.com). Use it only for a domain that no organisation claims: a
    registered organisation always wins, so the company of a self-employed person is never lost.
    """
    label = fold(registrable_label(domain)).replace(' ', '')
    parts = fold(person.name).split()
    login = fold(person.github or '').replace(' ', '')
    return bool(label) and (label == login or label in parts
                            or any(len(part) >= MIN_NAME_PART and part in label for part in parts))


class Finder:
    """The person behind the author of a commit, and whether the author is a bot."""

    def __init__(self, registry, bots):
        self.registry = registry
        self.bots = {bot.casefold() for bot in bots}
        self._cache = {}

    def person(self, email, name):
        """The person, or None when the author is a bot or matches nobody. Noreply login, address, then name."""
        key = (email.lower(), name)
        if key not in self._cache:
            self._cache[key] = self._find(email, name)
        return self._cache[key]

    def _is_bot(self, login):
        return login.endswith('[bot]') or login.casefold() in self.bots

    def _find(self, email, name):
        found = NOREPLY.match(email)
        if found:
            login = found.group('login')
            if self._is_bot(login):
                return None
            person = self.registry.person_for(login=login)
            if person:
                return person
        if self._is_bot(name.strip()):
            return None
        return self.registry.person_for(email=email) or self.registry.person_for(name=name)


def _runs(years):
    """[(first, last)] of the consecutive years."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return [tuple(run) for run in runs]


def gather(clones, finder, since):
    """({(person, organisation): {year: {domain: [commits, earliest (date, repository, sha), match]}}}, unmapped).

    The unmapped domains are {domain: {'commits': n, 'years': set, 'people': set}}.
    """
    registry = finder.registry
    found = defaultdict(lambda: defaultdict(dict))
    unmapped = defaultdict(lambda: {'commits': 0, 'years': set(), 'people': set()})

    def read(clone):
        # Only commits made in Git: the migration from Subversion assigned the addresses of the imported ones
        return clone[0], git_history.read_authors(clone[1], converted=False)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(read, clones))
    for repository, authors in results:
        for sha, email, name, date in authors:
            year = int(date[:4])
            if year < since or '@' not in email:
                continue
            domain = email.rsplit('@', 1)[1].lower().strip()
            person = finder.person(email, name)
            if person is None or not is_company_domain(domain):
                continue
            match = registry.match_domain(domain)
            if match is None:
                if is_own_domain(domain, person):
                    continue
                entry = unmapped[domain]
                entry['commits'] += 1
                entry['years'].add(year)
                entry['people'].add(person.id)
                continue
            organisation, how = match
            slot = found[(person.id, organisation)][year].setdefault(domain, [0, None, how])
            slot[0] += 1
            example = (date, repository, sha)
            if slot[1] is None or example < slot[1]:
                slot[1] = example
    return found, unmapped


def propose(registry, found):
    """(proposals, conflicts). A proposal is a dict with the keys of the proposals file, plus commits and example."""
    proposals, conflicts = [], []
    for (person, organisation), by_year in sorted(found.items()):
        own = [a for a in registry.affiliations if a.person == person]
        same = {y for y in by_year if any(a.organisation == organisation and a.covers(y) for a in own)}
        for first, last in _runs(set(by_year) - same):
            years = range(first, last + 1)
            first_slots = by_year[first].items()
            domain, (_, (_, repository, sha), how) = min(first_slots, key=lambda item: (item[1][1], item[0]))
            repository = repository.removesuffix('.git')
            proposals.append({
                'person': person, 'organisation': organisation, 'from': first, 'to': last,
                'evidence': f'Company address @{domain} in commits {_years(first, last)} '
                            f'(example: https://github.com/{ORGANISATION}/{repository}/commit/{sha})',
                'domain': domain, 'match': how,
                'commits': sum(v[0] for y in years for v in by_year[y].values()),
                'example': f'{repository}@{sha[:10]}',
            })
            for other in sorted({a.organisation for a in own if a.organisation != organisation}):
                overlap = [y for y in years if any(a.organisation == other and a.covers(y) for a in own)]
                for start, end in _runs(overlap):
                    conflicts.append({'person': person, 'from': start, 'to': end, 'proposed': organisation,
                                      'existing': other})
    return proposals, conflicts


def _years(first, last):
    return str(first) if first == last else f'{first}-{last}'


def report(proposals, conflicts, unmapped):
    """The Markdown report."""
    lines = ['# Affiliations from commit addresses', '', '## Proposals', '']
    if proposals:
        lines += ['| Person | Organisation | Years | Commits | Domain | Match | Example |',
                  '|---|---|---|---|---|---|---|']
        lines += [f"| {p['person']} | {p['organisation']} | {_years(p['from'], p['to'])} | {p['commits']} "
                  f"| {p['domain']} | {p['match']} | {p['example']} |" for p in proposals]
    else:
        lines.append('None.')
    lines += ['', '## Conflicts', '', 'Proposed years that another organisation covers in affiliations.csv.', '']
    if conflicts:
        lines += ['| Person | Years | Proposed | Existing |', '|---|---|---|---|']
        lines += [f"| {c['person']} | {_years(c['from'], c['to'])} | {c['proposed']} | {c['existing']} |"
                  for c in conflicts]
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
    return '\n'.join(lines) + '\n'


def run(cache=git_history.CACHE_DIR, since=DEFAULT_SINCE, people=(), write=False, mappings_dir=MAPPINGS_DIR):
    """Gather, propose, and (with write) append to the proposals file; return (report, proposals added)."""
    if not os.path.isdir(os.path.join(cache, ORGANISATION)):
        raise SystemExit(f'No clones in {cache}/{ORGANISATION}; fill the cache with `make run-changelogs`.')
    registry = load_registry(mappings_dir)
    unknown = [p for p in people if p not in registry.people]
    if unknown:
        raise SystemExit(f'Not in people.csv: {", ".join(unknown)}')
    finder = Finder(registry, load_bot_accounts())
    clones = [(name, os.path.join(cache, ORGANISATION, f'{name}.git')) for name, _ in cached_repositories(cache)]
    found, unmapped = gather(clones, finder, since)
    if people:
        found = {key: value for key, value in found.items() if key[0] in people}
        # The domains of other people are not the business of this run
        unmapped = {d: e for d, e in unmapped.items() if e['people'] & set(people)}
    proposals, conflicts = propose(registry, found)
    text = report(proposals, conflicts, unmapped)
    added = append_proposals(proposals, mappings_dir) if write else []
    return text, added


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--person', action='append', default=[], metavar='ID',
                        help='only this person (repeat for several)')
    parser.add_argument('--since', type=int, default=DEFAULT_SINCE, help='ignore commits before this year')
    parser.add_argument('--cache', default=git_history.CACHE_DIR, help='directory of the clones')
    parser.add_argument('--write', action='store_true', help='append the proposals to affiliation_proposals.csv')
    args = parser.parse_args(argv)
    text, added = run(args.cache, args.since, args.person, args.write)
    sys.stdout.write(text)
    if args.write:
        print(f'\nWrote {len(added)} new proposals to the proposals file.')


if __name__ == '__main__':
    main()
