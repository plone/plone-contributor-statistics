#!/usr/bin/env python3
"""Migrate the curated files to the people register (#139).

fetch-names is the one online step: it fetches the GitHub profile names of the
logins that no curated file names, and writes them to a file that the
migration reads. It needs GITHUB_TOKEN in the environment.

run is the migration itself, offline: it writes people.csv, identities.csv,
affiliations.csv, organisations.csv and affiliation_proposals.csv from the old
mapping files, rewrites the community files to ids, renames the commit authors
without a login in the collected files to person:<id>, deletes the old mapping
files and prints a report in Markdown. It takes no decision a person has to
take: what the old files state but the mapping does not becomes a proposal.
"""

import argparse
import contextlib
import csv
import io
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

from scripts.lib import paths
from scripts.lib.model.names import fold, slugify
from scripts.tools.migrate_data import community as old_community
from scripts.tools.migrate_data import legacy_community as community
from scripts.tools.migrate_data.legacy_mappings import (
    ACCOUNT_ALIASES, CHANGELOG_NAMES, COMMIT_AUTHORS, FULLNAMES, OVERRIDES, PROPOSALS, SOURCES, _rows,
    load_organisation_mapping, read_overrides)
from scripts.tools.migrate_data.legacy_people import PROFILE_LINK, build_person_index
from scripts.tools.migrate_data.organisation_aliases import ORGANISATION_ALIASES
from scripts.tools.unmatched_names import fetch_profile_names

FIRST_YEAR = 2003
LAST_YEAR = 2026
# The affiliations are materialised from this year on, as the specification says
AFFILIATION_FIRST_YEAR = 2002
UNMAPPED = 'Unmapped'
PLONE_FOUNDATION = 'Plone Foundation'
PERSON_PREFIX = 'person:'
NOT_VERIFIED = 'range from the current entry; years before {year} not verified (#139)'
OLD_FILES = (OVERRIDES, SOURCES, PROPOSALS, COMMIT_AUTHORS, ACCOUNT_ALIASES,
             FULLNAMES, CHANGELOG_NAMES)
HEADERS = {
    paths.PEOPLE: ['id', 'name', 'github', 'source'],
    paths.IDENTITIES: ['person', 'kind', 'value', 'source'],
    paths.AFFILIATIONS: ['person', 'organisation', 'from', 'to', 'source', 'checked', 'notes'],
    paths.ORGANISATIONS: ['id', 'name', 'kind', 'aliases', 'notes'],
    paths.AFFILIATION_PROPOSALS: ['person', 'organisation', 'from', 'to', 'evidence'],
}


def _proposal_logins(root):
    """The contributors of the old proposals file that are logins, not commit author names."""
    path = root / PROPOSALS
    if not path.exists():
        return set()
    names = {row['name'].strip() for row in _rows(root / COMMIT_AUTHORS) if not row['github_username'].strip()}
    return {row['contributor'].strip() for row in _rows(path)
            if ' ' not in row['contributor'].strip() and row['contributor'].strip() not in names}


def _login_cells(root):
    """Every login that the mapping files name, as a set."""
    logins = set()
    for row in _rows(root / paths.ORGANISATIONS):
        logins.update(part.strip() for part in row['Team'].split(';') if part.strip())
    for path in (OVERRIDES, SOURCES):
        if (root / path).exists():
            logins.update(row['github_username'].strip() for row in _rows(root / path))
    logins.update(row['github_username'].strip() for row in _rows(root / COMMIT_AUTHORS))
    logins.update(row['github_username'].strip() for row in _rows(root / ACCOUNT_ALIASES))
    logins.update(_proposal_logins(root))
    logins.discard('')
    return logins


