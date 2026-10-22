"""The registers of people, identities, affiliations and organisations, and the lookups on them."""

import csv
from dataclasses import dataclass

from scripts.lib import paths
from scripts.lib.model.names import fold
from scripts.lib.model.schema import read_rows, split_set

UNMAPPED = 'Unmapped'
PERSON_PREFIX = 'person:'
MIN_DOMAIN_KEY = 3  # the first word of an organisation name is a key for domains only from this length on


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    github: str | None
    source: str


@dataclass(frozen=True)
class Identity:
    person: str
    kind: str
    value: str
    source: str


@dataclass(frozen=True)
class Affiliation:
    person: str
    organisation: str
    from_year: int
    to_year: int | None
    source: str
    checked: object
    notes: str | None

    def covers(self, year):
        """Whether the affiliation holds in the year."""
        return self.from_year <= year and (self.to_year is None or year <= self.to_year)


@dataclass(frozen=True)
class Organisation:
    id: str
    name: str
    kind: str
    github: str | None
    aliases: tuple
    notes: str | None


class Registry:
    """The four registers, indexed for the lookups the pipeline needs.

    A name finds a person through a `name` identity of any length, or through the display name in people.csv
    when that has more than one word: a one-word display name, such as a login used as the name, is not
    evidence that the person wrote a changelog entry signed with that word.
    """

    def __init__(self, people, identities, affiliations, organisations):
        self.people = {person.id: person for person in people}
        self.identities = list(identities)
        self.affiliations = list(affiliations)
        self.organisations = {organisation.id: organisation for organisation in organisations}
        self._by_login = {}
        self._by_email = {}
        self._by_name = {}
        for person in self.people.values():
            if person.github:
                self._by_login.setdefault(person.github.casefold(), set()).add(person.id)
            if len(fold(person.name).split()) > 1:
                self._by_name.setdefault(fold(person.name), set()).add(person.id)
        for identity in self.identities:
            if identity.kind == 'login':
                self._by_login.setdefault(identity.value.casefold(), set()).add(identity.person)
            elif identity.kind == 'email':
                self._by_email.setdefault(identity.value.lower(), set()).add(identity.person)
            elif identity.kind == 'name':
                self._by_name.setdefault(fold(identity.value), set()).add(identity.person)
        self._organisation_ids = {}
        self._name_keys = {}  # folded name or alias without spaces -> {organisation id: 'name' or 'alias'}
        self._first_words = {}  # first word of a name or alias -> {organisation id}
        self._domain_aliases = {}
        for organisation in self.organisations.values():
            for number, name in enumerate((organisation.name, *organisation.aliases)):
                self._organisation_ids.setdefault(fold(name), organisation.id)
                if organisation.kind == 'organisation':
                    if '.' in name:  # an alias written as a domain
                        self._domain_aliases.setdefault(name.strip().lower(), set()).add(organisation.id)
                    words = fold(name).split()
                    if words:
                        kinds = self._name_keys.setdefault(''.join(words), {})
                        kinds.setdefault(organisation.id, 'name' if number == 0 else 'alias')
                        if len(words[0]) >= MIN_DOMAIN_KEY:
                            self._first_words.setdefault(words[0], set()).add(organisation.id)

    def _single(self, index, key):
        """The person of a key, or None when the key is unknown or belongs to several people."""
        ids = index.get(key, set())
        return self.people.get(next(iter(ids))) if len(ids) == 1 else None

    def person_for(self, *, login=None, email=None, name=None):
        """The person behind a login, an email address or a name; None when unknown or ambiguous."""
        if login is not None:
            return self._single(self._by_login, login.casefold())
        if email is not None:
            return self._single(self._by_email, email.lower())
        if name is not None:
            return self._single(self._by_name, fold(name))
        return None

    def person_for_username(self, username):
        """The person behind `person:<id>` or a GitHub login."""
        if username.startswith(PERSON_PREFIX):
            return self.people.get(username[len(PERSON_PREFIX):])
        return self.person_for(login=username)

    def username_of(self, person):
        """The username the collected files count the person under: the GitHub login, else `person:<id>`."""
        return person.github or f'{PERSON_PREFIX}{person.id}'

    def organisation_of(self, person_id, year):
        """The name of the organisation the person belonged to in the year, else UNMAPPED."""
        for affiliation in self.affiliations:
            if affiliation.person == person_id and affiliation.covers(year):
                return self.organisation_name(affiliation.organisation)
        return UNMAPPED

    def organisation_for_username(self, username, year):
        """The organisation of the person behind a username in the year, else UNMAPPED."""
        person = self.person_for_username(username)
        return self.organisation_of(person.id, year) if person else UNMAPPED

    def login_organisations(self, year):
        """The organisation of each GitHub login (including second accounts) that has one in the year."""
        logins = [(person.github, person.id) for person in self.people.values() if person.github]
        logins += [(i.value, i.person) for i in self.identities if i.kind == 'login']
        result = {}
        for login, person_id in logins:
            if len(self._by_login[login.casefold()]) != 1:
                continue  # an ambiguous login, as person_for sees it
            organisation = self.organisation_of(person_id, year)
            if organisation != UNMAPPED:
                result[login] = organisation
        return result

    def organisation_name(self, org_id):
        """The name of an organisation."""
        return self.organisations[org_id].name

    def organisation_id(self, name_or_alias):
        """The id of the organisation with this name or alias, ignoring case and punctuation; else None."""
        return self._organisation_ids.get(fold(name_or_alias))

    def match_domain(self, domain):
        """(organisation id, how) of a mail domain, else None; how is "alias", "name" or "first word".

        Tried in this order, the first tier with a unique hit wins:
        1. an alias written as a domain (`kuleuven.be`) matches that domain and its subdomains;
        2. each label of the domain but the last (`icts.kuleuven.be`: `icts`, then `kuleuven`), folded, equals the
           folded name or an alias of an organisation proper, written without spaces;
        3. a label equals the first word of such a name or alias.
        A key that belongs to several organisations matches none. Add a domain to the `aliases` of its
        organisation when the name does not give it away.
        """
        domain = domain.strip().lower()
        for alias, ids in self._domain_aliases.items():
            if len(ids) == 1 and (domain == alias or domain.endswith('.' + alias)):
                return next(iter(ids)), 'alias'
        keys = [fold(label).replace(' ', '') for label in domain.split('.')[:-1]]
        for key in keys:
            kinds = self._name_keys.get(key, {})
            if len(kinds) == 1:
                return next(iter(kinds.items()))
        for key in keys:
            ids = self._first_words.get(key, set())
            if len(ids) == 1:
                return next(iter(ids)), 'first word'
        return None

    def organisation_for_domain(self, domain):
        """The id of the organisation that a mail domain belongs to, else None; see match_domain."""
        match = self.match_domain(domain)
        return match[0] if match else None

    def is_counted_organisation(self, name):
        """Whether the name is an organisation proper, not an independent person, the foundation or Unmapped."""
        org_id = self.organisation_id(name)
        return org_id is not None and self.organisations[org_id].kind == 'organisation'

    def display_name(self, username):
        """The name of the person behind a username; the username itself when the register does not know it."""
        person = self.person_for_username(username)
        return person.name if person else username


