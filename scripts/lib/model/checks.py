"""Checks that a Table Schema cannot express, as Frictionless custom checks."""

import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import attrs
from frictionless import Check, errors

from scripts.lib.model.attribution import ASSUMED, COUNTING
from scripts.lib.model.names import fold
from scripts.lib.model.registers import UNIQUE_IDENTITY_KINDS
from scripts.lib.model.schema import CellTypeError
from scripts.lib.model.sources import source_id, split_archive_url


class SetKeysError(errors.CellError):
    type = 'set-keys'
    title = 'Set Keys'
    description = 'An element of a set cell is empty, repeated or not a key of the referenced register.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


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


class GithubLoginError(errors.CellError):
    type = 'github-login'
    title = 'GitHub Login'
    description = 'A person has two `github` identities, or a `github-alias` is the `github` identity of a person.'
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


class UniqueRowError(errors.RowError):
    type = 'unique-row'
    title = 'Unique Row'
    description = 'Two rows have the same values in the fields that make a row unique.'
    template = 'The row at position {rowNumber} has an error: {note}'


class IdentitySourceError(errors.CellError):
    type = 'identity-source'
    title = 'Identity Source'
    description = 'An identity cites no source, and is not an early commit address whose notes say what it rests on.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class SnippetError(errors.CellError):
    type = 'snippet'
    title = 'Snippet'
    description = 'A snippet has no source, or is not found in the excerpt of its source.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class UncitedAffiliationError(errors.RowError):
    type = 'uncited-affiliation'
    title = 'Uncited Affiliation'
    description = 'An affiliation that is not a proposal has no citation.'
    template = 'The row at position {rowNumber} has an error: {note}'


class ConflictCheckSkippedError(errors.TableError):
    type = 'conflict-check-skipped'
    title = 'Conflict Check Skipped'
    description = 'The registers cannot be read, so the open cases of the attribution could not be looked for.'
    template = 'General table error: {note}'


class OpenCaseWarning(errors.TableError):
    type = 'open-case'
    title = 'Open Case'
    description = ('No attribution rule decides which organisation a person counts for in a year: the year counts '
                   'as Unmapped until a decision settles it. A warning, not an error.')
    template = 'Open case: {note}'


class DecisionError(errors.TableError):
    type = 'decision-supersedes'
    title = 'Decision Supersedes'
    description = 'Of two decisions for one person and year, the later does not name the earlier in `supersedes`.'
    template = 'General table error: {note}'


class SourceIdError(errors.RowError):
    type = 'source-id'
    title = 'Source Id'
    description = 'The id of a source is not the hash of its address and archive timestamp.'
    template = 'The row at position {rowNumber} has an error: {note}'


class SourceExcerptError(errors.RowError):
    type = 'source-excerpt'
    title = 'Source Excerpt'
    description = 'A source has no excerpt file with a passage, or an excerpt file has no source.'
    template = 'The row at position {rowNumber} has an error: {note}'


class SourceExcerptOrphanError(errors.TableError):
    type = 'source-excerpt'
    title = 'Source Excerpt'
    description = 'A source has no excerpt file with a passage, or an excerpt file has no source.'
    template = 'General table error: {note}'


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


