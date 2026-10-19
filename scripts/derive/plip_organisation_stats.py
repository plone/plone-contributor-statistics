#!/usr/bin/env python3
"""PLIPs per organisation, mapped by the year of each PLIP (#95).

Reads plone-plips-detailed.csv and writes plone-plip-organisations.csv.
A closed PLIP counts for the organisation of its author in the year it was
closed, an open PLIP for the organisation in the year it was created, with the
affiliations of the registers.
"""

import argparse
import csv
from collections import defaultdict

from scripts.lib import paths
from scripts.lib.model import load_registry

PLIPS_FILE = paths.PLIPS_DETAILED
OUTPUT_FILE = paths.PLIP_ORGANISATIONS
COLUMNS = ['organisation', 'total_plips', 'open_plips', 'closed_plips', 'contributors_count', 'contributors',
           'repositories_count', 'repositories', 'first_plip', 'last_plip']


def read_plips(path=PLIPS_FILE):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def plip_year(plip):
    """The year that decides the organisation: closed, or created for open PLIPs."""
    date = plip['closed_at'] if plip['state'] == 'closed' and plip['closed_at'] else plip['created_at']
    return int(date[:4])


def organisation_lookup(*_legacy_paths, registry=None):
    """Return a function (login, year) -> organisation, reading the registers once.

    The positional arguments are the mapping files the callers passed before the registers; they are ignored.
    """
    registry = registry or load_registry()

    def organisation(login, year):
        return registry.organisation_for_username(login, year)

    return organisation


def plips_by_organisation(plips, organisation, years=None, closed_only=False):
    """Group PLIPs by organisation; `years` limits them to those years, `closed_only` to closed PLIPs."""
    groups = defaultdict(list)
    for plip in plips:
        if closed_only and plip['state'] != 'closed':
            continue
        year = plip_year(plip)
        if years is not None and year not in years:
            continue
        groups[organisation(plip['author'], year)].append(plip)
    return dict(groups)


def summary_rows(groups):
    rows = []
    for name, plips in groups.items():
        authors = sorted({p['author'] for p in plips}, key=str.lower)
        repositories = sorted({p['repository'] for p in plips})
        created = sorted(p['created_at'] for p in plips)
        rows.append({
            'organisation': name,
            'total_plips': len(plips),
            'open_plips': sum(p['state'] == 'open' for p in plips),
            'closed_plips': sum(p['state'] == 'closed' for p in plips),
            'contributors_count': len(authors),
            'contributors': ', '.join(authors),
            'repositories_count': len(repositories),
            'repositories': ', '.join(repositories),
            'first_plip': created[0],
            'last_plip': created[-1],
        })
    return sorted(rows, key=lambda r: (-r['total_plips'], r['organisation'].lower()))


def write_summary(rows, path=OUTPUT_FILE):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = summary_rows(plips_by_organisation(read_plips(), organisation_lookup()))
    write_summary(rows)
    print(f'Wrote {OUTPUT_FILE} ({len(rows)} organisations)')


if __name__ == '__main__':
    # No options; --help says what the script does
    argparse.ArgumentParser(description=__doc__.strip().splitlines()[0]).parse_args()
    main()
