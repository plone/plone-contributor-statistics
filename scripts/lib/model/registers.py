"""The registers of people, identities, affiliations, citations and organisations, and the lookups on them."""

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.attribution import DENIED, PROPOSED, Affiliation, Attribution, Citation
from scripts.lib.model.names import fold
from scripts.lib.model import sources as _sources  # the module: its atomic write
from scripts.lib.model.schema import read_rows, split_set
from scripts.lib.model.sources import load_sources

UNMAPPED = 'Unmapped'
PERSON_PREFIX = 'person:'
MIN_DOMAIN_KEY = 3  # the first word of an organisation name is a key for domains only from this length on
GITHUB = 'github'  # the login the collected files count a person under; at most one per person
GITHUB_ALIAS = 'github-alias'  # a further GitHub account of the person
LOGIN_KINDS = (GITHUB, GITHUB_ALIAS)
UNIQUE_IDENTITY_KINDS = (GITHUB, GITHUB_ALIAS, 'email')  # one person's each; a name may be shared by homonyms


@dataclass(frozen=True)
class Person:
    id: str
    name: str


@dataclass(frozen=True)
class Identity:
    person: str
    kind: str
    value: str
    source: str | None
    snippet: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Organisation:
    id: str
    name: str
    kind: str
    github: str | None
    aliases: tuple
    notes: str | None


def _no_attribution_inputs(citations):
    return lambda: (list(citations), {}, lambda source_id: '', lambda year: {})


class Registry:
    """The registers, indexed for the lookups the pipeline needs.

    A login finds a person through a `github` or `github-alias` identity. A name finds a person through a `name`
    identity of any length, or through the display name in people.csv when that has more than one word: a
    one-word display name, such as a login used as the name, is not evidence that the person wrote a changelog
    entry signed with that word. A `name` identity that spells the display name (the public record of the name
    of a person without GitHub) follows the rule of the display name.

    The organisation of a person in a year is computed by the attribution rules (`Attribution`) from the
    affiliations, their citations, the sources and the commit domains. `attribution_inputs` is a function that
    returns (citations, {id: Source}, excerpt(source id), commit_domains(year)); it is called on the first
    question about an organisation, so code that never asks reads none of them. Without it, the registry uses
    `citations` and no sources.
    """

    def __init__(self, people, identities, affiliations, organisations, citations=(), *, attribution_inputs=None):
        self.people = {person.id: person for person in people}
        self.identities = list(identities)
        self.affiliations = list(affiliations)
        self.organisations = {organisation.id: organisation for organisation in organisations}
        self._attribution_inputs = attribution_inputs or _no_attribution_inputs(citations)
        self._inputs = None
        self._attribution = None
        self._github = {}
        self._logins = {}
        self._by_login = {}
        self._by_email = {}
        self._by_name = {}
        for person in self.people.values():
            if len(fold(person.name).split()) > 1:
                self._by_name.setdefault(fold(person.name), set()).add(person.id)
        for identity in self.identities:
            if identity.kind in LOGIN_KINDS:
                if identity.kind == GITHUB:
                    self._github.setdefault(identity.person, identity.value)
                self._logins.setdefault(identity.person, []).append(identity.value)
                self._by_login.setdefault(identity.value.casefold(), set()).add(identity.person)
            elif identity.kind == 'email':
                self._by_email.setdefault(identity.value.lower(), set()).add(identity.person)
            elif identity.kind == 'name':
                person = self.people.get(identity.person)
                if person is not None and fold(identity.value) == fold(person.name):
                    continue  # the display name, indexed above when it has more than one word
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

    def github_of(self, person_id):
        """The `github` login of the person, else None."""
        return self._github.get(person_id)

    def logins_of(self, person_id):
        """Every GitHub login of the person: the `github` one and the further accounts, in register order."""
        return list(self._logins.get(person_id, []))

    def username_of(self, person):
        """The username the collected files count the person under: the `github` login, else `person:<id>`."""
        return self.github_of(person.id) or f'{PERSON_PREFIX}{person.id}'

    def _attribution_data(self):
        if self._inputs is None:
            self._inputs = self._attribution_inputs()
        return self._inputs

    @property
    def citations(self):
        """The citations of the affiliations."""
        return self._attribution_data()[0]

    @property
    def sources(self):
        """{id: Source} of the source register."""
        return self._attribution_data()[1]

    @property
    def attribution(self):
        """The attribution rules over the registers, built on first use."""
        if self._attribution is None:
            citations, sources, excerpt, commit_domains = self._attribution_data()
            self._attribution = Attribution(
                self.affiliations, citations, sources, excerpt, commit_domains, match_domain=self.match_domain,
                name_of=lambda person_id: self.people[person_id].name if person_id in self.people else '',
                logins_of=self.logins_of,
                username_of=lambda person_id: (self.username_of(self.people[person_id])
                                               if person_id in self.people else None),
                names_of_organisation=lambda org_id: ([self.organisations[org_id].name,
                                                       *self.organisations[org_id].aliases]
                                                      if org_id in self.organisations else []))
        return self._attribution

    def organisation_of(self, person_id, year):
        """The name of the organisation the person counts for in the year, else UNMAPPED."""
        org_id = self.attribution.organisation(person_id, year)
        return self.organisation_name(org_id) if org_id is not None else UNMAPPED

    def organisation_for_username(self, username, year):
        """The organisation of the person behind a username in the year, else UNMAPPED."""
        person = self.person_for_username(username)
        return self.organisation_of(person.id, year) if person else UNMAPPED

    def login_organisations(self, year):
        """The organisation of each GitHub login (including further accounts) that has one in the year."""
        result = {}
        for identity in self.identities:
            if identity.kind not in LOGIN_KINDS:
                continue
            if len(self._by_login[identity.value.casefold()]) != 1:
                continue  # an ambiguous login, as person_for sees it
            organisation = self.organisation_of(identity.person, year)
            if organisation != UNMAPPED:
                result[identity.value] = organisation
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