@attrs.define(kw_only=True, repr=False)
class ReachingBackPastRecord(Check):
    """An assumed range stops at a record of another organisation that its own organisation returns after.

    An assumed row, open-ended or not, is an error when it covers years before a stated row of another
    organisation and its own organisation covers years after that row: a current entry extended back through an
    older employer. Overlapping the stated row doesn't help, because the stated row wins only in its own years.
    """

    type = 'reaching-back-past-record'
    Errors = [ReachingBackPastRecordError]

    _rows: dict = attrs.field(factory=lambda: defaultdict(list), init=False)

    def validate_row(self, row):
        if row['person'] and row['from'] is not None and row['status'] in COUNTING:
            self._rows[row['person']].append(row)
        yield from []

    def validate_end(self):
        for rows in self._rows.values():
            rows = sorted(rows, key=lambda r: r['from'])
            for row in rows:
                if row['status'] != ASSUMED:
                    continue
                own = [r for r in rows if r['organisation'] == row['organisation']]
                records = [r for r in rows if r['organisation'] != row['organisation'] and r['status'] != ASSUMED
                           and r['to'] is not None and row['from'] < r['from']
                           and any(o['to'] is None or o['to'] > r['to'] for o in own)]
                if records:
                    record = records[0]
                    note = (f"the assumed years {row['from']}-{'' if row['to'] is None else row['to']} of "
                            f"{row['organisation']} lie before the record of {record['organisation']} in row "
                            f"{record.row_number}, and {row['organisation']} returns later")
                    yield ReachingBackPastRecordError.from_row(row, note=note)


