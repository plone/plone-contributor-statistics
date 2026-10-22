#!/usr/bin/env python3
"""Collect the mail domains of the commit authors per person and year.

The domain of the address a person committed with says where they worked at the time, which the attribution
rules accept as evidence (docs/explanation/attribution.md). This reads the author of every commit in the
cached clones of the plone repositories, leaves out merge commits, the commits imported from Subversion (the
migration assigned their addresses) and the excluded repositories, finds the person in the registers, skips bots
and authors that no register identifies, and counts the commits per person, domain and year of the author date.
Each change counts once, see `collect`. Only the domain is stored, never the local part of an address, and no
names of machines (`domain_of`); see docs/reference/data-files.md.

Needs the clones: `make run-changelogs` fills the cache.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from scripts.collect.plone_changelogs import FIRST_YEAR, ORGANISATION, cached_repositories
from scripts.lib import git_history, paths
from scripts.lib.commit_authors import Finder, domain_of
from scripts.lib.model import load_bot_accounts, load_excluded_repositories, load_registry

COLUMNS = ['username', 'domain', 'commits']


def collect(clones, finder, registry, workers=8):
    """{year: Counter[(username, domain)]} of the commits in the clones, [(name, path)].

    A change counts once, as in the commit statistics (docs/explanation/counting-rules.md): a commit on several
    branches, the "[fc]" copies in buildout.coredev, and the commits with the same author date and subject in one
    repository. Unlike the commit statistics, a commit that two clones share counts once as well.
    """
    def read(clone):
        return git_history.read_authors(clone[1], converted=False, merges=False, duplicates=False)

    counts = defaultdict(Counter)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(read, clones))
    seen = set()
    for authors in results:
        for sha, email, name, commit_date in authors:
            if sha in seen:
                continue
            seen.add(sha)
            domain = domain_of(email)
            if domain is None:
                continue
            person = finder.person(email, name)
            if person is not None:
                counts[int(commit_date[:4])][(registry.username_of(person), domain)] += 1
    return dict(counts)


def write(counts, years):
    """One file per year, the header only for a year without commits."""
    paths.COMMIT_DOMAINS_DIR.mkdir(parents=True, exist_ok=True)
    for year in years:
        rows = sorted(((user, domain, n) for (user, domain), n in counts.get(year, {}).items()),
                      key=lambda row: (row[0], -row[2], row[1]))
        with open(paths.commit_domains_file(year), 'w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(COLUMNS)
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cache', default=git_history.CACHE_DIR, help='directory of the clones')
    parser.add_argument('--first-year', type=int, default=FIRST_YEAR, help=f'first year to write (default: {FIRST_YEAR})')
    parser.add_argument('--last-year', type=int, default=date.today().year,
                        help='last year to write (default: the current year)')
    args = parser.parse_args(argv)
    if args.first_year > args.last_year:
        parser.error('--first-year must not be after --last-year')
    excluded = load_excluded_repositories()
    names = [name for name, _ in cached_repositories(args.cache) if name not in excluded]
    if not names:
        raise SystemExit(f'No clones in {args.cache}/{ORGANISATION}; fill the cache with `make run-changelogs`.')
    registry = load_registry()
    finder = Finder(registry, load_bot_accounts())
    clones = [(name, os.path.join(args.cache, ORGANISATION, f'{name}.git')) for name in names]
    counts = collect(clones, finder, registry)
    years = range(args.first_year, args.last_year + 1)
    write(counts, years)
    print(f'{len(clones)} repositories, {sum(sum(c.values()) for c in counts.values())} commits; '
          f'wrote {paths.commit_domains_file(years[0])} to {paths.commit_domains_file(years[-1])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