def logins_without_a_name(root=Path('.')):
    """Logins of the mapping files that no curated file gives a name.

    A login is named by a row of the fullname mapping, by a handle column of
    the community data, or by a name in commit_authors.csv.
    """
    root = Path(root)
    named = {row['github username'].strip().casefold() for row in _rows(root / FULLNAMES)}
    named.update(row['github_username'].strip().casefold()
                 for row in _rows(root / COMMIT_AUTHORS) if row['name'].strip())
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        named.update(record.handle.casefold()
                     for record in community.community_records(year, root / paths.COMMUNITY) if record.handle)
    return {login for login in _login_cells(root) if login.casefold() not in named}


def write_profile_names(names, path):
    """Write login, name and fetch date, sorted by login; a login without a profile name is its own name."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['login', 'name', 'fetched'])
        for login in sorted(names):
            writer.writerow([login, names[login] or login, today])


def fetch_names(out):
    """Fetch the profile names of the unnamed logins and write them to `out`."""
    load_dotenv()
    session = requests.Session()
    token = os.getenv('GITHUB_TOKEN')
    if token:
        session.headers['Authorization'] = f'token {token}'
    logins = sorted(logins_without_a_name())
    fetched = fetch_profile_names(session, logins)
    write_profile_names({login: fetched.get(login, '') for login in logins}, out)
    print(f'{len(logins)} logins, {sum(1 for login in logins if fetched.get(login))} with a profile name')


# The migration


@dataclass
class Report:
    """What the migration wrote, and everything it could not carry into a register row as it was."""

    people: int = 0
    identities: int = 0
    organisations: int = 0
    affiliations: int = 0
    proposals: int = 0
    proposal_kinds: Counter = field(default_factory=Counter)
    # (alias, target, reason)
    dropped_aliases: list = field(default_factory=list)
    # (organisation name, reason)
    added_organisations: list = field(default_factory=list)
    # (file, old username, new username, rows)
    renamed_usernames: list = field(default_factory=list)
    # (file, line, cut text)
    cut_sources: list = field(default_factory=list)
    # (file, line, persons, organisations): organisation cells that could not be paired with the persons
    unaligned: list = field(default_factory=list)
    # (file, line, entry): entries of person columns that are no person
    dropped_groups: list = field(default_factory=list)
    # (file, line, what): what the new files cannot hold
    unrepresentable: list = field(default_factory=list)
    # (base id, resulting ids, logins): people whose names give the same id, to review as possible duplicates
    id_collisions: list = field(default_factory=list)
    # (file, line, names, handles): handles not used because they are not one per name
    dropped_handles: list = field(default_factory=list)


def _read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


@dataclass
class Old:
    """The old curated files, read once."""

    root: Path
    organisation_names: list
    team: dict
    overrides: list
    sources: dict
    proposals: list
    fullnames: list
    commit_authors: list
    aliases: list
    changelog_names: list
    rows: list

    @classmethod
    def read(cls, root):
        overrides = read_overrides(root / OVERRIDES)
        for override, row in zip(overrides, _read(root / OVERRIDES)):
            override['source'] = row['source'].strip()
        team = {}
        for row in _read(root / paths.ORGANISATIONS):
            for login in (part.strip() for part in row['Team'].split(';')):
                if login:
                    team[login] = row['Organisation'].strip()
        changelog_path = root / CHANGELOG_NAMES
        return cls(
            root=root,
            organisation_names=[row['Organisation'].strip() for row in _read(root / paths.ORGANISATIONS)],
            team=team,
            overrides=overrides,
            sources={row['github_username'].strip().casefold(): row for row in _read(root / SOURCES)},
            proposals=_read(root / PROPOSALS) if (root / PROPOSALS).exists() else [],
            fullnames=_read(root / FULLNAMES),
            commit_authors=_read(root / COMMIT_AUTHORS),
            aliases=_read(root / ACCOUNT_ALIASES),
            changelog_names=_read(changelog_path) if changelog_path.exists() else [],
            rows=old_community.read_rows(root),
        )

    @property
    def commit_authors_path(self):
        return self.root / COMMIT_AUTHORS

    @property
    def fullnames_path(self):
        return self.root / FULLNAMES

    @property
    def proposal_logins(self):
        return _proposal_logins(self.root)


class Organisations:
    """The organisations register: rows, and the lookup of a spelling or alias to an id."""

    def __init__(self, old, report):
        names = list(old.organisation_names)
        if PLONE_FOUNDATION not in names:
            names.append(PLONE_FOUNDATION)
        self.rows = []
        self._ids = {}
        used = set()
        for name in names:
            self._add(name, used)
        self.used = used
        self.report = report
        self._aliases(report)

    def _add(self, name, used, notes=''):
        org_id = _unique_id(slugify(name), used, name)
        kind = 'independent' if name.endswith('(independent)') else 'foundation' if name == PLONE_FOUNDATION \
            else 'organisation'
        row = {'id': org_id, 'name': name, 'kind': kind, 'aliases': [], 'notes': notes}
        self.rows.append(row)
        self._ids.setdefault(fold(name), org_id)
        return org_id

    def _aliases(self, report):
        by_id = {row['id']: row for row in self.rows}
        for alias, target in ORGANISATION_ALIASES.items():
            if target == UNMAPPED:
                continue
            org_id = self._ids.get(fold(target))
            if org_id is None or fold(by_id[org_id]['name']) != fold(target):
                report.dropped_aliases.append((alias, target, 'the target is no organisation'))
                continue
            other = self._ids.get(fold(alias))
            if other is not None and other != org_id:
                report.dropped_aliases.append((alias, target, f'folds to the name or an alias of {other}'))
                continue
            by_id[org_id]['aliases'].append(alias)
            self._ids.setdefault(fold(alias), org_id)

    def id_for(self, spelling):
        """The id of the organisation with this name or alias, ignoring case and punctuation; else None."""
        return self._ids.get(fold(spelling))

    def id_or_add(self, spelling, reason):
        """The id of the organisation; an organisation no file has a row for gets one, with the reason."""
        org_id = self.id_for(spelling)
        if org_id is None:
            org_id = self._add(spelling, self.used, notes=f'added by the migration: {reason} (#139)')
            self.report.added_organisations.append((spelling, reason))
        return org_id

    def names(self):
        return {row['name'] for row in self.rows}

    def register(self):
        """The rows of organisations.csv, sorted by id ignoring case."""
        return [{**row, 'aliases': ';'.join(row['aliases'])}
                for row in sorted(self.rows, key=lambda row: row['id'].casefold())]


def _unique_id(base, used, what):
    """The base id, or base-2, base-3 when it is taken; ValueError for an empty base."""
    if not base:
        raise ValueError(f'"{what}" gives no id')
    candidate, number = base, 1
    while candidate in used:
        number += 1
        candidate = f'{base}-{number}'
    used.add(candidate)
    return candidate


class People:
    """The people register, built from the person index of the old files.

    A person is keyed during the build by the casefolded login or by `name:<normalised name>`, as the old
    person index keys them; account aliases key to their main login.
    """

    def __init__(self, old, organisations, profile_names):
        self.old = old
        self.index = build_person_index(old_community.records(old.rows), commit_authors_path=old.commit_authors_path,
                                        fullnames_path=old.fullnames_path, organisations=organisations.names())
        self.alias_keys = {row['alias'].strip().casefold(): row['github_username'].strip().casefold()
                           for row in old.aliases}
        self.profile_spellings = [row['login'].strip() for row in _read(profile_names)]
        self.profile_names = {row['login'].strip().casefold(): row['name'].strip() for row in _read(profile_names)}
        self.spelling = {}
        self.spellings = defaultdict(list)
        self.community = defaultdict(Counter)
        self.community_source = {}
        self.keys = set()
        self._collect()
        self.ids = {}
        self.rows = {}
        self._build()

    def key(self, name='', handle='', row_organisations=()):
        """The build key of a person cell; None for a group."""
        key = self.index.key(name, handle, row_organisations)
        return self.alias_keys.get(key, key) if key else None

    def login_key(self, login):
        return self.alias_keys.get(login.strip().casefold(), login.strip().casefold())

    def person_id(self, name, handle='', row_organisations=()):
        key = self.key(name, handle, row_organisations)
        return self.ids[key] if key else None

    def has_login(self, person_id):
        return bool(self.rows[person_id]['github'])

    def _login(self, login):
        key = self.login_key(login)
        if key.startswith('name:'):
            raise ValueError(f'"{login}" is no login')
        self.spelling.setdefault(key, login.strip())
        self.keys.add(key)
        return key

    def _collect(self):
        old = self.old
        for login in old.team:
            self._login(login)
        for override in old.overrides:
            self._login(override['github_username'])
        for row in old.sources.values():
            self._login(row['github_username'])
        for row in old.fullnames:
            key = self._login(row['github username'])
            self.spellings[key].append((row['fullname'].strip(), row['source'].strip(), 'fullname'))
        for row in old.commit_authors + old.changelog_names:
            name = (row.get('name') or '').strip()
            login = row['github_username'].strip()
            key = self._login(login) if login else self.key(name)
            if key is None:
                raise ValueError(f'commit author or changelog name "{name}" is neither a login nor a person')
            self.keys.add(key)
            if not login and not key.startswith('name:'):
                raise ValueError(f'"{name}" has no login, but the person index links the name to {key}')
            if name:
                self.spellings[key].append((name, row['source'].strip(), 'commit'))
            if row.get('changelog_name', '').strip():
                self.spellings[key].append((row['changelog_name'].strip(), row['source'].strip(), 'changelog'))
        for row in old.aliases:
            self._login(row['github_username'])
        for login in sorted(old.proposal_logins):
            self._login(login)
        for old_row in old.rows:
            source, _ = old_community.cut_source(old_row)
            organisations = old_community.split(old_row.row.get('Organisation'))
            for link in PROFILE_LINK.findall(old_row.row.get('Source') or ''):
                self.spelling.setdefault(link.casefold(), link)
            for name, handle in old_community.people_cells(old_row):
                key = self.key(name, handle, organisations)
                if key is None:
                    continue
                if handle.casefold() == key:  # not a second account's handle
                    self.spelling.setdefault(key, handle)
                self.keys.add(key)
                self.community[key][name] += 1
                self.spellings[key].append((name, source, 'community'))
                self.community_source.setdefault(key, old_community.first_link(source))
        for login in self.profile_spellings:
            self.spelling.setdefault(login.casefold(), login)

    def _name(self, key):
        """(name, source) of a person, by the rules of the specification."""
        spellings = self.spellings[key]
        fullnames = [(name, source) for name, source, origin in spellings if origin == 'fullname']
        if key.startswith('name:'):
            login = ''
        else:
            login = self.spelling[key]
            if fullnames:
                profile = [row for row in fullnames if row[1].startswith('GitHub profile name:')]
                return (profile or fullnames)[0]
            source = f'https://github.com/{login}'
            if key in self.profile_names:
                return self.profile_names[key], source
        counts = self.community[key]
        if counts:
            order = [name for name, _, origin in spellings if origin == 'community']
            name = max(counts, key=lambda spelling: (counts[spelling], -order.index(spelling)))
            return name, source if login else self.community_source[key]
        others = [(name, source) for name, source, origin in spellings if origin != 'community']
        if others:
            return others[0][0], source if login else (old_community.first_link(others[0][1]) or others[0][1])
        if login:
            return login, source
        raise ValueError(f'no name for {key}')

    def _build(self):
        logins = sorted(key for key in self.keys if not key.startswith('name:'))
        names = {key: self._name(key) for key in self.keys}
        named = sorted((key for key in self.keys if key.startswith('name:')), key=lambda k: (fold(names[k][0]), k))
        used = set()
        bases = defaultdict(list)
        for key in logins + named:
            name, source = names[key]
            login = '' if key.startswith('name:') else self.spelling[key]
            base = slugify(name) or slugify(login)
            person_id = _unique_id(base, used, name)
            bases[base].append((person_id, login))
            self.ids[key] = person_id
            self.rows[person_id] = {'id': person_id, 'name': name, 'github': login, 'source': source}
        # (base id, resulting ids, logins) of every base that more than one person needed
        self.collisions = [(base, ';'.join(i for i, _ in found), ';'.join(login for _, login in found))
                           for base, found in sorted(bases.items()) if len(found) > 1]

    def register(self):
        return [self.rows[person_id] for person_id in sorted(self.rows)]

    def identities(self):
        """The rows of identities.csv: other spellings, commit addresses and second accounts."""
        found = []
        for key, spellings in sorted(self.spellings.items()):
            person = self.rows[self.ids[key]]
            seen = {person['name'].casefold()}
            for name, source, _ in spellings:
                if name.casefold() not in seen:
                    seen.add(name.casefold())
                    found.append({'person': person['id'], 'kind': 'name', 'value': name, 'source': source})
        emails = {}
        for row in self.old.commit_authors:
            email = row['email'].strip().lower()
            login = row['github_username'].strip()
            person = self.ids[self.login_key(login) if login else self.key(row['name'])]
            if email in emails:
                if emails[email] != person:
                    raise ValueError(f'commit_authors.csv gives {email} to {emails[email]} and to {person}')
                continue
            emails[email] = person
            found.append({'person': person, 'kind': 'email', 'value': email, 'source': row['source'].strip()})
        for row in self.old.aliases:
            found.append({'person': self.ids[self.login_key(row['github_username'])], 'kind': 'login',
                          'value': row['alias'].strip(), 'source': row['source'].strip()})
        return sorted(found, key=lambda row: (row['person'], row['kind'], row['value']))


def _quiet(function, *args, **kwargs):
    """Call a function that prints, without the output."""
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def build_affiliations(root, old, people, organisations, until):
    """The rows of affiliations.csv: the organisation mapping of each year made explicit as ranges.

    A range comes either from the current entry (the `Team` column, with the record of the sources file)
    or from one override; `Unmapped` gives no row.
    """
    mappings = {}
    for year in range(AFFILIATION_FIRST_YEAR, until + 1):
        mapping = _quiet(load_organisation_mapping, root / paths.ORGANISATIONS, root / OVERRIDES, year=year)
        folded = {}
        for login, organisation in mapping.items():
            if folded.setdefault(login.casefold(), organisation) != organisation:
                raise ValueError(f'{login}: two spellings of the login give two organisations in {year}')
        mappings[year] = folded
    found = []
    for key in sorted(k for k in people.keys if not k.startswith('name:')):
        overrides = [(index, row) for index, row in enumerate(old.overrides)
                     if row['github_username'].strip().casefold() == key]
        years = []
        for year in range(AFFILIATION_FIRST_YEAR, until + 1):
            organisation = mappings[year].get(key)
            if not organisation or organisation == UNMAPPED:
                continue
            applying = [index for index, row in overrides if _applies(row, year)]
            years.append((year, organisation, applying[-1] if applying else None))
        found.extend(_ranges(people.ids[key], key, years, old, organisations, until))
    return sorted(found, key=lambda row: (row['person'], row['from']))


def _applies(override, year):
    """Whether an override covers the year, as load_organisation_mapping applies it."""
    from_year, to_year = override['from_year'], override['to_year']
    return bool(from_year and from_year <= year and (not to_year or year <= to_year))


def _ranges(person, key, years, old, organisations, until):
    runs = []
    for year, organisation, origin in years:
        if runs and runs[-1]['organisation'] == organisation and runs[-1]['origin'] == origin \
                and runs[-1]['to'] == year - 1:
            runs[-1]['to'] = year
        else:
            runs.append({'organisation': organisation, 'origin': origin, 'from': year, 'to': year})
    rows = []
    for run in runs:
        org_id = organisations.id_for(run['organisation'])
        if org_id is None:
            raise ValueError(f'{key}: "{run["organisation"]}" is no organisation in organisations.csv')
        row = {'person': person, 'organisation': org_id, 'from': run['from'],
               'to': '' if run['to'] == until else run['to'], 'checked': '', 'notes': ''}
        if run['origin'] is None:
            record = old.sources.get(key)
            if record is None:
                raise ValueError(f'{key}: the current entry has no row in organisation_mapping_sources.csv')
            row['source'] = record['source'].strip()
            row['checked'] = record['checked'].strip()
            if row['checked'] and run['from'] < int(row['checked'][:4]):
                row['notes'] = NOT_VERIFIED.format(year=row['checked'][:4])
        else:
            override = old.overrides[run['origin']]
            row['source'] = override['source']
            if override['to_year'] is not None and run['to'] == until:
                row['to'] = until
        rows.append(row)
    return rows


def old_proposals(old, people, organisations):
    """The rows of the old proposals file, as affiliation proposals."""
    found = []
    logins = old.proposal_logins
    for row in old.proposals:
        contributor = row['contributor'].strip()
        if contributor in logins:
            key = people.login_key(contributor)
        else:
            key = people.key(contributor)
        # A proposal may introduce an organisation; its row records the proposal's evidence as the reason
        org_id = organisations.id_or_add(row['organisation'].strip(),
                                         f'named in organisation_mapping_proposals.csv: {row["evidence"].strip()}')
        found.append({'person': people.ids[key], 'organisation': org_id, 'from': int(row['from_year']),
                      'to': int(row['to_year']) if row['to_year'].strip() else '',
                      'evidence': row['evidence'].strip(), 'kind': 'carried over'})
    return found


def rewrite_collected(root, people, report):
    """Rename the commit authors without a login to person:<id> in the collected contributors and changelogs.

    Only the renamed lines are written anew; every other byte of the files stays.
    """
    renames = {}
    for row in people.old.commit_authors:
        name = row['name'].strip()
        if name and not row['github_username'].strip():
            renames[name] = PERSON_PREFIX + people.ids[people.key(name)]
    files = sorted((root / paths.CONTRIBUTORS_DIR).glob('*.csv')) + sorted((root / paths.CHANGELOGS_DIR).glob('*.csv'))
    for path in files:
        if path.name.endswith('_checkpoint.csv'):
            continue
        with open(path, newline='', encoding='utf-8') as f:
            text = f.read()
        # Lines end at \n only, so that \r\n and characters such as U+2028 inside a cell stay as they are
        lines = [line for line in re.split(r'(?<=\n)', text) if line]
        parsed = list(csv.reader(io.StringIO(text, newline='')))
        if len(parsed) != len(lines):
            raise ValueError(f'{path}: a row spans several lines; the rename keeps one row per line')
        column = parsed[0].index('username')
        changed = Counter()
        for number, cells in enumerate(parsed[1:], start=1):
            if cells and cells[column] in renames:
                changed[cells[column]] += 1
                cells[column] = renames[cells[column]]
                ending = lines[number][len(lines[number].rstrip('\r\n')):]
                out = io.StringIO()
                csv.writer(out, lineterminator=ending).writerow(cells)
                lines[number] = out.getvalue()
        if changed:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                f.write(''.join(lines))
            relative = path.relative_to(root).as_posix()
            report.renamed_usernames.extend((relative, name, renames[name], count)
                                            for name, count in sorted(changed.items()))


def remove_old_files(root):
    """Delete the old mapping files; organisations.csv is rewritten in place."""
    for path in OLD_FILES:
        (root / path).unlink(missing_ok=True)


def write_report(report):
    """The report as Markdown: the counts first, then every list."""
    lists = [
        ('Dropped aliases', 'alias, target, reason', report.dropped_aliases),
        ('Added organisations', 'organisation, reason', report.added_organisations),
        ('Renamed usernames', 'file, old, new, rows', report.renamed_usernames),
        ('Unaligned organisation cells', 'file, line, persons, organisations', report.unaligned),
        ('Dropped groups', 'file, line, entry', report.dropped_groups),
        ('Not carried into the new files', 'file, line, what', report.unrepresentable),
        ('ID collisions', 'base id, resulting ids, logins', report.id_collisions),
        ('Dropped handles', 'file, line, names, handles', report.dropped_handles),
        ('Cut sources', 'file, line, cut text', report.cut_sources),
    ]
    out = ['# Migration to the registers (#139)', '', '| What | Count |', '|---|---|']
    for name in ('people', 'identities', 'organisations', 'affiliations', 'proposals'):
        out.append(f'| {name} | {getattr(report, name)} |')
    for kind, count in sorted(report.proposal_kinds.items()):
        out.append(f'| proposals: {kind} | {count} |')
    for title, _, items in lists:
        out.append(f'| {title.lower()} | {len(items)} |')
    for title, columns, items in lists:
        out += ['', f'## {title}', '', f'{len(items)} rows: {columns}.', '']
        out += [f'- {" | ".join(str(part) for part in item)}' for item in items]
    return '\n'.join(out) + '\n'


def migrate(root, until, profile_names):
    """Migrate the curated files under root to the registers and return the report."""
    root = Path(root)
    report = Report()
    old = Old.read(root)
    organisations = Organisations(old, report)
    people = People(old, organisations, Path(profile_names))
    report.id_collisions.extend(people.collisions)
    report.dropped_handles.extend(old_community.dropped_handles(old.rows))
    affiliations = build_affiliations(root, old, people, organisations, until)
    covered = {}
    for row in affiliations:
        for year in range(row['from'], (row['to'] or until) + 1):
            covered[(row['person'], year)] = row['organisation']
    rewriter = old_community.Rewriter(people, organisations, lambda person, year: covered.get((person, year)),
                                      report)
    files = rewriter.rewrite(old.rows)
    proposals = old_proposals(old, people, organisations) + rewriter.proposals
    report.proposal_kinds.update(row.pop('kind') for row in proposals)
    proposals.sort(key=lambda row: (row['person'], row['from'], row['organisation'], row['evidence']))
    identities = people.identities()
    _write(root / paths.PEOPLE, HEADERS[paths.PEOPLE], people.register())
    _write(root / paths.IDENTITIES, HEADERS[paths.IDENTITIES], identities)
    _write(root / paths.AFFILIATIONS, HEADERS[paths.AFFILIATIONS], affiliations)
    _write(root / paths.ORGANISATIONS, HEADERS[paths.ORGANISATIONS], organisations.register())
    _write(root / paths.AFFILIATION_PROPOSALS, HEADERS[paths.AFFILIATION_PROPOSALS], proposals)
    for file, (header, rows) in files.items():
        _write(root / file, header, rows)
    rewrite_collected(root, people, report)
    remove_old_files(root)
    report.people, report.identities = len(people.rows), len(identities)
    report.organisations, report.affiliations, report.proposals = len(organisations.rows), len(affiliations), \
        len(proposals)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Migrate the curated files to the people register')
    commands = parser.add_subparsers(dest='command', required=True)
    fetch = commands.add_parser('fetch-names', help='Fetch the GitHub profile names the migration needs '
                                                    '(needs GITHUB_TOKEN)')
    fetch.add_argument('--out', required=True, help='The CSV file to write: login, name, fetched')
    run = commands.add_parser('run', help='Migrate the curated files to the registers and print a report')
    run.add_argument('--root', default='.', help='The repository to migrate (default: the current directory)')
    run.add_argument('--until', type=int, required=True, help='The last year of the affiliations, e.g. 2026')
    run.add_argument('--profile-names', required=True, help='The file fetch-names wrote: login, name, fetched')
    run.add_argument('--report', help='Also write the report to this Markdown file')
    args = parser.parse_args(argv)
    if args.command == 'fetch-names':
        fetch_names(args.out)
    elif args.command == 'run':
        text = write_report(migrate(Path(args.root), args.until, args.profile_names))
        if args.report:
            Path(args.report).write_text(text, encoding='utf-8')
        print(text, end='')


if __name__ == '__main__':
    main()
