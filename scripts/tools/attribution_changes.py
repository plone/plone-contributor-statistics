#!/usr/bin/env python3
"""List every person and year whose organisation differs between a base commit and the working tree.

The counting before is that of the engine and the data at the base: the files the attribution needs (`scripts/`,
`curated/`, `collected/commit-domains/`) are taken from the base with `git archive` into a temporary folder, and
the model of the base runs there in a subprocess, so the old rules run on the old data. The counting after is
that of the working tree. Compared are the years of every person's affiliations, at the base and now, from the
first year to the last, open ones up to the current year, including the years between the rows.

A year is active when the collected and curated data of the working tree credit the person with something in it:
commits or pull requests (collected/contributors/), changelog entries (collected/changelogs/, names that no
identity maps left out), PLIPs (collected/plips/, in the year that counts for the PLIP's organisation: closed, or
created for an open one), or community roles (curated/community/: board, team lead, release manager, trainer,
speaker, sprint or conference organiser, podcast host). Only active years change a statistic; the others are
listed with --all-years.

The base defaults to the commit where the branch left origin/main (`git merge-base HEAD origin/main`).
"""

import argparse
import csv
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from scripts.derive.plip_organisation_stats import plip_year
from scripts.lib import paths
from scripts.lib.model import UNMAPPED, community_years, load_registry, roles
from scripts.lib.model.attribution import COUNTING
from scripts.tools.github_evidence import CONTRIBUTORS_FILE

# What the attribution of the base reads: the code, the registers and sources, the commit domains (rule 6b)
BASE_PATHS = ('scripts', 'curated', str(paths.COMMIT_DOMAINS_DIR))

# Runs in the tree of the base, with its model: reads {'until', 'pairs'} from stdin, writes [[person, year,
# organisation name or null]] of the pairs and of the years of the person's rows at the base
BEFORE = '''
import json, sys
from scripts.lib.model import load_registry
wanted = json.load(sys.stdin)
until = wanted['until']
registry = load_registry()
pairs = {(person, year) for person, year in wanted['pairs']}
rows = {}
for row in registry.affiliations:
    if row.status in ('stated', 'assumed'):
        rows.setdefault(row.person, []).append(row)
for person, own in rows.items():
    last = max([until] + [row.to_year for row in own if row.to_year is not None])
    pairs.update((person, year) for year in range(min(row.from_year for row in own), last + 1))
found = []
for person, year in sorted(pairs):
    org = registry.attribution.organisation(person, year)
    found.append([person, year, registry.organisation_name(org) if org is not None else None])
json.dump(found, sys.stdout)
'''


def default_base():
    """The commit where the branch left origin/main."""
    return subprocess.run(['git', 'merge-base', 'HEAD', 'origin/main'], capture_output=True, text=True,
                          check=True).stdout.strip()


def person_years(registry, until):
    """{(person id, year)} from the first year of each person's stated and assumed rows to the last one, open
    ones up to `until`."""
    rows = defaultdict(list)
    for row in registry.affiliations:
        if row.status in COUNTING:
            rows[row.person].append(row)
    found = set()
    for person, own in rows.items():
        last = max([until] + [row.to_year for row in own if row.to_year is not None])
        found.update((person, year) for year in range(min(row.from_year for row in own), last + 1))
    return found


def before_counting(base, pairs, until):
    """{(person id, year): organisation name or None} of the engine and data at the base commit, for the pairs
    and the years of the rows at the base."""
    present = subprocess.run(['git', 'ls-tree', '-d', '--name-only', base, *BASE_PATHS], capture_output=True,
                             text=True, check=True).stdout.split()
    archive = subprocess.run(['git', 'archive', '--format=tar', base, *present], capture_output=True,
                             check=True).stdout
    with tempfile.TemporaryDirectory() as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(folder, filter='data')
        result = subprocess.run([sys.executable, '-c', BEFORE], cwd=folder, capture_output=True, text=True,
                                input=json.dumps({'until': until, 'pairs': sorted(pairs)}))
    if result.returncode:
        raise SystemExit(f'The counting at {base} failed:\n{result.stderr[-2000:]}')
    return {(person, year): org for person, year, org in json.loads(result.stdout)}


def _person_of(registry, username):
    person = registry.person_for_username(username)
    return person.id if person else None