def _excerpt_reader(root):
    def read(source_id):
        path = Path(root) / paths.EXCERPTS_DIR / f'{source_id}.md'
        return path.read_text(encoding='utf-8') if path.is_file() else ''
    return read


def _commit_domains_reader(root):
    def read(year):
        # Imported here: commit_domains imports commit_authors, which imports the model
        from scripts.lib.commit_domains import load_commit_domains
        try:
            return load_commit_domains(year, root)
        except FileNotFoundError:
            return {}
    return read


def load_citations(mappings_dir=paths.MAPPINGS_DIR):
    """The rows of citations.csv."""
    return [Citation(r['affiliation'], r['source'], r['snippet'], r['supersedes'], r['notes'])
            for r in read_rows(Path(mappings_dir) / paths.CITATIONS.name)]


def load_identities(mappings_dir=paths.MAPPINGS_DIR):
    """The rows of identities.csv."""
    return [Identity(r['person'], r['kind'], r['value'], r['source'], r['snippet'], r['notes'])
            for r in read_rows(Path(mappings_dir) / paths.IDENTITIES.name)]


def load_registry(mappings_dir=paths.MAPPINGS_DIR):
    """Read the registers in the directory; the citations, sources, excerpts and commit domains on first use.

    The sources, their excerpts and the commit domains are read from the repository the directory is part of.
    This assumes the layout of the repository: the directory is `curated/mappings`, two levels below the root
    (`mappings_dir.parent.parent`), as in the checkout and in the temporary repositories of the tests. A
    directory elsewhere gets the sources and commit domains of whatever lies two levels above it.
    """
    mappings_dir = Path(mappings_dir)
    root = mappings_dir.parent.parent
    people = [Person(r['id'], r['name']) for r in read_rows(mappings_dir / paths.PEOPLE.name)]
    identities = load_identities(mappings_dir)
    affiliations = [Affiliation(r['id'], r['person'], r['organisation'], r['from'], r['to'], r['status'],
                                r['checked'], r['notes'])
                    for r in read_rows(mappings_dir / paths.AFFILIATIONS.name)]
    organisations = [Organisation(r['id'], r['name'], r['kind'], r['github'], split_set(r['aliases']), r['notes'])
                     for r in read_rows(mappings_dir / paths.ORGANISATIONS.name)]

    def inputs():
        return (load_citations(mappings_dir), load_sources(root / paths.SOURCES), _excerpt_reader(root),
                _commit_domains_reader(root))

    return Registry(people, identities, affiliations, organisations, attribution_inputs=inputs)


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
PEOPLE_FIELDS = ('id', 'name')
IDENTITY_FIELDS = ('person', 'kind', 'value', 'source', 'snippet', 'notes')
AFFILIATION_FIELDS = ('id', 'person', 'organisation', 'from', 'to', 'status', 'checked', 'notes')
CITATION_FIELDS = ('affiliation', 'source', 'snippet', 'supersedes', 'notes')


def _cell(value):
    if value is None:
        return ''
    return value.isoformat() if isinstance(value, date) else str(value)