@attrs.define(kw_only=True, repr=False)
class GithubLogins(Check):
    """A person has at most one `github` identity, and a `github-alias` is nobody's `github`, ignoring case."""

    type = 'github-login'
    Errors = [GithubLoginError]

    _github: dict = attrs.field(factory=dict, init=False)  # person -> row number of its github identity
    _owners: dict = attrs.field(factory=dict, init=False)  # login in lower case -> person
    _aliases: list = attrs.field(factory=list, init=False)

    def validate_row(self, row):
        if row['kind'] == 'github' and row['value']:
            self._owners.setdefault(row['value'].casefold(), row['person'])
            first = self._github.setdefault(row['person'], row.row_number)
            if first != row.row_number:
                note = (f'{row["person"]} has a github identity in row {first} already; a further account is a '
                        f'github-alias')
                yield GithubLoginError.from_row(row, note=note, field_name='value')
        elif row['kind'] == 'github-alias' and row['value']:
            self._aliases.append(row)

    def validate_end(self):
        for row in self._aliases:
            owner = self._owners.get(row['value'].casefold())
            if owner is not None:
                note = f'the github-alias "{row["value"]}" of {row["person"]} is the github identity of {owner}'
                yield GithubLoginError.from_row(row, note=note, field_name='value')


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
    value within its kind; with `only`, among the rows whose scope is one of these values.
    """

    type = 'unique-casefold'
    Errors = [UniqueCasefoldError]

    field: str
    scope: str = None
    only: tuple = attrs.field(default=None)
    _seen: dict = attrs.field(factory=dict, init=False)

    @only.validator
    def _only_needs_scope(self, attribute, value):
        if value is not None and not self.scope:
            raise ValueError('`only` names values of the `scope` field: give a scope')

    def validate_row(self, row):
        value = row[self.field]
        if not value or (self.only is not None and row[self.scope] not in self.only):
            return
        key = (row[self.scope] if self.scope else None, value.casefold())
        first = self._seen.setdefault(key, row.row_number)
        if first != row.row_number:
            within = f' of {self.scope} {row[self.scope]}' if self.scope else ''
            note = f'"{value}" is the same as the value{within} in row {first} once case goes'
            yield UniqueCasefoldError.from_row(row, note=note, field_name=self.field)


@attrs.define(kw_only=True, repr=False)
class UniqueRow(Check):
    """No two rows have the same values in the fields; an empty cell counts as a value."""

    type = 'unique-row'
    Errors = [UniqueRowError]

    fields: list
    only: dict = attrs.field(factory=dict)
    """{field: value}: only the rows with these values are compared, for example the sprints of the events."""
    _seen: dict = attrs.field(factory=dict, init=False)

    def validate_row(self, row):
        if any(row[name] != value for name, value in self.only.items()):
            return
        key = tuple(row[name] for name in self.fields)
        first = self._seen.setdefault(key, row.row_number)
        if first != row.row_number:
            names = ', '.join(self.fields)
            yield UniqueRowError.from_row(row, note=f'row {first} has the same {names}')


@attrs.define(kw_only=True, repr=False)
class SourceUnlessEmail(Check):
    """An identity cites a source, unless it is an early commit address whose notes say what it rests on."""

    type = 'identity-source'
    Errors = [IdentitySourceError]

    def validate_row(self, row):
        if row['source']:
            return
        if row['kind'] != 'email':
            yield IdentitySourceError.from_row(row, note='the identity needs a source', field_name='source')
        elif not row['notes']:
            yield IdentitySourceError.from_row(row, note='an address without a source needs notes that say what '
                                                         'it rests on', field_name='source')


@attrs.define(kw_only=True, repr=False)
class SnippetInExcerpt(Check):
    """A snippet appears in the excerpt of its source, compared as the capture compares a quote (`find_quote`)."""

    type = 'snippet'
    Errors = [SnippetError]

    folder: Path
    """The folder of the excerpt files."""

    def validate_row(self, row):
        # Imported here: scripts.lib.capture imports the model
        from scripts.lib.capture.passages import find_quote

        if not row['snippet']:
            return
        if not row['source']:
            yield SnippetError.from_row(row, note='the snippet has no source', field_name='snippet')
            return
        path = self.folder / f'{row["source"]}.md'
        text = path.read_text(encoding='utf-8') if path.is_file() else ''
        if find_quote(text, row['snippet']) is None:
            note = f'the snippet is not in the excerpt of {row["source"]}'
            yield SnippetError.from_row(row, note=note, field_name='snippet')


@attrs.define(kw_only=True, repr=False)
class Cited(Check):
    """Every affiliation but a proposal has at least one citation."""

    type = 'uncited-affiliation'
    Errors = [UncitedAffiliationError]

    cited: set = attrs.field(factory=set)
    """The affiliation ids that citations.csv names."""

    def validate_row(self, row):
        if row['id'] and row['status'] != 'proposed' and row['id'] not in self.cited:
            yield UncitedAffiliationError.from_row(row, note=f'the affiliation {row["id"]} has no citation')


@attrs.define(kw_only=True, repr=False)
class UnresolvedConflict(Check):
    """A person-year that no attribution rule decides is an open case, a warning: Unmapped until a decision settles it.

    That the registers cannot be read is an error."""

    type = 'open-case'
    Errors = [ConflictCheckSkippedError, OpenCaseWarning]

    attribution: object
    """A function that returns the `Attribution` of the registers, or the reason why they cannot be read."""
    until: int

    def validate_end(self):
        attribution = self.attribution()
        if isinstance(attribution, str):
            yield ConflictCheckSkippedError(note=f'the conflict check was skipped: {attribution}')
            return
        for person, year, organisations in attribution.conflicts(until=self.until):
            note = (f'{person}, {year}: no attribution rule decides between {", ".join(organisations)}; '
                    f'it counts as Unmapped until a decision settles it')
            yield OpenCaseWarning(note=note)


@attrs.define(kw_only=True, repr=False)
class DecisionSupersedes(Check):
    """Of two decisions for one person and year, the later names the earlier in `supersedes`."""

    type = 'decision-supersedes'
    Errors = [DecisionError]

    attribution: object
    """A function that returns the `Attribution` of the registers, or the reason why they cannot be read."""
    until: int

    def validate_end(self):
        attribution = self.attribution()
        if isinstance(attribution, str):
            yield DecisionError(note=f'the decision check was skipped: {attribution}')
            return
        for message in attribution.decision_errors(until=self.until):
            yield DecisionError(note=message)


@attrs.define(kw_only=True, repr=False)
class SourceIdMatchesUrl(Check):
    """The id is the hash of the address and, for an archived copy, its timestamp."""

    type = 'source-id'
    Errors = [SourceIdError]

    def validate_row(self, row):
        archive = split_archive_url(row['archive_url']) if row['archive_url'] else None
        expected = source_id(row['url'], archive[1] if archive else None)
        if row['id'] != expected:
            yield SourceIdError.from_row(row, note=f'the id of {row["url"]} is {expected}, not {row["id"]}')


@attrs.define(kw_only=True, repr=False)
class SourceExcerptFiles(Check):
    """Every source has an excerpt file with a passage, and every excerpt file has a source."""

    type = 'source-excerpt'
    Errors = [SourceExcerptError, SourceExcerptOrphanError]

    folder: Path
    """The folder of the excerpt files."""
    stems: set = attrs.field(factory=set)
    """The names, without `.md`, of the excerpt files on disk."""
    _ids: set = attrs.field(factory=set, init=False)

    def validate_row(self, row):
        self._ids.add(row['id'])
        path = self.folder / f'{row["id"]}.md'
        if row['id'] not in self.stems:
            yield SourceExcerptError.from_row(row, note=f'the excerpt file {path.name} is missing')
        elif not path.read_text(encoding='utf-8').strip():
            yield SourceExcerptError.from_row(row, note=f'the excerpt file {path.name} has no passage')

    def validate_end(self):
        for stem in sorted(self.stems - self._ids):
            yield SourceExcerptOrphanError(note=f'the excerpt file {stem}.md has no row in sources.csv')


class OrganiserError(errors.RowError):
    type = 'organiser'
    title = 'Organiser'
    description = 'An organiser row names both a person and an organisation, or neither.'
    template = 'The row at position {rowNumber} has an error: {note}'


class EventSourceError(errors.CellError):
    type = 'event-source'
    title = 'Event Source'
    description = 'An event that is not only the holder of the rows pointing to it cites no source.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


@attrs.define(kw_only=True, repr=False)
class PersonOrOrganisation(Check):
    """An organiser row names exactly one of `person` and `organisation`."""

    type = 'organiser'
    Errors = [OrganiserError]

    def validate_row(self, row):
        if row['person'] and row['organisation']:
            yield OrganiserError.from_row(row, note='a row names one organiser: a person or an organisation, not both')
        elif not row['person'] and not row['organisation']:
            yield OrganiserError.from_row(row, note='the row names no organiser: give a person or an organisation')


class EventDateError(errors.CellError):
    type = 'event-date'
    title = 'Event Date'
    description = 'A World Plone Day event has no full day as its start.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


class EventKindError(errors.CellError):
    type = 'event-kind'
    title = 'Event Kind'
    description = 'A row points to an event of a kind that rows of its file may not point to.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


# The events the migration made to hold the rows pointing to them, which cite their sources: the Plone Conference of
# a year and the online World Plone Day edition of a year. They have no source and no date of their own.
HOLDER_EVENT_IDS = ('plone-conference-{year}', 'wpd-{year}-online')


def is_holder_event(row):
    """Whether an events row is one the migration made to hold the rows pointing to it, by its id."""
    return row['id'] in {pattern.format(year=row['year']) for pattern in HOLDER_EVENT_IDS}


@attrs.define(kw_only=True, repr=False)
class EventSources(Check):
    """An event cites a source, unless it is a `plone-conference-<year>` or `wpd-<year>-online` the migration made.

    These hold the talks, trainings and organisers that point to them, and those cite their sources.
    """

    type = 'event-source'
    Errors = [EventSourceError]

    def validate_row(self, row):
        if row['sources'] or is_holder_event(row):
            return
        yield EventSourceError.from_row(row, note=f'the {row["kind"]} event needs a source', field_name='sources')


@attrs.define(kw_only=True, repr=False)
class WorldPloneDayDate(Check):
    """A World Plone Day event starts on a full day, `YYYY-MM-DD`, unless it is a `wpd-<year>-online` edition."""

    type = 'event-date'
    Errors = [EventDateError]

    def validate_row(self, row):
        if row['kind'] != 'wpd' or is_holder_event(row):
            return
        start = row['start'] or ''
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start):
            yield EventDateError.from_row(row, note=f'the World Plone Day event {row["id"]} needs its day as start',
                                          field_name='start')


# The kinds of events that the rows of a file may point to
EVENT_KINDS_OF = {
    'talks': ('conference', 'symposium', 'wpd'),
    'trainings': ('conference', 'symposium'),
}


@attrs.define(kw_only=True, repr=False)
class PointsToEventKind(Check):
    """A row points to an event of a kind that its file allows, see EVENT_KINDS_OF."""

    type = 'event-kind'
    Errors = [EventKindError]

    allowed: tuple
    kinds: dict = attrs.field(factory=dict)
    """{event id: kind} of the events file; an unknown event is the foreign key's error."""

    def validate_row(self, row):
        kind = self.kinds.get(row['event'])
        if kind is not None and kind not in self.allowed:
            note = f'the event {row["event"]} is a {kind}; this file points to {", ".join(self.allowed)} events'
            yield EventKindError.from_row(row, note=note, field_name='event')


