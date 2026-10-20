#!/usr/bin/env python3
"""Find a person in the register, or add one (see docs/how-to/add-a-person.md)."""

import argparse
import csv
import re
import sys

from scripts.lib.model import MAPPINGS_DIR, Person, append_person, load_registry
from scripts.lib.model.names import fold, unique_slug

LINK = re.compile(r'https?://\S+')


def find(registry, query):
    """The people matching the query by id, name, GitHub login or email, in id order."""
    query = query.strip()
    found = set()
    if query in registry.people:
        found.add(query)
    folded, login, email = fold(query), query.casefold(), query.lower()
    if folded:
        found |= {p.id for p in registry.people.values() if fold(p.name) == folded}
    found |= {p.id for p in registry.people.values() if p.github and p.github.casefold() == login}
    for identity in registry.identities:
        if identity.kind == 'name' and folded and fold(identity.value) == folded:
            found.add(identity.person)
        elif identity.kind == 'login' and identity.value.casefold() == login:
            found.add(identity.person)
        elif identity.kind == 'email' and identity.value.lower() == email:
            found.add(identity.person)
    return [registry.people[person_id] for person_id in sorted(found) if person_id in registry.people]


def add(mappings_dir, name, github, source):
    """Add a person to people.csv with a generated id and return them.

    A link anywhere in the source is enough (the record convention of the repository).
    """
    name = ' '.join(name.split())
    github = (github or '').strip()
    source = (source or '').strip()
    if not name:
        raise ValueError('The name is empty')
    if not LINK.search(source):
        raise ValueError('The source needs a link to a public record (https://...)')
    registry = load_registry(mappings_dir)
    if github:
        login = github.casefold()
        owners = {p.id for p in registry.people.values() if p.github and p.github.casefold() == login}
        owners |= {i.person for i in registry.identities if i.kind == 'login' and i.value.casefold() == login}
        if owners:
            raise ValueError(f'The login {github} belongs to {", ".join(sorted(owners))} already')
    person = Person(unique_slug(name, set(registry.people)), name, github or None, source)
    append_person(mappings_dir, person)
    return person


def _cells(*values):
    return ['' if value is None else str(value) for value in values]


def _row(person):
    return _cells(person.id, person.name, person.github, person.source)


def _print_group(writer, filename, header, rows):
    print(f'# curated/mappings/{filename}')
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)


def _print_person(writer, registry, person):
    """The rows of the person in the three registers, each group under the name of its file."""
    _print_group(writer, 'people.csv', ['id', 'name', 'github', 'source'], [_row(person)])
    identities = [_cells(i.person, i.kind, i.value, i.source) for i in registry.identities if i.person == person.id]
    if identities:
        _print_group(writer, 'identities.csv', ['person', 'kind', 'value', 'source'], identities)
    affiliations = [_cells(a.person, a.organisation, a.from_year, a.to_year, a.source, a.checked, a.notes)
                    for a in registry.affiliations if a.person == person.id]
    if affiliations:
        _print_group(writer, 'affiliations.csv',
                     ['person', 'organisation', 'from', 'to', 'source', 'checked', 'notes'], affiliations)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', nargs='?', metavar='QUERY', help='id, name, GitHub login or email to look for')
    parser.add_argument('--add', metavar='NAME', help='add a person with this name')
    parser.add_argument('--github', help='the GitHub login of the new person')
    parser.add_argument('--source', help='link to the public record for the new person')
    args = parser.parse_args(argv)
    writer = csv.writer(sys.stdout, lineterminator='\n')
    if args.add:
        if not args.source:
            parser.error('--add needs --source')
        try:
            person = add(MAPPINGS_DIR, args.add, args.github, args.source)
        except ValueError as error:
            parser.error(str(error))
        writer.writerow(_row(person))
        return 0
    if not args.query:
        parser.error('give a QUERY or use --add')
    registry = load_registry(MAPPINGS_DIR)
    people = find(registry, args.query)
    for number, person in enumerate(people):
        if number:
            print()
        _print_person(writer, registry, person)
    return 0 if people else 1


if __name__ == '__main__':
    sys.exit(main())
