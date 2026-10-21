"""Checks that a Table Schema cannot express, as Frictionless custom checks."""

import re
from collections import defaultdict

import attrs
from frictionless import Check, errors

from scripts.lib.model.names import fold

OPEN_END = 9999


class SetKeysError(errors.CellError):
    type = 'set-keys'
    title = 'Set Keys'
    description = 'An element of a set cell is empty, repeated or not a key of the referenced register.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class AffiliationOverlapError(errors.RowError):
    type = 'affiliation-overlap'
    title = 'Affiliation Overlap'
    description = 'Two affiliations of one person cover the same years.'
    template = 'The row at position {rowNumber} has an error: {note}'


class AffiliationPeriodError(errors.RowError):
    type = 'affiliation-period'
    title = 'Affiliation Period'
    description = 'An affiliation ends before it starts, or is open-ended without the date its record was read.'
    template = 'The row at position {rowNumber} has an error: {note}'


class ReachingBackPastRecordError(errors.RowError):
    type = 'reaching-back-past-record'
    title = 'Reaching Back Past Record'
    description = ('A guessed range of an organisation lies before a record of another organisation, although the '
                   'organisation returns later: a current entry extended back through an older employer.')
    template = 'The row at position {rowNumber} has an error: {note}'


class LoginOwnerError(errors.CellError):
    type = 'login-owner'
    title = 'Login Owner'
    description = 'A second login of one person is the GitHub login of another person.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class NameFoldError(errors.CellError):
    type = 'name-fold'
    title = 'Name Fold'
    description = 'A name or alias differs from another one only in case, accents or punctuation.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class NotSortedError(errors.RowError):
    type = 'not-sorted'
    title = 'Not Sorted'
    description = 'The rows of the register are not in order.'
    template = 'The row at position {rowNumber} has an error: {note}'


class UniqueCasefoldError(errors.CellError):
    type = 'unique-casefold'
    title = 'Unique Casefold'
    description = 'Two rows have values that differ only in case.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class SourceLinkError(errors.CellError):
    type = 'source-link'
    title = 'Source Link'
    description = 'The source of an identity contains no web address.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


@attrs.define(kw_only=True, repr=False)
class SetKeys(Check):
    """Every element of a semicolon separated cell is a key of the referenced register, once."""

    type = 'set-keys'
    Errors = [SetKeysError]

    field: str
    keys: set = attrs.field(factory=set)

    def validate_row(self, row):
        value = row[self.field]
        if not value:
            return
        seen = set()
        for element in (part.strip() for part in value.split(';')):
            if not element:
                note = 'the set has an empty element'
            elif element in seen:
                note = f'"{element}" is listed twice'
            elif element not in self.keys:
                note = f'"{element}" is not in the register'
            else:
                seen.add(element)
                continue
            yield SetKeysError.from_row(row, note=note, field_name=self.field)


@attrs.define(kw_only=True, repr=False)
class AffiliationOverlap(Check):
    """The year ranges of one person's affiliations do not overlap."""

    type = 'affiliation-overlap'
    Errors = [AffiliationOverlapError]

    _rows: dict = attrs.field(factory=lambda: defaultdict(list), init=False)

    def validate_row(self, row):
        if row['person'] and row['from'] is not None:
            self._rows[row['person']].append((row['from'], row['to'] or OPEN_END, row))
        yield from []

    def validate_end(self):
        for rows in self._rows.values():
            for index, (start_a, end_a, row_a) in enumerate(rows):
                for start_b, end_b, row_b in rows[index + 1:]:
                    if start_a <= end_b and start_b <= end_a:
                        note = f'rows {row_a.row_number} and {row_b.row_number} overlap'
                        yield AffiliationOverlapError.from_row(row_b, note=note)


@attrs.define(kw_only=True, repr=False)
class AffiliationPeriod(Check):
    """`from` is not after `to`, and an affiliation without `to` says when its record was read."""

    type = 'affiliation-period'
    Errors = [AffiliationPeriodError]

    def validate_row(self, row):
        start, end = row['from'], row['to']
        if start is not None and end is not None and start > end:
            yield AffiliationPeriodError.from_row(row, note=f'from {start} is after to {end}')
        if end is None and not row['checked']:
            yield AffiliationPeriodError.from_row(row, note='an affiliation up to the present needs checked')


GUESS_NOTE = 'not verified'


@attrs.define(kw_only=True, repr=False)
class ReachingBackPastRecord(Check):
    """A guessed range (its notes say "not verified") does not lie before a record of another organisation when its
    own organisation returns later: a range reaching back from the current entry stops at the first record."""

    type = 'reaching-back-past-record'
    Errors = [ReachingBackPastRecordError]

    _rows: dict = attrs.field(factory=lambda: defaultdict(list), init=False)

    def validate_row(self, row):
        if row['person'] and row['from'] is not None:
            self._rows[row['person']].append(row)
        yield from []

    def validate_end(self):
        for rows in self._rows.values():
            rows = sorted(rows, key=lambda r: r['from'])
            for index, row in enumerate(rows):
                if row['to'] is None or GUESS_NOTE not in (row['notes'] or ''):
                    continue
                later = rows[index + 1:]
                records = [r for r in later
                           if r['organisation'] != row['organisation'] and GUESS_NOTE not in (r['notes'] or '')]
                if not records:
                    continue
                record = records[0]
                if any(r['organisation'] == row['organisation'] and r['from'] > record['from'] for r in later):
                    note = (f"the guessed years {row['from']}-{row['to']} of {row['organisation']} lie before the "
                            f"record of {record['organisation']} in row {record.row_number}, and "
                            f"{row['organisation']} returns later")
                    yield ReachingBackPastRecordError.from_row(row, note=note)


