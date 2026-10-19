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
    """No two rows have values in the field that differ only in case; empty cells are skipped."""

    type = 'unique-casefold'
    Errors = [UniqueCasefoldError]

    field: str
    _seen: dict = attrs.field(factory=dict, init=False)

    def validate_row(self, row):
        value = row[self.field]
        if not value:
            return
        first = self._seen.setdefault(value.casefold(), row.row_number)
        if first != row.row_number:
            note = f'"{value}" is the same as the value in row {first} once case goes'
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


def checks_for(resource_name, package):
    """The custom checks of a resource in the package."""
    checks = {
        'people': lambda: [Sorted(fields=['id'], casefold=False), UniqueCasefold(field='github')],
        'organisations': lambda: [Sorted(fields=['id'], casefold=True), NameFold()],
        'affiliations': lambda: [AffiliationOverlap(), Sorted(fields=['person', 'from'], casefold=False)],
        'identities': lambda: [LinkUnlessEmail(), Sorted(fields=['person', 'kind', 'value'], casefold=False)],
    }
    result = checks.get(resource_name, lambda: [])()
    for field in package.get_resource(resource_name).schema.fields:
        referenced = field.to_descriptor().get('x-set')
        if referenced:
            result.append(SetKeys(field=field.name, keys=_keys_of(package, referenced)))
    return result
