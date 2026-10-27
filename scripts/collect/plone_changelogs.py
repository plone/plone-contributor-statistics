#!/usr/bin/env python3
"""Collect the changelog entries per person and year (#71).

Before pull requests, Plone's changelogs said who made each change: from
mid-2003 on, an entry ends with "[name]". This collector reads the
changelog files at the tips of the same branches as the commit collector,
the default branch and the release branches, of all repositories of the
`plone` organisation except the excluded ones. It needs no file history:
the tip of a changelog holds all its entries.

The files are read from the same local clones as the commits
(scripts/lib/git_history.py). Only the trees of the branch tips and the
changelog files are fetched into them.

Each entry is dated by its release, counted once (see
scripts/lib/changelogs.py), and credited in full to every person it names.
Names are mapped to people with the registers of people and identities; names
that no identity maps are kept as written. The output has one file per year, one row
per person; see docs/reference/data-files.md.
"""

import argparse
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from dotenv import load_dotenv

from scripts.lib import changelogs, git_history, paths
from scripts.lib.addresses import mask_text
from scripts.lib.github_api import GitHubAPIError, github_get
from scripts.lib.model import load_bot_accounts, load_excluded_repositories, load_registry
from scripts.lib.tables import by_count
from scripts.lib.years import last_completed_year

ORGANISATION = 'plone'
FIRST_YEAR = 2002
COLUMNS = ['username', 'changelog_entries', 'repositories_count', 'repositories', 'changelog_names', 'matched_by']


def organisation_repositories(session):
    """[(name, default branch)] of all repositories of the organisation."""
    repositories = []
    page = 1
    while True:
        response = github_get(session, f'https://api.github.com/orgs/{ORGANISATION}/repos',
                              params={'page': page, 'per_page': 100, 'sort': 'full_name'})
        data = response.json()
        if not data:
            break
        repositories.extend((repo['name'], repo.get('default_branch') or 'main') for repo in data)
        page += 1
    return sorted(repositories)


def cached_repositories(cache_dir=git_history.CACHE_DIR):
    """[(name, default branch)] of the clones in the cache, without asking GitHub.

    The default branch is the one the clone was made with; the collector asks
    GitHub instead, because a default branch can change.
    """
    folder = os.path.join(cache_dir, ORGANISATION)
    repositories = []
    for entry in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if entry.endswith('.git'):
            path = os.path.join(folder, entry)
            head = git_history._git('symbolic-ref', 'HEAD', cwd=path).strip()
            repositories.append((entry[:-4], head.removeprefix('refs/heads/')))
    return repositories


def repository_occurrences(name, default_branch, cache_dir=git_history.CACHE_DIR, token=None, update=True):
    """Every occurrence of a changelog entry in the repository, on all counted branches."""
    path = os.path.join(cache_dir, ORGANISATION, f'{name}.git')
    if update:
        git_history.update_clone(f'https://github.com/{ORGANISATION}/{name}.git', path, token, tags=True)
    branches = git_history.list_branches(path)
    if default_branch not in branches:  # empty repository
        return []
    counted = [default_branch] + git_history.release_branches(branches, default_branch)
    files = git_history.files_at_tips(path, counted, lambda file: changelogs.is_changelog_file(name, file), token)
    tags = git_history.tag_dates(path)
    found = []
    for (branch, file), (commit, content) in sorted(files.items()):
        text = changelogs.decode(content)
        if changelogs.is_gnu_changelog(text):
            continue
        found.extend(changelogs.occurrences_in_file(name, file, branch, branch == default_branch, commit, text, tags))
    return found


def collect(repositories, cache_dir=git_history.CACHE_DIR, token=None, update=True, workers=8, log=print):
    """All occurrences in the repositories; a failing repository stops the collection."""
    def one(repository):
        name, default_branch = repository
        found = repository_occurrences(name, default_branch, cache_dir, token, update)
        log(f'{name}: {len(found)} occurrences')
        return found

    occurrences = []
    with ThreadPoolExecutor(workers) as pool:
        for found in pool.map(one, repositories):
            occurrences.extend(found)
    return occurrences


def name_mapper(contributors_dir=paths.CONTRIBUTORS_DIR):
    """The NameMapper from the registers and the logins with code work."""
    logins = set()
    for path in sorted(contributors_dir.glob('*-plone-contributors.csv')):
        logins.update(pd.read_csv(path, usecols=['username'])['username'].dropna().astype(str))
    return changelogs.NameMapper(load_registry(), sorted(logins), load_bot_accounts())


