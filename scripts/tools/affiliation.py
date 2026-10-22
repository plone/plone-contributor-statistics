#!/usr/bin/env python3
"""Explain which row of affiliations.csv gives the organisation a person counts for in a year."""

import argparse
import sys

from scripts.lib.model import UNMAPPED, load_registry
from scripts.lib.model.attribution import COUNTING


def explain(registry, person, year):
    """The organisation of the person in the year and the row that says so, or Unmapped.

    The person is given by id, by a GitHub login (also a second account) or as `person:<id>`.
    """
    if person in registry.people:
        person_id = person
    else:
        found = registry.person_for_username(person)
        if found is None:
            raise ValueError(f'Unknown person: {person}')
        person_id = found.id
    organisation = registry.organisation_of(person_id, year)
    # Rows are in file order and the header is line 1
    rows = [(line, a) for line, a in enumerate(registry.affiliations, start=2)
            if a.person == person_id and a.covers(year) and a.status in COUNTING]
    for line, affiliation in rows:
        if registry.organisation_name(affiliation.organisation) == organisation:
            end = affiliation.to_year if affiliation.to_year is not None else 'present'
            return (f'{organisation} (affiliations.csv line {line}: {affiliation.from_year}–{end}, '
                    f'{affiliation.status}, {affiliation.id})')
    if rows:
        return f'{UNMAPPED} (no attribution rule decides {year})'
    return f'{UNMAPPED} (no row covers {year})'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('person', metavar='PERSON',
                        help='the id of the person, such as jane-doe, a GitHub login, or person:<id>')
    parser.add_argument('year', metavar='YEAR', type=int)
    args = parser.parse_args(argv)
    try:
        print(explain(load_registry(), args.person, args.year))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    sys.exit(main())
