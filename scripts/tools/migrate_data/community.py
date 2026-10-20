"""The community part of the migration (#139): the old community files read, and rewritten to the new shape.

The old files name people by free text and state a per-person organisation; the new files refer to people
and organisations by id. An organisation the old files state for a person is kept only where the
affiliations do not already say it: it then becomes an affiliation proposal, never an affiliation.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.lib import paths
from scripts.tools.migrate_data.legacy_community import ROLE_KINDS, Record, _source
from scripts.tools.migrate_data.legacy_people import normalise

UNMAPPED = 'Unmapped'
TALKS = 'world-plone-day-talks'
# Kinds whose organisation cells state the organisation of each person; the cells disappear
PER_PERSON = ('board-of-directors', 'team-leaders', 'release-managers', 'podcasts', 'plone-conference-trainings',
              TALKS)
# Kinds whose organisation cells name the organising entities; the cells stay, as ids
EVENTS = ('sprints', 'plone-conference', 'world-plone-day-event')
# What the notes call the people of a kind, for a group dropped from its person cell
PEOPLE_WORDS = {'sprints': 'organisers', 'plone-conference': 'organisers', 'plone-conference-trainings': 'trainers',
                TALKS: 'speakers'}
HEADERS = {
    'board-of-directors': ['person', 'role', 'source', 'notes'],
    'team-leaders': ['person', 'team', 'source', 'notes'],
    'release-managers': ['person', 'source', 'notes'],
    'podcasts': ['series', 'person', 'episodes', 'source', 'notes'],
    'plone-conference-trainings': ['title', 'trainers', 'source', 'notes'],
    TALKS: ['title', 'speakers', 'organisations', 'type', 'location', 'source', 'notes'],
    'sprints': ['sprint', 'start', 'end', 'location', 'organisers', 'organisations', 'level', 'source', 'notes'],
    'plone-conference': ['organisation', 'organisers', 'source', 'notes'],
    'world-plone-day-event': ['date', 'location', 'format', 'organisations', 'organisers', 'source', 'notes'],
}
# How a segment of a Source cell starts that is a note on a person's organisation, not the record of the row
NOTES = ('organisation of ', 'organisation from ', 'organisations from ', 'organisation: ')
LINK = re.compile(r'https?://\S+')
# A note that says an organisation cell was copied from the mapping; with a name, it is about that person only
COPIED = re.compile(r'organisations? (?:of (?P<who>[^;:]+?) )?from (?:the organisation mapping|organisations\.csv)')


@dataclass(frozen=True)
class OldRow:
    """One row of an old community file, with where it comes from."""

    kind: str
    year: int
    file: str
    line: int
    row: dict


def split(value):
    """The parts of a cell separated by semicolons."""
    return [part.strip() for part in (value or '').split(';') if part.strip()]


def first_link(text):
    """The first web address in the text, without trailing punctuation; '' when there is none."""
    match = LINK.search(text or '')
    return match.group(0).rstrip(';,') if match else ''


def read_rows(root):
    """Every row of the old community files under root, in file name and line order."""
    found = []
    for path in sorted((Path(root) / paths.COMMUNITY).glob('*.csv')):
        match = re.fullmatch(r'(\d{4})-(.+)', path.stem)
        if not match or match.group(2) not in HEADERS:
            continue
        file = (paths.COMMUNITY / path.name).as_posix()
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                found.append(OldRow(match.group(2), int(match.group(1)), file, reader.line_num, row))
    return found


def people_cells(old):
    """The (name, handle) pairs of the person column of a row; a handle only when the counts agree."""
    if old.kind not in ROLE_KINDS:
        return []
    _, person_column, handle_column, _ = ROLE_KINDS[old.kind]
    names = split(old.row.get(person_column))
    handles = split(old.row.get(handle_column)) if handle_column else []
    if len(handles) != len(names):
        handles = [''] * len(names)
    return list(zip(names, handles))


def dropped_handles(rows):
    """(file, line, names, handles) of the rows whose handles are not one per name, so none is used."""
    found = []
    for old in rows:
        if old.kind not in ROLE_KINDS or not ROLE_KINDS[old.kind][2]:
            continue
        _, person_column, handle_column, _ = ROLE_KINDS[old.kind]
        names, handles = split(old.row.get(person_column)), split(old.row.get(handle_column))
        if handles and len(handles) != len(names):
            found.append((old.file, old.line, ';'.join(names), ';'.join(handles)))
    return found


def records(rows):
    """The rows as the old person index reads them: one Record per name, talks of every type included."""
    found = []
    for old in rows:
        cells = people_cells(old)
        for name, handle in cells:
            found.append(Record(kind=old.kind, year=old.year, person=name, handle=handle, organisation='',
                                label='', detail='', file=old.file, line=old.line, source=_source(old.kind, old.row),
                                shared=len(cells) > 1))
    return found


def cut_source(old):
    """(record of the row, cut remainder) of the Source cell of a row.

    The cell is read as segments separated by `; `. A segment that is a note on a person's organisation
    (it starts with `organisation of `, `organisation from `, `organisations from ` or `organisation: `) or a
    person's record (`<person of the row>: <link>`) is evidence about affiliations, not the record of the
    row: the affiliations or a proposal hold it, and the segment is cut. A segment that is only a bare link
    right after a cut segment belongs to that note (a note listing two links) and is cut with it. Every
    other segment stays, in order. When nothing with a link stays, the record is the first link of the
    cell. A talk without a Source has its video as record.
    """
    source = (old.row.get('Source') or '').strip()
    if old.kind == TALKS and not source and (old.row.get('YouTube ID') or '').strip():
        return f"https://www.youtube.com/watch?v={old.row['YouTube ID'].strip()}", ''
    names = [re.escape(name) for name, _ in people_cells(old)]
    person_record = re.compile(rf'(?:{"|".join(names)}): https?://') if names else None
    kept, cut, previous_cut = [], [], False
    for segment in source.split('; '):
        text = segment.strip()
        is_note = text.startswith(NOTES) or bool(person_record and person_record.match(text))
        is_stray_link = previous_cut and bool(re.fullmatch(r'https?://\S+', text))
        if is_note or is_stray_link:
            cut.append(segment)
        else:
            kept.append(segment)
        previous_cut = is_note or is_stray_link
    if not cut:
        return source, ''
    record = '; '.join(kept).strip()
    if not LINK.search(record):
        record = first_link(source)
    return record, '; ' + '; '.join(cut)


def copied(old, name):
    """Whether the row says the organisation of the person was copied from the mapping."""
    text = f"{old.row.get('Source') or ''} {old.row.get('Notes') or ''}"
    for match in COPIED.finditer(text):
        who = match.group('who')
        if who is None or normalise(who) == normalise(name):
            return True
    return False


def person_link(cut, name, single):
    """The link of the cut remainder that is about the person, else ''.

    That is `organisation of <name> from …: <link>` or `<name>: <link>`; in a row of one person also a note
    without a name, such as `organisation from the Board page of the year: <link>` or `organisation: <link>`.
    """
    segments = [segment.strip() for segment in cut.split('; ') if segment.strip()]
    for segment in segments:
        match = re.match(r'organisations? of (?P<who>[^;:]+?) from [^:]*:', segment) or \
            re.match(r'(?P<who>[^:;]+): https?://', segment)
        if match and normalise(match.group('who')) == normalise(name) and first_link(segment):
            return first_link(segment)
    if single:
        for segment in segments:
            if re.match(r'organisations?(:| from )', segment) and first_link(segment):
                return first_link(segment)
    return ''


def unique(values):
    """The values without empty ones and repeats, in order."""
    return list(dict.fromkeys(value for value in values if value))


class Rewriter:
    """Rewrites the old rows with the registers built from them.

    `people.person_id(name, handle, row_organisations)` gives the id of a person or None for a group;
    `organisations.id_for(spelling)` the id of an organisation or None; `affiliated(person, year)` the
    organisation id the affiliations give, or None.
    """

    def __init__(self, people, organisations, affiliated, report):
        self.people = people
        self.organisations = organisations
        self.affiliated = affiliated
        self.report = report
        self.proposals = []

    def organisation(self, old, spelling):
        """The id of an organisation cell; ValueError for a spelling that is no organisation."""
        org_id = self.organisations.id_for(spelling)
        if org_id is None:
            raise ValueError(f'{old.file}:{old.line}: "{spelling}" is no organisation in organisations.csv')
        return org_id

    def organisation_set(self, old, cell):
        """The ids of a cell of organising entities, without Unmapped."""
        return unique(self.organisation(old, spelling) for spelling in split(cell) if spelling != UNMAPPED)

    def rewrite(self, rows):
        """{file: (header, new rows)} for every old file, in the order of the old rows."""
        files = {}
        for old in rows:
            header, new_rows = files.setdefault(old.file, (HEADERS[old.kind], []))
            new_rows.extend(self.rewrite_row(old))
        return files

    def resolve(self, old):
        """[(name, person id or None)] of the person column, groups reported or turned into organisations.

        Returns the people, the organisation ids of the `<Org> team` entries of talks, and the other groups,
        which are dropped from the person cell.
        """
        organisations = split(old.row.get('Organisation'))
        cells = people_cells(old)
        resolved, teams, groups = [], [], []
        for index, (name, handle) in enumerate(cells):
            person = self.people.person_id(name, handle, organisations)
            resolved.append((name, person))
            if person is not None:
                continue
            if old.kind == TALKS and name.casefold().endswith(' team'):
                paired = organisations[index] if len(organisations) == len(cells) else ''
                org_id = self.organisations.id_for(paired) if paired and paired != UNMAPPED else None
                teams.append(org_id or self.organisation(old, name[:-len(' team')].strip()))
            else:
                self.report.dropped_groups.append((old.file, old.line, name))
                groups.append(name)
        return resolved, teams, groups

    def state(self, old, resolved, cut):
        """Turn the organisation cells of a per-person row into proposals where the affiliations differ.

        A cell the row marks as copied from the mapping must agree with the affiliations of its year; a copy
        that does not stops the run, as the migration cannot tell which of the two is right.
        """
        organisations = split(old.row.get('Organisation'))
        if not organisations or not resolved:
            return
        if len(organisations) == len(resolved):
            pairs = list(zip(resolved, organisations))
        else:
            pairs = [(cell, organisation) for cell in resolved for organisation in organisations]
            self.report.unaligned.append((old.file, old.line, '; '.join(name for name, _ in resolved),
                                          ';'.join(organisations)))
        for (name, person), spelling in pairs:
            if person is None or spelling == UNMAPPED:
                continue
            org_id = self.organisation(old, spelling)
            current = self.affiliated(person, old.year)
            if copied(old, name):
                if current != org_id:
                    raise ValueError(f'{old.file}:{old.line}: the organisation of {name} is marked as copied from '
                                     f'the mapping, but the mapping gives no "{spelling}" for {old.year}')
                continue
            if current == org_id:
                continue
            kind = 'no-login' if not self.people.has_login(person) else 'unmapped' if current is None else 'differs'
            link = person_link(cut, name, len(resolved) == 1) or first_link(old.row.get('Source')) or 'no link'
            self.proposals.append({'person': person, 'organisation': org_id, 'from': old.year, 'to': old.year,
                                   'evidence': f'{old.file}:{old.line}; {link}', 'kind': kind})

    def rewrite_row(self, old):
        """The new rows of an old row."""
        row = old.row
        source, cut = cut_source(old)
        if cut:
            self.report.cut_sources.append((old.file, old.line, cut))
        notes = (row.get('Notes') or '').strip()
        resolved, teams, groups = self.resolve(old)
        if groups:
            # A group is no person; what the old cell said goes to the notes, as for a podcast without a host
            word = PEOPLE_WORDS.get(old.kind, 'people')
            notes = '; '.join(unique([notes, f'{word} in the old file: {"; ".join(groups)}']))
        people = unique(person for _, person in resolved)
        if old.kind in PER_PERSON:
            self.state(old, resolved, cut)
        kind = old.kind
        if kind == 'podcasts' and not resolved:
            # A series without a named host keeps its row; the organisation it named goes to the notes
            cell = (row.get('Organisation') or '').strip()
            notes = '; '.join(unique([notes, f'organisation in the old file: {cell}' if cell else '']))
            return [{'series': row['Series'].strip(), 'person': '', 'episodes': row['Episodes'].strip(),
                     'source': source, 'notes': notes}]
        if kind in ('board-of-directors', 'team-leaders', 'release-managers', 'podcasts'):
            if not resolved:
                self.report.unrepresentable.append((old.file, old.line, f'no person: {dict(row)}'))
            extra = {'board-of-directors': lambda: {'role': row['Role'].strip()},
                     'team-leaders': lambda: {'team': row['Team'].strip()},
                     'release-managers': lambda: {},
                     'podcasts': lambda: {'series': row['Series'].strip(), 'episodes': row['Episodes'].strip()}}[kind]
            return [{**extra(), 'person': person, 'source': source, 'notes': notes} for person in people]
        if kind == 'plone-conference-trainings':
            return [{'title': row['Title'].strip(), 'trainers': ';'.join(people), 'source': source, 'notes': notes}]
        if kind == TALKS:
            video = (row.get('YouTube ID') or '').strip()
            if video and video not in source:
                self.report.unrepresentable.append((old.file, old.line, f'YouTube ID {video} is not in the source'))
            if not resolved:
                teams.extend(self.organisation_set(old, row.get('Organisation')))
            return [{'title': row['Video Title'].strip(), 'speakers': ';'.join(people),
                     'organisations': ';'.join(unique(teams)), 'type': row['Type'].strip(),
                     'location': row['Event / Location'].strip(), 'source': source, 'notes': notes}]
        organisations = self.organisation_set(old, row.get('Organisation'))
        if kind == 'sprints':
            return [{'sprint': row['Sprint'].strip(), 'start': row['Start'].strip(), 'end': row['End'].strip(),
                     'location': row['Location'].strip(), 'organisers': ';'.join(people),
                     'organisations': ';'.join(organisations), 'level': row['Level'].strip(), 'source': source,
                     'notes': notes}]
        if kind == 'plone-conference':
            if len(organisations) > 1:
                self.report.unrepresentable.append((old.file, old.line, f'several organisations: {dict(row)}'))
                return []
            # An Unmapped host leaves the cell empty; organisers, source and notes stay
            return [{'organisation': organisations[0] if organisations else '', 'organisers': ';'.join(people),
                     'source': source, 'notes': notes}]
        return [{'date': row['Date'].strip(), 'location': row['Location'].strip(), 'format': row['Format'].strip(),
                 'organisations': ';'.join(organisations), 'organisers': '', 'source': source, 'notes': notes}]