def count(entries, mapper):
    """{year: {person: {'entries', 'repositories', 'names', 'layers'}}} and the coverage per year.

    Every person an entry names gets full credit. Unmatched names count under
    their most frequent spelling, ignoring case.
    """
    credits = [(entry, changelogs.credited(entry, mapper)) for entry in entries if entry.year]
    spellings = defaultdict(Counter)
    for _, people in credits:
        for person, name, layer in people:
            if layer == changelogs.UNMATCHED:
                spellings[person.casefold()][person] += 1
    spelling = {key: min(found.items(), key=lambda item: (-item[1], item[0]))[0] for key, found in spellings.items()}

    per_year = defaultdict(lambda: defaultdict(lambda: {'entries': 0, 'repositories': set(), 'names': set(),
                                                        'layers': set()}))
    coverage = defaultdict(Counter)
    for entry, people in credits:
        year = entry.year
        coverage[year]['entries'] += 1
        coverage[year]['named'] += bool(entry.names) and (entry.variant not in changelogs.WEAK_VARIANTS or bool(people))
        coverage[year]['mapped'] += any(layer != changelogs.UNMATCHED for _, _, layer in people)
        for person, name, layer in people:
            if layer == changelogs.UNMATCHED:
                person = spelling[person.casefold()]
            stats = per_year[year][person]
            stats['entries'] += 1
            stats['repositories'].add(entry.repository)
            stats['names'].add(name)
            stats['layers'].add(layer)
    return per_year, coverage


def year_table(people):
    rows = [{
        'username': mask_text(person),
        'changelog_entries': stats['entries'],
        'repositories_count': len(stats['repositories']),
        'repositories': ', '.join(sorted(stats['repositories'])),
        'changelog_names': mask_text(';'.join(sorted(stats['names'], key=lambda name: (name.casefold(), name)))),
        'matched_by': ';'.join(sorted(stats['layers'])),
    } for person, stats in people.items()]
    return by_count(pd.DataFrame(rows, columns=COLUMNS), 'changelog_entries', 'username')


def unmatched_names(per_year, years):
    """{name: entries} of the names that the registers do not map, over the years."""
    found = Counter()
    for year in years:
        for person, stats in per_year.get(str(year), {}).items():
            if changelogs.UNMATCHED in stats['layers']:
                found[person] += stats['entries']
    return found


def coverage_lines(coverage, years):
    """The share of entries per year that name someone, and that name someone the registers map."""
    lines = ['year  entries  named  mapped']
    for year in years:
        found = coverage.get(str(year), Counter())
        total = found['entries']
        share = (lambda n: f'{n / total:6.0%}') if total else (lambda n: '     -')
        lines.append(f"{year}  {total:7}  {share(found['named'])}  {share(found['mapped'])}")
    return lines


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Collect the changelog entries per person and year from all repositories of the plone '
                    'organisation (#71). Uses GITHUB_TOKEN from the environment or .env, if set.')
    parser.add_argument('--from-year', type=int, default=FIRST_YEAR,
                        help=f'First year to write (default: {FIRST_YEAR})')
    parser.add_argument('--to-year', type=int, default=last_completed_year(),
                        help='Last year to write (default: the last completed year)')
    parser.add_argument('--workers', type=int, default=8, help='Repositories processed in parallel (default: 8)')
    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.from_year > args.to_year:
        print('Error: --from-year must not be after --to-year')
        return 1
    years = range(args.from_year, args.to_year + 1)
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')
    session = requests.Session()
    if token:
        session.headers['Authorization'] = f'token {token}'
    try:
        excluded = load_excluded_repositories()
        repositories = [repo for repo in organisation_repositories(session) if repo[0] not in excluded]
        print(f'{len(repositories)} repositories, {len(excluded)} excluded')
        mapper = name_mapper()
        occurrences = collect(repositories, token=token, workers=args.workers)
    except (KeyboardInterrupt, GitHubAPIError, git_history.GitError, requests.exceptions.RequestException) as error:
        # Never write incomplete data
        print(f'\nCollection stopped ({type(error).__name__}: {error}). No data file was written.')
        return 1

    entries = changelogs.deduplicate(occurrences)
    per_year, coverage = count(entries, mapper)
    paths.CHANGELOGS_DIR.mkdir(parents=True, exist_ok=True)
    for year in years:
        year_table(per_year.get(str(year), {})).to_csv(paths.changelog_entries_file(year), index=False)
    print(f'\n{len(occurrences)} occurrences, {len(entries)} entries after deduplication, '
          f'{sum(1 for e in entries if e.year)} with a release date')
    print('\n'.join(coverage_lines(coverage, years)))
    unmatched = unmatched_names(per_year, years)
    print(f'\n{len(unmatched)} names without a mapping, the most frequent:')
    for name, entries_count in unmatched.most_common(20):
        print(f'  {name}: {entries_count}')
    print(f'\nWrote {paths.changelog_entries_file(years[0])} to {paths.changelog_entries_file(years[-1])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