class TalkTypeError(errors.CellError):
    type = 'talk-type'
    title = 'Talk Type'
    description = 'A talk has a type that talks at events of its kind do not have.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


# The types of the talks at the events of a kind: the programme of a conference or symposium calls a talk a Keynote,
# Talk or Panel; a World Plone Day video is what it is, and only its type Talk is a talk that counts
TALK_TYPES_OF = {
    'conference': ('Keynote', 'Talk', 'Panel'),
    'symposium': ('Keynote', 'Talk', 'Panel'),
    'wpd': ('Talk', 'Teaser', 'Announcement', 'Welcome', 'Recap', 'Duplicate', 'Opening', 'Full stream', 'Newsroom'),
}


def or_list(values):
    """The values as text, the last one joined with `or`: `a, b or c`."""
    return ', '.join(values[:-1]) + f' or {values[-1]}' if len(values) > 1 else values[0]


@attrs.define(kw_only=True, repr=False)
class TalkTypeOfEventKind(Check):
    """A talk has a type of the talks at events of its kind, see TALK_TYPES_OF."""

    type = 'talk-type'
    Errors = [TalkTypeError]

    kinds: dict = attrs.field(factory=dict)
    """{event id: kind} of the events file; an unknown event is the foreign key's error."""

    def validate_row(self, row):
        kind = self.kinds.get(row['event'])
        allowed = TALK_TYPES_OF.get(kind)
        if allowed is not None and row['type'] and row['type'] not in allowed:
            note = f'a talk at the {kind} event {row["event"]} is a {or_list(allowed)}, not a {row["type"]}'
            yield TalkTypeError.from_row(row, note=note, field_name='type')


