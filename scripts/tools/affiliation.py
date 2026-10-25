#!/usr/bin/env python3
"""Show the organisation a person counts for in each year, and the affiliations with the sources they cite.

The organisation of a year is computed by the attribution rules (docs/explanation/attribution.md) from every
affiliation of the person, not by one row, and each year names the rule that gave it, such as `bridged`; the
citations below it are the evidence those rules weigh.
"""

import argparse
import sys
from datetime import date

from scripts.lib.model import UNMAPPED, load_registry


def person_id(registry, person):
    """The id of the person given by id, by a GitHub login (also a further account) or as `person:<id>`."""
    if person in registry.people:
        return person
    found = registry.person_for_username(person)
    if found is None:
        raise ValueError(f'Unknown person: {person}')
    return found.id


def years_of(registry, person, until=None):
    """The years from the first year of the person's affiliations up to the last one, open ones up to `until`
    (the current year by default)."""
    rows = [a for a in registry.affiliations if a.person == person]
    if not rows:
        return []
    until = until or date.today().year
    return list(range(min(a.from_year for a in rows), max(a.to_year or until for a in rows) + 1))


def organisations(registry, person, years):
    """`YEAR: organisation (rule)` for each year, with the rule that gave it, such as `2018: Zest Software
    (bridged)`; an undecided year names the organisations in conflict."""
    lines = []
    for year in years:
        org_id, rule = registry.attribution.explain(person, year)
        if org_id is not None:
            lines.append(f'{year}: {registry.organisation_name(org_id)} ({rule})')
            continue
        conflict = registry.attribution.conflict(person, year)
        if conflict:
            names = ', '.join(sorted(registry.organisation_name(org) for org in conflict))
            lines.append(f'{year}: {UNMAPPED} (no rule decides between {names})')
        else:
            lines.append(f'{year}: {UNMAPPED}')
    return lines


def _source_line(registry, source_id):
    source = registry.sources.get(source_id)
    if source is None:
        return f'  {source_id} (not in the source register)'
    return f'  {source_id} {source.title}, {source.date}, {source.archive_url or source.url}'


def citations(registry, person):
    """For each affiliation of the person: its id, organisation, years and status, then each citation with its
    source, snippet, `supersedes` and notes."""
    by_affiliation = {}
    for citation in registry.citations:
        by_affiliation.setdefault(citation.affiliation, []).append(citation)
    lines = []
    for affiliation in registry.affiliations:
        if affiliation.person != person:
            continue
        end = affiliation.to_year if affiliation.to_year is not None else 'present'
        lines.append(f'{affiliation.id}: {registry.organisation_name(affiliation.organisation)}, '
                     f'{affiliation.from_year}–{end}, {affiliation.status}')
        if affiliation.notes:
            lines.append(f'  notes: {affiliation.notes}')
        cited = by_affiliation.get(affiliation.id, [])
        if not cited:
            lines.append('  no citation')
        for citation in cited:
            lines.append(_source_line(registry, citation.source))
            lines.append(f'    "{citation.snippet}"' if citation.snippet else '    no snippet')
            if citation.supersedes:
                lines.append(f'    supersedes: {citation.supersedes}')
            if citation.notes:
                lines.append(f'    notes: {citation.notes}')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('person', metavar='PERSON',
                        help='the id of the person, such as jane-doe, a GitHub login, or person:<id>')
    parser.add_argument('years', metavar='YEAR', type=int, nargs='*',
                        help='the years to show; default: the years of the affiliations of the person')
    args = parser.parse_args(argv)
    registry = load_registry()
    try:
        person = person_id(registry, args.person)
    except ValueError as error:
        parser.error(str(error))
    print(f'{registry.people[person].name} ({person})')
    years = args.years or years_of(registry, person)
    if years:
        print()
        print('\n'.join(organisations(registry, person, years)))
    print()
    print('\n'.join(citations(registry, person)) or 'No affiliations.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
