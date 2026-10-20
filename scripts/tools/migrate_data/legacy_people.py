"""The old person index of the migration (#139); it serves the migration only.

One identity per person across code work (GitHub logins) and community work (mostly names).

A person is keyed by GitHub login (lower case, as logins are case-insensitive)
where the committed data resolves one, else by
their normalised name ("name:jane doe"). Names that stay unmatched can count a
person twice (#117).
"""

import csv
import re
import unicodedata
from collections import defaultdict

from scripts.tools.migrate_data.legacy_mappings import COMMIT_AUTHORS, FULLNAMES

# A link to a GitHub profile, not to a repository or commit below it
PROFILE_LINK = re.compile(r'https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?=$|[\s;,)])')


def normalise(name):
    """Lower case, without accents and extra whitespace, to compare names."""
    decomposed = unicodedata.normalize('NFKD', name)
    plain = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return ' '.join(plain.lower().split())


def is_group(name, organisations, row_organisations=()):
    """True for entries in person columns that are not one person.

    Groups are several entries, teams, organisations, and entries that name one of
    the row's organisations, such as "Mathematics Institute at UNAM"; a person
    with their organisation in parentheses, such as "Alex (Juizi)", is a person.
    """
    name = name.strip()
    if ';' in name or name.lower().endswith(' team') or name in organisations:
        return True
    for organisation in row_organisations:
        if name.casefold() == organisation.casefold():
            return True
        word = re.escape(organisation)
        if re.search(rf'(?<!\w){word}(?!\w)', name, re.I) and not re.search(rf'\({word}\)', name, re.I):
            return True
    return False


class PersonIndex:
    """Finds the key of a person: their GitHub login if known, else their normalised name."""

    def __init__(self, logins_by_name, organisations=frozenset()):
        self.logins_by_name = logins_by_name
        self.organisations = organisations

    def key(self, name='', handle='', row_organisations=()):
        if handle.strip():
            return handle.strip().casefold()
        if not name.strip() or is_group(name, self.organisations, row_organisations):
            return None
        normalised = normalise(name)
        return self.logins_by_name.get(normalised, f'name:{normalised}')


def _logins_from_records(records):
    for record in records:
        if not record.person.strip():
            continue
        if record.handle.strip():
            yield record.person, record.handle.strip().casefold()
            continue
        if getattr(record, 'shared', False):
            # A profile link in a row with several people may belong to any of them
            continue
        links = PROFILE_LINK.findall(record.source or '')
        if len({link.casefold() for link in links}) == 1:
            yield record.person, links[0].casefold()


def build_person_index(records, commit_authors_path=COMMIT_AUTHORS, fullnames_path=FULLNAMES,
                       organisations=frozenset()):
    """A PersonIndex from the names and logins the committed data links.

    `records` are community records with `person`, `handle` and `source`. A name
    that would map to two different logins maps to none.
    """
    candidates = defaultdict(set)
    for name, login in _logins_from_records(records):
        candidates[normalise(name)].add(login)
    with open(commit_authors_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['name'].strip() and row['github_username'].strip():
                candidates[normalise(row['name'])].add(row['github_username'].strip().casefold())
    with open(fullnames_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            candidates[normalise(row['fullname'])].add(row['github username'].strip().casefold())
    logins = {name: next(iter(found)) for name, found in candidates.items() if len(found) == 1}
    return PersonIndex(logins, organisations)