@attrs.define(kw_only=True, repr=False)
class LoginOwner(Check):
    """A `login` identity is not the `github` of another person in the people register, ignoring case."""

    type = 'login-owner'
    Errors = [LoginOwnerError]

    github: dict = attrs.field(factory=dict)
    """The person id of every `people.github`, by the login in lower case."""

    def validate_row(self, row):
        if row['kind'] != 'login' or not row['value']:
            return
        owner = self.github.get(row['value'].casefold())
        if owner is not None and owner != row['person']:
            note = f'the login "{row["value"]}" of {row["person"]} is the github of {owner} in people.csv'
            yield LoginOwnerError.from_row(row, note=note, field_name='value')


@attrs.define(kw_only=True, repr=False)
class NameFold(Check):
    """No name or alias folds to the same text as the name or alias of another row."""

    type = 'name-fold'
    Errors = [NameFoldError]

    existing: dict = attrs.field(factory=dict)
    """Fold of every name and alias seen so far, mapped to the id of its row."""

    def validate_row(self, row):
        mine = {}
        for field, text in [('name', row['name'])] + [('aliases', a) for a in (row['aliases'] or '').split(';')]:
            key = fold(text.strip()) if text else ''
            if key:
                mine.setdefault(key, (field, text.strip()))
        for key, (field, text) in mine.items():
            other = self.existing.get(key)
            if other is not None and other != row['id']:
                note = f'"{text}" is the same as a name or alias of "{other}" once case, accents and punctuation go'
                yield NameFoldError.from_row(row, note=note, field_name=field)
        for key in mine:
            self.existing.setdefault(key, row['id'])


def _sort_value(value, casefold):
    if value is None:
        return (0, '')
    return (1, value.casefold() if casefold and isinstance(value, str) else value)


@attrs.define(kw_only=True, repr=False)
class Sorted(Check):
    """The rows are ordered by the given fields."""

    type = 'not-sorted'
    Errors = [NotSortedError]

    fields: list
    casefold: bool = False
    _previous: tuple = attrs.field(default=None, init=False)

    def validate_row(self, row):
        key = tuple(_sort_value(row[name], self.casefold) for name in self.fields)
        if self._previous is not None and key < self._previous[0]:
            note = f'row {row.row_number} comes after row {self._previous[1]} but sorts before it'
            yield NotSortedError.from_row(row, note=note)
        self._previous = (key, row.row_number)


@attrs.define(kw_only=True, repr=False)
class UniqueCasefold(Check):
    """No two rows have values in the field that differ only in case; empty cells are skipped.

    With `scope`, the value is unique among the rows with the same value in that field, e.g. an identity
    value within its kind.
    """

    type = 'unique-casefold'
    Errors = [UniqueCasefoldError]

    field: str
    scope: str = None
    _seen: dict = attrs.field(factory=dict, init=False)

    def validate_row(self, row):
        value = row[self.field]
        if not value:
            return
        key = (row[self.scope] if self.scope else None, value.casefold())
        first = self._seen.setdefault(key, row.row_number)
        if first != row.row_number:
            within = f' of {self.scope} {row[self.scope]}' if self.scope else ''
            note = f'"{value}" is the same as the value{within} in row {first} once case goes'
            yield UniqueCasefoldError.from_row(row, note=note, field_name=self.field)


@attrs.define(kw_only=True, repr=False)
class LinkUnlessEmail(Check):
    """The source of an identity contains a web address, unless the identity is an email address."""

    type = 'source-link'
    Errors = [SourceLinkError]

    def validate_row(self, row):
        if row['kind'] != 'email' and not re.search(r'https?://', row['source'] or ''):
            yield SourceLinkError.from_row(row, note='the source needs a link', field_name='source')


def _keys_of(package, resource_name):
    """The values of the primary key column of a resource in the package."""
    resource = package.get_resource(resource_name)
    key = resource.schema.primary_key[0]
    return {row[key] for row in resource.read_rows() if row[key]}


def _github_owners(package):
    """{login in lower case: person id} of the `github` column of people.csv; {} without the register."""
    if not package.has_resource('people'):
        return {}
    return {row['github'].casefold(): row['id'] for row in package.get_resource('people').read_rows()
            if row['github'] and row['id']}


def checks_for(resource_name, package):
    """The custom checks of a resource in the package."""
    checks = {
        'people': lambda: [Sorted(fields=['id'], casefold=False), UniqueCasefold(field='github')],
        'rejected-proposals': lambda: [Sorted(fields=['person', 'from'], casefold=False)],
        'organisations': lambda: [Sorted(fields=['id'], casefold=True), NameFold(), UniqueCasefold(field='github')],
        'affiliations': lambda: [AffiliationOverlap(), AffiliationPeriod(), ReachingBackPastRecord(),
                                 Sorted(fields=['person', 'from'], casefold=False)],
        'identities': lambda: [LinkUnlessEmail(), Sorted(fields=['person', 'kind', 'value'], casefold=False),
                               UniqueCasefold(field='value', scope='kind'),
                               LoginOwner(github=_github_owners(package))],
    }
    result = checks.get(resource_name, lambda: [])()
    for field in package.get_resource(resource_name).schema.fields:
        referenced = field.to_descriptor().get('x-set')
        if referenced:
            result.append(SetKeys(field=field.name, keys=_keys_of(package, referenced)))
    return result