class CitedAsError(errors.CellError):
    type = 'cited-as'
    title = 'Cited As'
    description = 'A row that cites sources, or says how it cites them, gives no web address in `cited_as`.'
    template = 'The cell {cell} in row at position {rowNumber} and field {fieldName} has an error: {note}'


WEB_ADDRESS = re.compile(r'https?://')


@attrs.define(kw_only=True, repr=False)
class CitedAsWebAddress(Check):
    """`cited_as` contains a web address, unless the row leaves both `sources` and `cited_as` empty.

    Only an event the migration made to hold the rows pointing to it cites nothing, see EventSources.
    """

    type = 'cited-as'
    Errors = [CitedAsError]

    def validate_row(self, row):
        if (row['sources'] or row['cited_as']) and not WEB_ADDRESS.search(row['cited_as'] or ''):
            yield CitedAsError.from_row(row, note='cited_as needs the web address of a source', field_name='cited_as')


def _event_kinds(package):
    """{event id: kind} of the events of the package; empty without the events file."""
    if not package.has_resource('events'):
        return {}
    return {row['id']: row['kind'] for row in package.get_resource('events').read_rows() if row['id']}


def _excerpt_stems(package):
    """The file names without `.md` in the excerpt folder next to the curated files of the package."""
    folder = Path(package.basepath) / 'sources' / 'excerpts'
    return {path.stem for path in folder.glob('*.md')} if folder.is_dir() else set()


