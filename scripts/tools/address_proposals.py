#!/usr/bin/env python3
"""Propose affiliations from the company email addresses in Git commits (see docs/how-to/add-an-affiliation.md).

The attribution rules accept a company address in the commits of a person as evidence for the years of those
commits, in commits made in Git only. This reads the author of every commit of the cached clones of the plone
repositories, leaves out the commits imported from Subversion, finds the person in the registers, keeps the
addresses of companies, and proposes the years as an affiliation. With --write, the earliest commit of each
proposal is captured from its clone as a source (curated/sources/), and the proposal goes to
curated/mappings/affiliations.csv as a `proposed` row citing it, with the author line of the commit as the snippet;
a reviewer turns it into a stated row. Domains that belong to no organisation are listed, so that they can be added
to the `aliases` of the organisation.

Needs the clones: `make run-changelogs` fills the cache. The capture of the evidence commits reads the clones of
the shared cache of the main checkout (PLONE_STATS_CACHE, else `.cache` of the main checkout), not those of
--cache: with another --cache, the capture may fall back to the GitHub API, which needs GITHUB_TOKEN.
"""

import argparse
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from scripts.collect.plone_changelogs import ORGANISATION, cached_repositories
from scripts.lib import git_history
from scripts.lib.capture import CaptureError, capture_commit
from scripts.lib.commit_authors import (Finder, is_company_domain, is_own_domain_for,  # noqa: F401
                                        registrable_label)
from scripts.lib.model import MAPPINGS_DIR, append_proposals, load_bot_accounts, load_registry, load_rejections
from scripts.lib.model.attribution import COUNTING
from scripts.lib.model.schema import CellTypeError

DEFAULT_SINCE = 2002


def is_own_domain(domain, person, registry):
    """Whether the domain looks like the person's own, by the name and every GitHub login the registry has for
    the person; see `is_own_domain_for`. Only for unclaimed domains."""
    return is_own_domain_for(domain, person.name, registry.logins_of(person.id))


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
    """({(person, organisation): {year: {domain: [commits, earliest (date, repository, sha, email), match]}}},
    unmapped).

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
                if is_own_domain(domain, person, registry):
                    continue
                entry = unmapped[domain]
                entry['commits'] += 1
                entry['years'].add(year)
                entry['people'].add(person.id)
                continue
            organisation, how = match
            slot = found[(person.id, organisation)][year].setdefault(domain, [0, None, how])
            slot[0] += 1
            example = (date, repository, sha, email)
            if slot[1] is None or example < slot[1]:
                slot[1] = example
    return found, unmapped


def propose(registry, found, rejected=frozenset()):
    """(proposals, conflicts). A proposal is a dict with the keys `append_proposals` takes (person, organisation,
    from, to, sources, notes), plus evidence, domain, match, commits, example and the commit to cite (`commit`:
    its address, `email`: its author's address); `cite` fills its sources.

    rejected: {(person, organisation, year)} that a reviewer turned down, the `denied` affiliations.
    """
    proposals, conflicts = [], []
    for (person, organisation), by_year in sorted(found.items()):
        own = [a for a in registry.affiliations if a.person == person and a.status in COUNTING]
        same = {y for y in by_year if any(a.organisation == organisation and a.covers(y) for a in own)}
        turned_down = {y for y in by_year if (person, organisation, y) in rejected}
        for first, last in _runs(set(by_year) - same - turned_down):
            years = range(first, last + 1)
            first_slots = by_year[first].items()
            domain, (_, (_, repository, sha, email), how) = min(first_slots, key=lambda item: (item[1][1], item[0]))
            repository = repository.removesuffix('.git')
            url = f'https://github.com/{ORGANISATION}/{repository}/commit/{sha}'
            evidence = f'Company address @{domain} in commits {_years(first, last)} (example: {url})'
            proposals.append({
                'person': person, 'organisation': organisation, 'from': first, 'to': last,
                'sources': [], 'notes': evidence, 'evidence': evidence,
                'domain': domain, 'match': how,
                'commits': sum(v[0] for y in years for v in by_year[y].values()),
                'example': f'{repository}@{sha[:10]}', 'commit': url, 'email': email,
            })
            for other in sorted({a.organisation for a in own if a.organisation != organisation}):
                overlap = [y for y in years if any(a.organisation == other and a.covers(y) for a in own)]
                for start, end in _runs(overlap):
                    conflicts.append({'person': person, 'from': start, 'to': end, 'proposed': organisation,
                                      'existing': other})
    return proposals, conflicts


def _years(first, last):
    return str(first) if first == last else f'{first}-{last}'


def cite(proposals, **options):
    """(the proposals with their sources, [(proposal, reason)] of those whose commit could not be captured).

    The commit of each proposal is captured as a source (`capture_commit`; from the clone when there is one), and
    cited with the line of its author's address as the snippet, and the notes of `citation_notes` if any.
    `options` go to the capture.
    """
    cited, failed = [], []
    for proposal in proposals:
        if not proposal.get('commit'):
            failed.append((proposal, 'no commit to cite'))
            continue
        try:
            source, snippet = capture_commit(proposal['commit'], proposal.get('email') or '',
                                             names=proposal.get('names', ()), **options)
        except CaptureError as error:
            failed.append((proposal, str(error)))
            continue
        cited.append({**proposal, 'sources': [(source, snippet, proposal.get('citation_notes'))]})
    return cited, failed


def not_captured(failed):
    """The Markdown section of the proposals that were not written, because their commit was not captured."""
    lines = ['', '## Not captured', '',
             'Proposals not written: their commit could not be captured as a source. Run again to retry.', '',
             '| Person | Organisation | Years | Commit | Reason |', '|---|---|---|---|---|']
    lines += [f"| {p['person']} | {p['organisation']} | {_years(p['from'], p['to'])} | {p.get('commit') or ''} "
              f"| {reason} |" for p, reason in failed]
    return '\n'.join(lines) + '\n'


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
    """Gather, propose, and (with write) capture the commits and add the proposed affiliations; return (report,
    proposals added)."""
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
    proposals, conflicts = propose(registry, found, load_rejections(mappings_dir))
    text = report(proposals, conflicts, unmapped)
    if not write:
        return text, []
    cited, failed = cite(proposals)
    if failed:
        text += not_captured(failed)
    return text, append_proposals(cited, mappings_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--person', action='append', default=[], metavar='ID',
                        help='only this person (repeat for several)')
    parser.add_argument('--since', type=int, default=DEFAULT_SINCE, help='ignore commits before this year')
    parser.add_argument('--cache', default=git_history.CACHE_DIR,
                        help='directory of the clones whose authors are read (default: .cache/repositories of the '
                             'current directory); the capture of the evidence commits '
                             'reads the clones of the shared cache (PLONE_STATS_CACHE) and may use the GitHub API')
    parser.add_argument('--write', action='store_true',
                        help='capture the example commits as sources and add the proposals to affiliations.csv as '
                             'proposed rows citing them')
    args = parser.parse_args(argv)
    try:
        text, added = run(args.cache, args.since, args.person, args.write)
    except CellTypeError as error:  # a cell of a curated file has the wrong type: its own message says which
        print(error, file=sys.stderr)
        sys.exit(1)
    except ValueError as error:  # a proposal whose id an affiliation has already: append_proposals wrote nothing
        print(f'Nothing written: {error}', file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(text)
    if args.write:
        print(f'\nWrote {len(added)} new proposals to affiliations.csv.')


if __name__ == '__main__':
    main()