def load_registry(mappings_dir=paths.MAPPINGS_DIR):
    """Read the four register files in the directory."""
    people = [Person(r['id'], r['name'], r['github'], r['source'])
              for r in read_rows(mappings_dir / paths.PEOPLE.name)]
    identities = [Identity(r['person'], r['kind'], r['value'], r['source'])
                  for r in read_rows(mappings_dir / paths.IDENTITIES.name)]
    affiliations = [Affiliation(r['person'], r['organisation'], r['from'], r['to'], r['source'], r['checked'],
                                r['notes'])
                    for r in read_rows(mappings_dir / paths.AFFILIATIONS.name)]
    organisations = [Organisation(r['id'], r['name'], r['kind'], r['github'], split_set(r['aliases']), r['notes'])
                     for r in read_rows(mappings_dir / paths.ORGANISATIONS.name)]
    return Registry(people, identities, affiliations, organisations)


def _list_rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_excluded_repositories(path=paths.EXCLUDED_REPOSITORIES):
    """Load the repositories to skip, mapped to the reason for skipping them."""
    return {row['repository'].strip(): row['reason'].strip() for row in _list_rows(path)}


def load_bot_accounts(path=paths.BOT_ACCOUNTS):
    """Load bot accounts that the GitHub API lists as type User, mapped to a reason."""
    return {row['login'].strip(): row['reason'].strip() for row in _list_rows(path)}


MAPPINGS_DIR = paths.MAPPINGS_DIR  # where the tools write, so that they need not name curated/
PEOPLE_FIELDS = ('id', 'name', 'github', 'source')


def append_person(mappings_dir, person):
    """Add the person to people.csv, which stays sorted by id; ValueError for an existing id or login."""
    path = mappings_dir / paths.PEOPLE.name
    rows = [{field: row[field] or '' for field in PEOPLE_FIELDS} for row in read_rows(path)]
    if any(row['id'] == person.id for row in rows):
        raise ValueError(f'The id {person.id} exists already')
    if person.github and any(row['github'].casefold() == person.github.casefold() for row in rows):
        raise ValueError(f'The login {person.github} exists already')
    rows.append({'id': person.id, 'name': person.name, 'github': person.github or '', 'source': person.source})
    rows.sort(key=lambda row: row['id'])
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=PEOPLE_FIELDS, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


PROPOSAL_FIELDS = ('person', 'organisation', 'from', 'to', 'evidence')


def load_rejection_rows(mappings_dir=MAPPINGS_DIR):
    """The rows of rejected_proposals.csv as dicts, with their reason and source; [] when the file is missing."""
    try:
        return read_rows(mappings_dir / paths.REJECTED_PROPOSALS.name)
    except FileNotFoundError:
        return []


def load_rejections(mappings_dir=MAPPINGS_DIR):
    """{(person, organisation, year)} of rejected_proposals.csv: evidence a reviewer turned down, which the tools
    don't propose again. An empty set when the file is missing."""
    return {(row['person'], row['organisation'], year)
            for row in load_rejection_rows(mappings_dir) for year in range(row['from'], row['to'] + 1)}


def append_proposals(rows, mappings_dir=MAPPINGS_DIR):
    """Append rows to affiliation_proposals.csv, leaving out those that are in it already; return those added.

    A row is a dict with the keys person, organisation, from, to and evidence. It is in the file already when
    a row has the same person, organisation, first and last year.
    """
    path = mappings_dir / paths.AFFILIATION_PROPOSALS.name

    def key(row):
        return (row['person'], row['organisation'], int(row['from']), int(row['to']) if row['to'] else None)

    known = {key(row) for row in read_rows(path)}
    added = []
    for row in rows:
        if key(row) not in known:
            known.add(key(row))
            added.append(row)
    if added:
        with open(path, 'rb') as f:
            content = f.read()
        with open(path, 'a', newline='', encoding='utf-8') as f:
            if content and not content.endswith(b'\n'):
                f.write('\n')
            writer = csv.DictWriter(f, fieldnames=PROPOSAL_FIELDS, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            writer.writerows({field: '' if row[field] is None else row[field] for field in PROPOSAL_FIELDS}
                             for row in added)
    return added