def _keys_of(package, resource_name):
    """The values of the primary key column of a resource in the package."""
    resource = package.get_resource(resource_name)
    key = resource.schema.primary_key[0]
    return {row[key] for row in resource.read_rows() if row[key]}


def _cited(package):
    """The affiliation ids that the citations name; empty without the register."""
    if not package.has_resource('citations'):
        return set()
    return {row['affiliation'] for row in package.get_resource('citations').read_rows() if row['affiliation']}


def _attribution(package):
    """A function returning the `Attribution` of the registers of the package, read once; when a file of the
    registers is missing or has a cell of the wrong type, the reason, which the attribution checks report as
    skipped (the validation of that file reports the cell itself)."""
    found = []

    def attribution():
        if not found:
            # Imported here: the registers import the attribution engine, whose rules import other libraries
            from scripts.lib.model.registers import load_registry

            try:
                found.append(load_registry(Path(package.basepath) / 'mappings').attribution)
            except FileNotFoundError as error:
                found.append(f'the registers cannot be read: {error.filename or error} is missing')
            except CellTypeError as error:
                found.append(f'the registers cannot be read: {error}')
        return found[0]

    return attribution


def checks_for(resource_name, package, until=None):
    """The custom checks of a resource in the package; `until` is the last year the attribution checks follow
    open-ended affiliations to (the current year by default)."""
    until = until or date.today().year
    excerpts = Path(package.basepath) / 'sources' / 'excerpts'
    checks = {
        'people': lambda: [Sorted(fields=['id'], casefold=False)],
        'organisations': lambda: [Sorted(fields=['id'], casefold=True), NameFold(), UniqueCasefold(field='github')],
        'affiliations': lambda: [AffiliationPeriod(), ReachingBackPastRecord(),
                                 Sorted(fields=['person', 'from', 'organisation'], casefold=False),
                                 UniqueRow(fields=['person', 'organisation', 'from', 'to']),
                                 Cited(cited=_cited(package)),
                                 *[check(attribution=attribution, until=until)
                                   for attribution in [_attribution(package)]
                                   for check in (UnresolvedConflict, DecisionSupersedes)]],
        'citations': lambda: [SnippetInExcerpt(folder=excerpts),
                              Sorted(fields=['affiliation', 'source', 'snippet'], casefold=False),
                              UniqueRow(fields=['affiliation', 'source', 'snippet'])],
        'identities': lambda: [SourceUnlessEmail(), SnippetInExcerpt(folder=excerpts),
                               Sorted(fields=['person', 'kind', 'value'], casefold=False),
                               UniqueCasefold(field='value', scope='kind', only=UNIQUE_IDENTITY_KINDS),
                               GithubLogins()],
        'sources': lambda: [SourceIdMatchesUrl(), Sorted(fields=['id'], casefold=False),
                            SourceExcerptFiles(folder=excerpts, stems=_excerpt_stems(package))],
        'events': lambda: [EventSources(), WorldPloneDayDate(),
                           UniqueRow(fields=['year', 'name'], only={'kind': 'sprint'})],
        'talks': lambda: [PointsToEventKind(allowed=EVENT_KINDS_OF['talks'], kinds=_event_kinds(package)),
                          TalkTypeOfEventKind(kinds=_event_kinds(package))],
        'trainings': lambda: [PointsToEventKind(allowed=EVENT_KINDS_OF['trainings'], kinds=_event_kinds(package)),
                              UniqueRow(fields=['event', 'title'])],
        'organisers': lambda: [PersonOrOrganisation(), UniqueRow(fields=['event', 'person', 'organisation'])],
    }
    result = checks.get(resource_name, lambda: [])()
    names = package.get_resource(resource_name).schema.field_names
    if 'sources' in names and 'cited_as' in names:
        result.append(CitedAsWebAddress())
    for field in package.get_resource(resource_name).schema.fields:
        referenced = field.to_descriptor().get('x-set')
        if referenced:
            result.append(SetKeys(field=field.name, keys=_keys_of(package, referenced)))
    return result
