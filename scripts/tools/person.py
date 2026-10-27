#!/usr/bin/env python3
"""Find a person in the register, or add one (see docs/how-to/add-a-person.md)."""

import argparse
import csv
import re
import sys

from scripts.lib import addresses
from scripts.lib.model import (LOGIN_KINDS, MAPPINGS_DIR, Identity, Person, append_person, load_registry, source_id,
                               split_archive_url)
from scripts.lib.model.names import fold, unique_slug

SOURCE_ID = re.compile(r'^[0-9a-f]{12}$')


def find(registry, query):
    """The people matching the query by id, name, GitHub login or email, in id order."""
    query = query.strip()
    found = set()
    if query in registry.people:
        found.add(query)
    folded, login = fold(query), query.casefold()
    email = addresses.mask_address(query).lower() if '@' in query or addresses.is_masked(query) else None
    if folded:
        found |= {p.id for p in registry.people.values() if fold(p.name) == folded}
    for identity in registry.identities:
        if identity.kind == 'name' and folded and fold(identity.value) == folded:
            found.add(identity.person)
        elif identity.kind in LOGIN_KINDS and identity.value.casefold() == login:
            found.add(identity.person)
        elif identity.kind == 'email' and email and addresses.mask_address(identity.value).lower() == email:
            found.add(identity.person)
    return [registry.people[person_id] for person_id in sorted(found) if person_id in registry.people]


CAPTURE_FIRST = 'capture it first with python -m scripts.tools.capture'


def _source_of(registry, source):
    """The id of the source in the register: given as its id, its address or its archived copy's address."""
    if SOURCE_ID.match(source):
        sid = source
    else:
        archived = split_archive_url(source)
        sid = source_id(*archived) if archived else source_id(source)
    if sid not in registry.sources:
        raise ValueError(f'The source {source} is not in the source register: {CAPTURE_FIRST}')
    return sid


def add(mappings_dir, name, github, source):
    """Add a person to people.csv with a generated id, and the `github` identity, or the `name` identity without
    a login, citing the source; return the person and the identity.

    The source is a source id, or the address of a source in the register.
    """
    name = ' '.join(name.split())
    github = (github or '').strip()
    source = (source or '').strip()
    if not name:
        raise ValueError('The name is empty')
    if not source:
        raise ValueError('The source of the public record is empty: give the id or the address of a source in the '
                         f'source register; if the record is not in the register yet, {CAPTURE_FIRST}')
    registry = load_registry(mappings_dir)
    if github:
        login = github.casefold()
        owners = {i.person for i in registry.identities if i.kind in LOGIN_KINDS and i.value.casefold() == login}
        if owners:
            raise ValueError(f'The login {github} belongs to {", ".join(sorted(owners))} already')
    sid = _source_of(registry, source)
    person = Person(unique_slug(name, set(registry.people)), name)
    identity = Identity(person.id, 'github', github, sid) if github else Identity(person.id, 'name', name, sid)
    append_person(mappings_dir, person, identity)
    return person, identity


def _cells(*values):
    return ['' if value is None else str(value) for value in values]


IDENTITY_HEADER = ['person', 'kind', 'value', 'source', 'snippet', 'notes']


def _identity_row(identity):
    return _cells(identity.person, identity.kind, identity.value, identity.source, identity.snippet, identity.notes)


def _print_group(writer, filename, header, rows):
    print(f'# curated/mappings/{filename}')
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)


def _print_person(writer, registry, person):
    """The rows of the person in the three registers, each group under the name of its file."""
    _print_group(writer, 'people.csv', ['id', 'name'], [_cells(person.id, person.name)])
    identities = [_identity_row(i) for i in registry.identities if i.person == person.id]
    if identities:
        _print_group(writer, 'identities.csv', IDENTITY_HEADER, identities)
    affiliations = [_cells(a.id, a.person, a.organisation, a.from_year, a.to_year, a.status, a.checked, a.notes)
                    for a in registry.affiliations if a.person == person.id]
    if affiliations:
        _print_group(writer, 'affiliations.csv',
                     ['id', 'person', 'organisation', 'from', 'to', 'status', 'checked', 'notes'], affiliations)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', nargs='?', metavar='QUERY', help='id, name, GitHub login or email to look for')
    parser.add_argument('--add', metavar='NAME', help='add a person with this name')
    parser.add_argument('--github', help='the GitHub login of the new person')
    parser.add_argument('--source', help='the public record for the new person: the id or the address of a '
                                         'source in the source register')
    args = parser.parse_args(argv)
    writer = csv.writer(sys.stdout, lineterminator='\n')
    if args.add:
        try:
            person, identity = add(MAPPINGS_DIR, args.add, args.github, args.source)
        except ValueError as error:
            parser.error(str(error))
        writer.writerow(_cells(person.id, person.name))
        writer.writerow(_identity_row(identity))
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