def _rows(path):
    if not Path(path).exists():
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def activity(registry):
    """{(person id, year): {what: count}} of what the collected and curated data credit each person with.

    `what` is commits, pull requests, changelog entries, PLIPs, or the label of a community role.
    """
    found = defaultdict(lambda: defaultdict(int))
    for path in sorted(paths.CONTRIBUTORS_DIR.glob('*-plone-contributors.csv')):
        if not CONTRIBUTORS_FILE.match(path.name):
            continue  # a file of several years
        year = int(path.name[:4])
        for row in _rows(path):
            person = _person_of(registry, row['username'])
            if person:
                found[(person, year)]['commits'] += int(row['total_commits'] or 0)
                found[(person, year)]['pull requests'] += int(row['total_pull_requests'] or 0)
    for path in sorted(paths.CHANGELOGS_DIR.glob('*-plone-changelog-entries.csv')):
        year = int(path.name[:4])
        for row in _rows(path):
            if 'unmatched' in row['matched_by'].split(';'):
                continue  # a name, no login
            person = _person_of(registry, row['username'])
            if person and int(row['changelog_entries'] or 0):
                found[(person, year)]['changelog entries'] += int(row['changelog_entries'])
    for plip in _rows(paths.PLIPS_DETAILED):
        person = _person_of(registry, plip['author'])
        if person:
            found[(person, plip_year(plip))]['PLIPs'] += 1
    for year in community_years():
        for role in roles(year):
            found[(role.person, year)][role.label] += 1
    return {key: {what: count for what, count in value.items() if count} for key, value in found.items()
            if any(value.values())}


def describe(credited):
    """`3 commits, 1 pull request, Speaker` of what a person is credited with in a year."""
    singular = {'commits': 'commit', 'pull requests': 'pull request', 'changelog entries': 'changelog entry',
                'PLIPs': 'PLIP'}
    parts = []
    for what in ('commits', 'pull requests', 'changelog entries', 'PLIPs'):
        if credited.get(what):
            count = credited[what]
            parts.append(f'{count} {singular[what] if count == 1 else what}')
    parts += sorted(what for what in credited if what not in singular)
    return ', '.join(parts)


def changes(registry, before, credited):
    """[{person, year, before, after, rule, activity}] of the person-years whose organisation differs, sorted by
    person and year; the activity is empty for an inactive year."""
    found = []
    for person, year in sorted(before):
        old = before[(person, year)] or UNMAPPED
        org, rule = registry.attribution.explain(person, year)
        new = registry.organisation_name(org) if org is not None else UNMAPPED
        what = describe(credited.get((person, year), {}))
        if old != new:
            found.append({'person': person, 'year': year, 'before': old, 'after': new, 'rule': rule,
                          'activity': what})
    return found


def compute(base, until, all_years=False):
    """(the changes listed, the number of active and of inactive changes)."""
    registry = load_registry()
    credited = activity(registry)
    pairs = person_years(registry, until) | {pair for pair in credited if pair[1] <= until}
    before = before_counting(base, pairs, until)
    every = changes(registry, before, credited)
    active = sum(1 for change in every if change['activity'])
    listed = every if all_years else [change for change in every if change['activity']]
    return listed, active, len(every) - active


COLUMNS = ('person', 'year', 'before', 'after', 'rule now', 'activity')


def _cells(change):
    return [change['person'], str(change['year']), change['before'], change['after'], change['rule'],
            change['activity'] or 'inactive']


def text_table(rows):
    """The changes as a text table, columns aligned."""
    cells = [list(COLUMNS)] + [_cells(row) for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(COLUMNS))]
    return '\n'.join('  '.join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in cells)


def markdown_table(rows):
    """The changes as a Markdown table."""
    lines = ['| ' + ' | '.join(COLUMNS) + ' |', '|' + '---|' * len(COLUMNS)]
    lines += ['| ' + ' | '.join(cell.replace('|', '\\|') for cell in _cells(row)) + ' |' for row in rows]
    return '\n'.join(lines)


def summary(base, active, inactive, all_years):
    hidden = '' if all_years or not inactive else ' (listed with --all-years)'
    return (f'Compared with {base}: {active} active person-years count for another organisation, '
            f'{inactive} inactive ones{hidden}.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', help='the commit to compare with; default: git merge-base HEAD origin/main')
    parser.add_argument('--all-years', action='store_true', help='list the inactive person-years too')
    parser.add_argument('--markdown', action='store_true', help='print a Markdown table')
    args = parser.parse_args(argv)
    try:
        base = args.base or default_base()
        rows, active, inactive = compute(base, date.today().year, args.all_years)
    except subprocess.CalledProcessError as error:  # no such commit, or no origin/main to find the base
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr or ''
        raise SystemExit(f'{" ".join(error.cmd[:2])} failed: {stderr.strip()}') from None
    if rows:
        print(markdown_table(rows) if args.markdown else text_table(rows))
        print()
    print(summary(base, active, inactive, args.all_years))
    return 0


if __name__ == '__main__':
    sys.exit(main())
