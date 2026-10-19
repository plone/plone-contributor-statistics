#!/usr/bin/env python3
"""Explain which row of affiliations.csv gives the organisation of a person in a year."""

import argparse
import sys

from scripts.lib.model import UNMAPPED, load_registry


def explain(registry, person_id, year):
    """The organisation of the person in the year and the row that says so, or Unmapped."""
    if person_id not in registry.people:
        raise ValueError(f'Unknown person: {person_id}')
    # Rows are in file order and the header is line 1
    for line, affiliation in enumerate(registry.affiliations, start=2):
        if affiliation.person == person_id and affiliation.covers(year):
            end = affiliation.to_year if affiliation.to_year is not None else 'present'
            return (f'{registry.organisation_name(affiliation.organisation)} '
                    f'(affiliations.csv line {line}: {affiliation.from_year}–{end}, {affiliation.source})')
    return f'{UNMAPPED} (no row covers {year})'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('person', metavar='PERSON', help='the id of the person, such as jane-doe')
    parser.add_argument('year', metavar='YEAR', type=int)
    args = parser.parse_args(argv)
    try:
        print(explain(load_registry(), args.person, args.year))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    sys.exit(main())