def _write_rows(path, fields, rows):
    """Write the rows (dicts as read_rows returns them, or of texts) under the header of the fields, atomically:
    readers see the old file or the whole new one."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writeheader()
    writer.writerows({field: _cell(row.get(field)) for field in fields} for row in rows)
    _sources._write_atomic(path, buffer.getvalue())


def _citation_key(row):
    """The order of citations.csv: affiliation, source, snippet (an empty snippet first)."""
    return (row['affiliation'], row['source'], row['snippet'] or '')


def _identity_key(row):
    """The order of identities.csv: person, kind, value."""
    return (row['person'], row['kind'], row['value'])


def write_citations(citations, mappings_dir=MAPPINGS_DIR):
    """Replace citations.csv by the citations (Citation rows), sorted as the checks expect, atomically."""
    rows = [{field: getattr(citation, field) for field in CITATION_FIELDS} for citation in citations]
    _write_rows(Path(mappings_dir) / paths.CITATIONS.name, CITATION_FIELDS, sorted(rows, key=_citation_key))


def write_identities(identities, mappings_dir=MAPPINGS_DIR):
    """Replace identities.csv by the identities (Identity rows), sorted as the checks expect, atomically."""
    rows = [{field: getattr(identity, field) for field in IDENTITY_FIELDS} for identity in identities]
    _write_rows(Path(mappings_dir) / paths.IDENTITIES.name, IDENTITY_FIELDS, sorted(rows, key=_identity_key))


def affiliation_id(person, organisation, start, end):
    """The opaque id of an affiliation: `a` and eight hex digits of a hash over its person, organisation and
    years at creation; it is never recomputed when the row changes later."""
    end = '' if end is None else end
    return 'a' + hashlib.sha1(f'{person}|{organisation}|{start}|{end}'.encode()).hexdigest()[:8]


def _same_identity(row, identity):
    """Whether the identity row records the identity's login or address (ignoring case), or is the same row."""
    if row['value'].casefold() != identity.value.casefold():
        return False
    if identity.kind in LOGIN_KINDS:  # a login is one person's, whether as the github one or a further account
        return row['kind'] in LOGIN_KINDS
    if identity.kind in UNIQUE_IDENTITY_KINDS:
        return row['kind'] == identity.kind
    return (row['person'], row['kind'], row['value']) == (identity.person, identity.kind, identity.value)


def append_person(mappings_dir, person, identity):
    """Add the person to people.csv and the identity that records the name or login to identities.csv.

    Both files stay sorted. ValueError for an existing id, or for an identity that exists already: a GitHub login
    or an address (ignoring case) of anyone. A name may be the name of another person too (homonyms).
    """
    mappings_dir = Path(mappings_dir)
    people = read_rows(mappings_dir / paths.PEOPLE.name)
    identities = read_rows(mappings_dir / paths.IDENTITIES.name)
    if any(row['id'] == person.id for row in people):
        raise ValueError(f'The id {person.id} exists already')
    if any(_same_identity(row, identity) for row in identities):
        what = 'login' if identity.kind in LOGIN_KINDS else identity.kind
        raise ValueError(f'The {what} {identity.value} exists already')
    people.append({'id': person.id, 'name': person.name})
    identities.append({field: getattr(identity, field) for field in IDENTITY_FIELDS})
    _write_rows(mappings_dir / paths.PEOPLE.name, PEOPLE_FIELDS, sorted(people, key=lambda row: row['id']))
    _write_rows(mappings_dir / paths.IDENTITIES.name, IDENTITY_FIELDS, sorted(identities, key=_identity_key))


def load_rejections(mappings_dir=MAPPINGS_DIR):
    """{(person, organisation, year)} of the `denied` affiliations: readings a reviewer turned down, which the
    tools don't propose again. An open-ended denial runs to the current year."""
    return {(row['person'], row['organisation'], year)
            for row in read_rows(Path(mappings_dir) / paths.AFFILIATIONS.name) if row['status'] == DENIED
            for year in range(row['from'], (row['to'] or date.today().year) + 1)}


def append_proposals(rows, mappings_dir=MAPPINGS_DIR):
    """Add rows as `proposed` affiliations with their citations, leaving out those in the register already;
    return those added.

    A row is a dict with the keys person, organisation, from, to and sources, a list of (source id, snippet) or
    (source id, snippet, notes of the citation), and optionally notes. It is in the register already when an
    affiliation of any status has the same person, organisation, first and last year. Both files stay sorted.
    ValueError, and nothing written, when the id of a new row is the id of an affiliation already: ids are not
    recomputed when a row changes, so a row whose years changed later keeps the id of its first years.
    """
    mappings_dir = Path(mappings_dir)
    affiliations = read_rows(mappings_dir / paths.AFFILIATIONS.name)
    citations = read_rows(mappings_dir / paths.CITATIONS.name)

    def key(row):
        return (row['person'], row['organisation'], int(row['from']), int(row['to']) if row['to'] else None)

    known = {key(row) for row in affiliations}
    ids = {row['id'] for row in affiliations}
    added = []
    for row in rows:
        if key(row) in known:
            continue
        known.add(key(row))
        aid = affiliation_id(*key(row))
        if aid in ids:
            raise ValueError(f'The id {aid} of the proposal {row["person"]}, {row["organisation"]}, '
                             f'{row["from"]}-{row["to"] or ""} is the id of an affiliation already')
        ids.add(aid)
        added.append(row)
        affiliations.append({'id': aid, 'person': row['person'], 'organisation': row['organisation'],
                             'from': int(row['from']), 'to': int(row['to']) if row['to'] else None,
                             'status': PROPOSED, 'checked': None, 'notes': row.get('notes')})
        for source, snippet, *notes in row['sources']:
            citations.append({'affiliation': aid, 'source': source, 'snippet': snippet or None, 'supersedes': None,
                              'notes': (notes[0] if notes else None) or None})
    if added:
        _write_rows(mappings_dir / paths.AFFILIATIONS.name, AFFILIATION_FIELDS,
                    sorted(affiliations, key=lambda row: (row['person'], row['from'], row['organisation'])))
        _write_rows(mappings_dir / paths.CITATIONS.name, CITATION_FIELDS, sorted(citations, key=_citation_key))
    return added
