"""The audit of the regenerated outputs after the migration (#139).

`git diff` shows what the regeneration changed in derived/ and reports/. The specification allows few causes:
code attribution must not change at all; community credit changes only for the rows the migration deferred to
affiliation_proposals.csv and for organiser roles; every other difference must be explained by a defect named in
the analysis (#139, Part 1). The audit gives every changed line one class, the cause it can prove:

- person-rename: a person without a GitHub login, once named, is now the username `person:<id>`.
- deferred: credit that a community row stated and the migration deferred to a proposal.
- organiser-role: a sprint or conference organiser's role counts for the person's organisation now, no longer
  for the organising entity.
- positional-fix: a row whose organisations were not one per person credited each organisation once per person.
- unmapped-cell: a row whose organisation cell said Unmapped (or nothing) counts for the organisation the mapping
  gives for the year: the cell was a copy older than the mapping.
- no-host-podcast: a podcast series without a named host credited the organisation of its row; the podcasts
  schema has one row per host and no organisation column, so the migration moved the organisation to the notes
  and the series credits no one. Not a cause the specification names: a reviewer must accept it.
- key-shape: the community page names people by person id, not by `name:` key or lower-case login.
- display-name: a person is shown by the display name of the register, not by the spelling of the row or login.
- source-cut: a Source cell lost the notes on people's organisations, which the affiliations hold now.
- reordered: the line's record is unchanged on the other side; only its position moved.
- timestamp: the generation time stamp, which the reproducibility test ignores too.
- unexplained: anything else.

A line is unexplained unless a rule proves its class; the rules are deliberately narrow.
"""

import csv
import io
import json
import re
import subprocess
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model import UNMAPPED, events, items, load_registry, read_rows
from scripts.lib.model.names import fold
from scripts.tools.migrate_data import legacy_community
from scripts.tools.migrate_data.community import NOTES, first_link
from scripts.tools.migrate_data.community import read_rows as read_old_rows
from scripts.tools.migrate_data.legacy_people import is_group

CLASSES = ('person-rename', 'deferred', 'organiser-role', 'positional-fix', 'unmapped-cell', 'no-host-podcast',
           'key-shape', 'display-name', 'source-cut', 'reordered', 'timestamp', 'unexplained')
UNEXPLAINED = 'unexplained'
# The time stamp line of the reports, as tests/test_reproducible_outputs.py ignores it
GENERATED = re.compile(r'^\*?Generated( on)?:.*$')
PERSON_USERNAME = re.compile(r'^person:[a-z0-9-]+$')
ORGANISER_KINDS = ('sprints', 'plone-conference')
TALKS = 'world-plone-day-talks'
PAGE = paths.COMMUNITY_PAGE.as_posix()
RECOGNITION_CSV = re.compile(r'^derived/community-recognition/(\d{4})-community-recognition-report\.csv$')
RECOGNITION_MD = 'reports/community-recognition.md'
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


@dataclass
class Line:
    """A changed line: `-` from the committed file, `+` from the work tree, and its counterpart, if paired."""

    sign: str
    number: int
    text: str
    counterpart: 'Line | None' = None

    def excerpt(self):
        return f'{self.sign}{self.number}: {self.text[:200]}'


def git(root, *args):
    """The output of a read-only git command in root."""
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8',
                          check=True).stdout


def changed_files(root):
    """The files under derived/ and reports/ that differ from the committed ones, staged or not."""
    return git(root, 'diff', 'HEAD', '--name-only', '--', 'derived', 'reports').split()


def hunks(root, file):
    """[(removed lines, added lines)] of the hunks of `git diff -U0` of a file."""
    found = []
    for text in git(root, 'diff', 'HEAD', '-U0', '--', file).splitlines():
        match = HUNK.match(text)
        if match:
            found.append(([], []))
            numbers = {'-': int(match.group(1)), '+': int(match.group(3))}
        elif found and text[:1] in ('-', '+'):  # the `---`/`+++` header lines come before the first hunk
            sign = text[0]
            (found[-1][0] if sign == '-' else found[-1][1]).append(Line(sign, numbers[sign], text[1:]))
            numbers[sign] += 1
    return found


def pair_by_position(removed, added):
    """Pair the removed and added lines of a hunk by their position in it."""
    for old, new in zip(removed, added):
        old.counterpart, new.counterpart = new, old


def csv_cells(text):
    return next(csv.reader([text]), [])


def pair_by_first_cell(lines):
    """Pair the removed and added lines of a CSV file by their first cell (the organisation), when it is unique on
    both sides: a row whose points changed may move to another position."""
    def first_cell(line):
        return (csv_cells(line.text) or [''])[0]

    counts = Counter((line.sign, first_cell(line)) for line in lines)
    pairs = {}
    for line in lines:
        key = first_cell(line)
        if counts[('-', key)] == 1 and counts[('+', key)] == 1:
            pairs.setdefault(key, {})[line.sign] = line
    for pair in pairs.values():
        pair['-'].counterpart, pair['+'].counterpart = pair['+'], pair['-']


def json_lines(value):
    """[path] per line of `json.dump(value, indent=1, sort_keys=True, ensure_ascii=False)`, with the lines.

    A path is the tuple of keys and list indexes from the root; the lines that open and close a container carry
    the container's path.
    """
    found = []

    def emit(item, path, depth, key, last):
        pad = ' ' * depth
        head = pad + (json.dumps(key, ensure_ascii=False) + ': ' if key is not None else '')
        comma = '' if last else ','
        if isinstance(item, dict) and item:
            found.append((path, head + '{'))
            keys = sorted(item)
            for index, child in enumerate(keys):
                emit(item[child], path + (child,), depth + 1, child, index == len(keys) - 1)
            found.append((path, pad + '}' + comma))
        elif isinstance(item, list) and item:
            found.append((path, head + '['))
            for index, child in enumerate(item):
                emit(child, path + (index,), depth + 1, None, index == len(item) - 1)
            found.append((path, pad + ']' + comma))
        else:
            found.append((path, head + json.dumps(item, ensure_ascii=False) + comma))

    emit(value, (), 0, None, True)
    return found


def value_at(document, path):
    """The value at a path, or KeyError."""
    for key in path:
        if isinstance(document, list):
            if not isinstance(key, int) or key >= len(document):
                raise KeyError(key)
        elif not isinstance(document, dict) or key not in document:
            raise KeyError(key)
        document = document[key]
    return document


def is_source_cut(old, new, is_person):
    """Whether `new` is the Source cell `old` without its notes on people's organisations.

    The cell is read as `; `-separated segments, as the migration cuts it: a segment that starts with a note
    (`organisation of `, `organisation from `, ...) or is `<name of a person>: <link>` is cut, and so is a bare
    link right after a cut segment; the other segments stay in order. When nothing with a link stays, the record
    is the first link of the cell.
    """
    if not isinstance(old, str) or not isinstance(new, str) or old == new:
        return False
    kept, previous_cut = [], False
    for segment in old.split('; '):
        text = segment.strip()
        record = re.match(r'([^:;]+): https?://', text)
        cut = text.startswith(NOTES) or bool(record and is_person(record.group(1))) or (
            previous_cut and bool(re.fullmatch(r'https?://\S+', text)))
        if not cut:
            kept.append(segment)
        previous_cut = cut
    record = '; '.join(kept).strip()
    return new == record or (not re.search(r'https?://', record) and new == first_link(old))


class Context:
    """What the rules need to know, read once: the registers, the proposals, the old and new files."""

    def __init__(self, root, base):
        self.root = Path(root)
        self.base = base
        self._temporary = None
        self._credits = {}
        self._people_index = {}
        self._deferred_organisations = None
        # Set by the recognition CSV, which is audited before the markdown report that sums it up
        self.recognition_all_deferred = False

    def close(self):
        if self._temporary is not None:
            self._temporary.cleanup()

    @cached_property
    def registry(self):
        return load_registry(self.root / paths.MAPPINGS_DIR)

    @cached_property
    def proposals(self):
        return read_rows(self.root / paths.AFFILIATION_PROPOSALS)

    def old_text(self, file):
        return git(self.root, 'show', f'HEAD:{file}')

    def new_text(self, file):
        return (self.root / file).read_text(encoding='utf-8')

    @cached_property
    def old_page(self):
        return json.loads(self.old_text(PAGE))

    @cached_property
    def new_page(self):
        return json.loads(self.new_text(PAGE))

    # People

    @cached_property
    def spellings(self):
        """{spelling: display name} of every name and login of a person that differs from the display name."""
        found = {}
        for person in self.registry.people.values():
            if person.github and person.github != person.name:
                found.setdefault(person.github, person.name)
        for identity in self.registry.identities:
            display = self.registry.people[identity.person].name
            if identity.kind in ('name', 'login') and identity.value != display:
                found.setdefault(identity.value, display)
        return found

    @cached_property
    def spelling_pattern(self):
        alternatives = sorted(self.spellings, key=len, reverse=True)
        return re.compile(r'(?<!\w)(?:' + '|'.join(map(re.escape, alternatives)) + r')(?!\w)')

    def with_display_names(self, text):
        """The text with every spelling of a person replaced by the person's display name."""
        if not self.spellings:
            return text
        return self.spelling_pattern.sub(lambda match: self.spellings[match.group(0)], text)

    def person_without_login(self, name):
        """The person without a GitHub login that a name denotes, or None."""
        person = self.registry.person_for(name=name)
        return person if person is not None and not person.github else None

    def page_key(self, old_key):
        """The person id the new page uses for a key of the old page: `name:<name>` or a lower-case login."""
        if old_key.startswith('name:'):
            person = self.registry.person_for(name=old_key[len('name:'):])
        else:
            person = self.registry.person_for(login=old_key)
        return person.id if person else old_key

    def people_index(self, year):
        """{'-': {new key: index in the old list}, '+': {id: index in the new list}} of the people of a year.

        A key that two old entries resolve to is left out, so that they find no counterpart.
        """
        if year not in self._people_index:
            old = Counter(self.page_key(p['id']) for p in self.old_page['people'][year])
            self._people_index[year] = {
                '-': {self.page_key(p['id']): i for i, p in enumerate(self.old_page['people'][year])
                      if old[self.page_key(p['id'])] == 1},
                '+': {p['id']: i for i, p in enumerate(self.new_page['people'][year])},
            }
        return self._people_index[year]

    # Organisations and proposals

    @cached_property
    def organisation_names(self):
        return {organisation.name for organisation in self.registry.organisations.values()}

    def canonical(self, spelling):
        """The register name of an organisation spelling; the spelling itself when the register has none."""
        org_id = self.registry.organisation_id(spelling)
        return self.registry.organisation_name(org_id) if org_id else spelling

    def has_proposal(self, person_id, organisation, year):
        """Whether a proposal says the person belonged to the organisation in the year."""
        org_id = self.registry.organisation_id(organisation)
        return any(p['person'] == person_id and p['organisation'] == org_id and p['from'] <= year <= p['to']
                   for p in self.proposals)

    def row_proposal(self, file, line, organisation):
        """Whether a proposal for the organisation names the old row `file:line` as its evidence."""
        org_id = self.registry.organisation_id(organisation)
        return any(p['organisation'] == org_id and p['evidence'].startswith(f'{file}:{line};')
                   for p in self.proposals)

    # The old community files and what they credited

    @cached_property
    def old_root(self):
        """A folder with the curated community files of the base revision, or None without a base."""
        if self.base is None:
            return None
        self._temporary = tempfile.TemporaryDirectory(prefix='audit-')
        archive = subprocess.run(['git', 'archive', '--format=tar', self.base, paths.COMMUNITY.as_posix()],
                                 cwd=self.root, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(self._temporary.name, filter='data')
        return Path(self._temporary.name)

    @cached_property
    def old_rows(self):
        """{(file, line): old row} of the old community files."""
        return {(row.file, row.line): row for row in read_old_rows(self.old_root)}

    def relative(self, file):
        return Path(file).relative_to(self.old_root).as_posix()

    def credits(self, year):
        """[Credit] of every old community record of the year: what it credited then and what it credits now."""
        if year not in self._credits:
            records = legacy_community.community_records(year, self.old_root / paths.COMMUNITY)
            self._credits[year] = [credit_of(self, record, year) for record in records]
        return self._credits[year]


@dataclass
class Credit:
    record: object
    old: list
    new: list
    cause: str | None


def person_of(ctx, record):
    """The person of an old record: by its handle where the row had one per person, else by its name."""
    person = ctx.registry.person_for(login=record.handle) if record.handle else None
    return person or ctx.registry.person_for(name=record.person)


def credit_of(ctx, record, year):
    """The organisations an old record credited (the old cell, split) and credits now (the person's organisation).

    A talk of a company team, without a person or with the team in the speaker column, counts for the team's
    organisation then and now; another record without a person (a group) credits no one now.
    """
    file = ctx.relative(record.file)
    row = ctx.old_rows[(file, record.line)].row
    old = [ctx.canonical(o) for o in legacy_community.split(record.organisation)]
    person = person_of(ctx, record) if record.person else None
    team = not record.person or is_group(record.person, ctx.organisation_names,
                                         legacy_community.split(row.get('Organisation')))
    if person is not None:
        new = [ctx.registry.organisation_of(person.id, year)]
    elif record.kind == TALKS and team:
        new = old
    else:
        new = []
    old_counted, new_counted = [o for o in old if o != UNMAPPED], [o for o in new if o != UNMAPPED]
    cause = None
    if Counter(old_counted) != Counter(new_counted):
        cause = cause_of(ctx, record, file, row, person, old_counted, new_counted, year)
    return Credit(record, old, new, cause)


def cause_of(ctx, record, file, row, person, old, new, year):
    """Why a record credits other organisations than before; 'unexplained' when no rule proves it.

    Organiser roles first: they count for the person's organisation by design. Then a row whose stated
    organisations all went to proposals: deferred, or positional-fix when the row had not one organisation per
    person. A cell without a stated organisation that now has the mapping's: unmapped-cell.
    """
    if record.kind in ORGANISER_KINDS:
        return 'organiser-role'
    if record.kind == 'podcasts' and not record.person:
        return 'no-host-podcast' if podcast_organisation_in_notes(ctx, row, year) else UNEXPLAINED
    stated = [o for o in old if o not in new]
    if not stated:
        return 'unmapped-cell' if person is not None else UNEXPLAINED
    person_column = legacy_community.ROLE_KINDS[record.kind][1]
    people = legacy_community.split(row.get(person_column))
    organisations = legacy_community.split(row.get('Organisation'))
    aligned = len(organisations) == len(people)
    if aligned and person is not None and all(ctx.has_proposal(person.id, o, year) for o in stated):
        return 'deferred'
    if not aligned and all(ctx.row_proposal(file, record.line, o) for o in stated):
        return 'positional-fix'
    return UNEXPLAINED


def podcast_organisation_in_notes(ctx, row, year):
    """Whether the new podcasts file keeps the series of an old row without a host, without a host, and with the
    organisation of the old row in its notes, as the migration writes it."""
    note = f"organisation in the old file: {(row.get('Organisation') or '').strip()}"
    return any(item.key == (row.get('Series') or '').strip() and not item.people and note in item.notes
               for item in items(year, 'podcasts', ctx.root / paths.COMMUNITY))


def joined(causes):
    """One class for a line that several credit changes explain, e.g. `deferred+organiser-role`."""
    causes = set(causes)
    if not causes or UNEXPLAINED in causes:
        return UNEXPLAINED
    return '+'.join(c for c in CLASSES if c in causes)


# Plain files: CSV, markdown and text


def classify_person_rename(ctx, line):
    """person-rename: the line equals its counterpart once each `person:<id>` username is read as a name of that
    person without a GitHub login. CSV cells are compared as sets of `, `-separated usernames, since a renamed
    username sorts elsewhere in the list."""
    old, new = (line, line.counterpart) if line.sign == '-' else (line.counterpart, line)
    if old is None or 'person:' not in new.text:
        return None

    def username(token, side):
        if side == 'new' and PERSON_USERNAME.match(token) and token[len('person:'):] in ctx.registry.people:
            return token if not ctx.registry.people[token[len('person:'):]].github else None
        person = ctx.person_without_login(token) if side == 'old' and ' ' in token else None
        return f'person:{person.id}' if person else token

    old_cells, new_cells = csv_cells(old.text), csv_cells(new.text)
    if len(old_cells) != len(new_cells):
        return None
    for old_cell, new_cell in zip(old_cells, new_cells):
        if old_cell == new_cell:
            continue
        old_names = sorted(username(t.strip(), 'old') for t in old_cell.split(','))
        new_names = sorted(username(t.strip(), 'new') for t in new_cell.split(','))
        if None in new_names or old_names != new_names:
            return None
    return 'person-rename'


def classify_timestamp(ctx, line):
    """timestamp: both the line and its counterpart are the `Generated:` line of a report."""
    if line.counterpart and GENERATED.match(line.text) and GENERATED.match(line.counterpart.text):
        return 'timestamp'
    return None


def classify_display_name(ctx, line):
    """display-name: the line equals its counterpart once every spelling of a person in the committed line is
    replaced by the person's display name."""
    old, new = (line, line.counterpart) if line.sign == '-' else (line.counterpart, line)
    if old is None or old.text == new.text:
        return None
    return 'display-name' if ctx.with_display_names(old.text) == new.text else None


def classify_plain(ctx, file, lines, rules):
    return [(file, next((c for c in (rule(ctx, line) for rule in rules) if c), UNEXPLAINED), line.excerpt())
            for line in lines]


# The recognition CSV and its markdown report


def deferred_organisations(ctx):
    """{name: points lost} of the organisations whose recognition contributions changed only by deferred rows.

    A contribution that only one side has must be a row that a proposal for that organisation names as
    evidence (`file:line`); the contributions both sides have must have the same points (their text and source
    are classified on their own lines).
    """
    if ctx._deferred_organisations is not None:
        return ctx._deferred_organisations
    found = {}
    old_orgs, new_orgs = ctx.old_page['organisations'], ctx.new_page['organisations']
    for slug in set(old_orgs) | set(new_orgs):
        old, new = old_orgs.get(slug, {}), new_orgs.get(slug, {})
        name = old.get('name') or new.get('name')
        lost, changed, explained = 0, False, True
        for category in set(old.get('categories', {})) | set(new.get('categories', {})):
            before = old.get('categories', {}).get(category, {}).get('contributions', [])
            after = new.get('categories', {}).get(category, {}).get('contributions', [])
            for side, contributions, others in (('-', before, after), ('+', after, before)):
                for contribution in contributions:
                    counterpart = contribution_counterpart(contribution, others)
                    if counterpart is None:
                        changed = True
                        lost += contribution['points'] if side == '-' else -contribution['points']
                        explained = explained and ctx.row_proposal(contribution['file'], contribution['line'], name)
                    elif counterpart['points'] != contribution['points']:
                        explained = False
        if changed and explained:
            found[name] = lost
    ctx._deferred_organisations = found
    return found


def contribution_counterpart(contribution, others):
    """The contribution of the same row on the other side, or None."""
    same = [c for c in others if (c['file'], c['line']) == (contribution['file'], contribution['line'])]
    return same[0] if len(same) == 1 else None


def classify_recognition_csv(ctx, file, lines):
    """deferred: a recognition row of an organisation whose changed contributions are all deferred rows: its talk
    points and total fell by the points of those rows (to nothing for a row that dropped out), and the other
    columns but the level are unchanged."""
    header = csv_cells(ctx.new_text(file).splitlines()[0])
    talk, total = header.index('WPD Talk'), header.index('Total Points')
    unchanged = [i for i, name in enumerate(header) if name not in ('Recognition Level', 'WPD Talk', 'Total Points')]
    deferred = deferred_organisations(ctx)

    def kind(line):
        cells = csv_cells(line.text)
        if not cells or cells[0] not in deferred:
            return UNEXPLAINED
        old, new = (line, line.counterpart) if line.sign == '-' else (line.counterpart, line)
        old_cells = csv_cells(old.text) if old else None
        new_cells = csv_cells(new.text) if new else [cells[0]] + ['0'] * (len(header) - 1)
        if old_cells is None:
            return UNEXPLAINED
        lost = deferred[cells[0]]
        if (float(old_cells[talk]) - float(new_cells[talk]) == lost == float(old_cells[total]) - float(new_cells[total])
                and (new is None or all(old_cells[i] == new_cells[i] for i in unchanged))):
            return 'deferred'
        return UNEXPLAINED

    found = [(file, kind(line), line.excerpt()) for line in lines]
    ctx.recognition_all_deferred = all(k == 'deferred' for _, k, _ in found)
    return found


def markdown_sections(text):
    """[(h2, h3)] per line of a markdown report: the headings the line is under."""
    found, h2, h3 = [], None, None
    for text_line in text.splitlines():
        if text_line.startswith('## '):
            h2, h3 = text_line[3:], None
        elif text_line.startswith('### '):
            h3 = text_line[4:]
        found.append((h2, h3))
    return found


def section_lines(text, sections):
    """{h3: [lines]} of the organisation sections."""
    found = {}
    for text_line, (h2, h3) in zip(text.splitlines(), sections):
        if h3:
            found.setdefault(h3, []).append(text_line)
    return found


LEADERBOARD_ROW = re.compile(r'^\| (\d+) \| (.+) \| (.+) \| ([\d.]+) \|$')


def classify_recognition_markdown(ctx, file, lines):
    """The lines of the recognition report, by the section they are in.

    deferred: a line in the section of a deferred organisation, a leaderboard row of one, or a line of the
    summaries (Executive Summary, Recognition Levels, Statistics by Category) when every changed row of the
    recognition CSV is deferred. reordered: a leaderboard row whose organisation, level and points are unchanged,
    or a line of an organisation section that moved as a whole. display-name and timestamp as everywhere.
    """
    old_text, new_text = ctx.old_text(file), ctx.new_text(file)
    sections = {'-': markdown_sections(old_text), '+': markdown_sections(new_text)}
    blocks = {'-': section_lines(old_text, sections['-']), '+': section_lines(new_text, sections['+'])}
    boards = {sign: {m.group(2): (m.group(3), m.group(4)) for m in map(LEADERBOARD_ROW.match, text.splitlines())
                     if m} for sign, text in (('-', old_text), ('+', new_text))}
    deferred = deferred_organisations(ctx)
    summaries = ('Executive Summary', 'Recognition Levels', 'Statistics by Category')

    def kind(line):
        h2, h3 = sections[line.sign][line.number - 1]
        other = '+' if line.sign == '-' else '-'
        row = LEADERBOARD_ROW.match(line.text)
        if classify_timestamp(ctx, line):
            return 'timestamp'
        if h3 in deferred or (row and row.group(2) in deferred):
            return 'deferred'
        if h2 in summaries and h3 is None and ctx.recognition_all_deferred:
            return 'deferred'
        if row and boards[other].get(row.group(2)) == (row.group(3), row.group(4)):
            return 'reordered'
        if h3 and blocks['-'].get(h3) == blocks['+'].get(h3):
            return 'reordered'
        return classify_display_name(ctx, line) or UNEXPLAINED

    return [(file, kind(line), line.excerpt()) for line in lines]


# The community page


def page_counterpart(ctx, side, path):
    """The path of the same record on the other side, or None when it has none.

    People are matched by person (the old key resolved through the register), contributions by their row
    (file and line), wall entries by organisation name within their level; everything else by its path.
    """
    old, new = ctx.old_page, ctx.new_page
    this, that = (old, new) if side == '-' else (new, old)
    if path[:1] == ('people',) and len(path) >= 3:
        year = path[1]
        key = value_at(this, path[:3])['id']
        index = ctx.people_index(year)['+' if side == '-' else '-'].get(ctx.page_key(key) if side == '-' else key)
        return None if index is None else ('people', year, index, *path[3:])
    if path[:1] == ('organisations',) and len(path) >= 6 and path[4] == 'contributions':
        contribution = value_at(this, path[:6])
        try:
            others = value_at(that, path[:5])
        except KeyError:
            return None
        row = (contribution['file'], contribution['line'])
        match = [i for i, c in enumerate(others) if (c['file'], c['line']) == row]
        return (*path[:5], match[0], *path[6:]) if len(match) == 1 else None
    if path[:1] == ('wall',) and len(path) >= 2:
        level = value_at(this, path[:2])['level']
        levels = [i for i, w in enumerate(that['wall']) if w['level'] == level]
        if not levels:
            return None
        if len(path) < 4:
            return ('wall', levels[0], *path[2:])
        name = value_at(this, path[:4])['name']
        match = [i for i, o in enumerate(that['wall'][levels[0]]['organisations']) if o['name'] == name]
        return ('wall', levels[0], 'organisations', match[0], *path[4:]) if match else None
    try:
        value_at(that, path)
    except KeyError:
        return None
    return path


def classify_page(ctx, file, lines):
    """Every changed line of the community page, by the path of its value in the JSON document."""
    walked = {'-': json_lines(ctx.old_page), '+': json_lines(ctx.new_page)}
    texts = {'-': ctx.old_text(file).splitlines(), '+': ctx.new_text(file).splitlines()}
    if any([text for _, text in walked[side]] != texts[side] for side in '-+'):
        return [(file, UNEXPLAINED, f'{line.excerpt()} (the JSON layout is not the one the audit reads)')
                for line in lines]
    return [(file, classify_page_line(ctx, line.sign, walked[line.sign][line.number - 1][0]), line.excerpt())
            for line in lines]


def classify_page_line(ctx, side, path):
    """The class of one line of the community page, from the values at its path on both sides."""
    section = path[0] if path else None
    if section == 'people_names':
        return classify_people_names(ctx, side, path)
    if section == 'people' and len(path) >= 3:
        counterpart = page_counterpart(ctx, side, path[:3])
        return UNEXPLAINED if counterpart is None else classify_person_record(ctx, side, path[:3], counterpart)
    if section == 'organisations' and len(path) >= 2:
        name = value_at(ctx.old_page if side == '-' else ctx.new_page, path[:2])['name']
        if page_counterpart(ctx, side, path[:2]) is None:
            return 'deferred' if name in deferred_organisations(ctx) else UNEXPLAINED
    this = value_at(ctx.old_page if side == '-' else ctx.new_page, path)
    counterpart = page_counterpart(ctx, side, path)
    try:
        that = value_at(ctx.new_page if side == '-' else ctx.old_page, counterpart) if counterpart else None
    except KeyError:
        counterpart = None
    if counterpart is None:
        return classify_one_sided(ctx, side, path)
    old, new = (this, that) if side == '-' else (that, this)
    if isinstance(old, (dict, list)) or old == new:
        return 'reordered'
    return classify_page_value(ctx, side, path if side == '-' else counterpart, old, new)


def classify_one_sided(ctx, side, path):
    """A value that only one side has: a field the new page added, or a deferred contribution or organisation."""
    section = path[0]
    page = ctx.old_page if side == '-' else ctx.new_page
    if section == 'organisations' and len(path) >= 4 and path[2] == 'categories':
        name = value_at(page, path[:2])['name']
        if name not in deferred_organisations(ctx):
            return UNEXPLAINED
        return 'deferred'
    if section == 'wall' and len(path) >= 4:
        name = value_at(page, path[:4])['name']
        return 'deferred' if name in deferred_organisations(ctx) else UNEXPLAINED
    return UNEXPLAINED


def classify_person_record(ctx, side, path, counterpart):
    """key-shape: a person of a year whose commits, pull requests and roles are equal on both sides; only the key
    (`name:` or a lower-case login, now the person id) and the added display name of the person differ."""
    old_path, new_path = (path, counterpart) if side == '-' else (counterpart, path)
    old = value_at(ctx.old_page, old_path)
    new = value_at(ctx.new_page, new_path)
    person = ctx.registry.people.get(new['id'])
    fields = ('commits', 'pull_requests', 'roles')
    if (all(old[f] == new[f] for f in fields) and ctx.page_key(old['id']) == new['id']
            and new['name'] == (person.name if person else new['id'])):
        return 'key-shape'
    return UNEXPLAINED


def classify_people_names(ctx, side, path):
    """key-shape: the search index of names. An old entry (normalised name -> login) is found again as the folded
    name -> the id of that login's person; a new entry's key is the folded name, login or identity of its id."""
    if len(path) != 2:
        return UNEXPLAINED
    key = path[1]
    if side == '-':
        login = ctx.old_page['people_names'][key]
        person = ctx.registry.person_for(login=login)
        return 'key-shape' if person and ctx.new_page['people_names'].get(fold(key)) == person.id else UNEXPLAINED
    person = ctx.registry.people.get(ctx.new_page['people_names'][key])
    if person is None:
        return UNEXPLAINED
    keys = {fold(person.name), fold(person.github or '')}
    keys |= {fold(i.value) for i in ctx.registry.identities if i.person == person.id and i.kind in ('name', 'login')}
    return 'key-shape' if key in keys else UNEXPLAINED


def classify_page_value(ctx, side, old_path, old, new):
    """A value that differs between the sides, by what it is."""
    section, field = old_path[0], old_path[-1]
    if field == 'name' or (section == 'organisations' and field == 'text'):
        return 'display-name' if isinstance(old, str) and ctx.with_display_names(old) == new else UNEXPLAINED
    if field == 'source' or (len(old_path) >= 2 and old_path[-2] == 'sources'):
        is_person = lambda name: ctx.registry.person_for(name=name) is not None  # noqa: E731
        if old is None and section == 'organisations':
            return classify_talk_without_video(ctx, value_at(ctx.old_page, old_path[:-1]), new, is_person)
        return 'source-cut' if is_source_cut(old, new, is_person) else UNEXPLAINED
    if section == 'history' and field == 'organisation':
        return classify_holder_organisation(ctx, old_path, old, new)
    if section == 'organisations' and old_path[2:3] == ('history',) and field == 'roles':
        return classify_role_count(ctx, old_path, old, new)
    if section == 'organisations' and field in ('points', 'level', 'next_level', 'points_to_next'):
        name = ctx.old_page['organisations'][old_path[1]]['name']
        return 'deferred' if name in deferred_organisations(ctx) else UNEXPLAINED
    if section == 'wall':
        name = value_at(ctx.old_page, old_path[:4])['name']
        return 'deferred' if name in deferred_organisations(ctx) else UNEXPLAINED
    if section == 'headline' and field == 'organisations':
        return classify_headline_organisations(ctx, old_path, old, new)
    return UNEXPLAINED


def classify_talk_without_video(ctx, contribution, new, is_person):
    """source-cut: a talk without a video, which the old page showed without a source (its source was the video
    link), shows the row's Source cell now, cut like every other."""
    if ctx.old_root is None or not contribution['file'].endswith(f'-{TALKS}.csv'):
        return UNEXPLAINED
    row = ctx.old_rows[(contribution['file'], contribution['line'])].row
    if (row.get('YouTube ID') or '').strip():
        return UNEXPLAINED
    source = (row.get('Source') or '').strip()
    return 'source-cut' if new == source or is_source_cut(source, new, is_person) else UNEXPLAINED


def classify_holder_organisation(ctx, path, old, new):
    """The organisation of a Board member or team lead: the person's organisation of the year now.

    unmapped-cell when the row said Unmapped; deferred when every organisation it stated that is not the one the
    affiliations give is a proposal for the person and year, positional-fix when the row stated several
    organisations for the one person, which the old page credited each.
    """
    year = int(path[1])
    holder = value_at(ctx.new_page, path[:-1])
    person = ctx.registry.person_for(name=value_at(ctx.old_page, path[:-1])['name'])
    if person is None or person.name != holder['name']:
        named = [p for p in ctx.registry.people.values() if p.name == holder['name']]
        person = named[0] if len(named) == 1 else None
    if person is None or ctx.registry.organisation_of(person.id, year) != new:
        return UNEXPLAINED
    cell = [ctx.canonical(o) for o in legacy_community.split(old)]
    stated = [o for o in cell if o not in (UNMAPPED, new)]
    if not stated:
        return 'unmapped-cell'
    if not all(ctx.has_proposal(person.id, o, year) for o in stated):
        return UNEXPLAINED
    return 'positional-fix' if len(cell) > 1 else 'deferred'


def classify_role_count(ctx, path, old, new):
    """The roles of an organisation in a year: the old records, credited the old way, give the old count; credited
    the new way they must give the new count, and every record whose credit changed has an allowed cause."""
    if ctx.old_root is None:
        return UNEXPLAINED
    name, year = ctx.old_page['organisations'][path[1]]['name'], int(path[3])
    credits = ctx.credits(year)
    if sum(c.old.count(name) for c in credits) != old or sum(c.new.count(name) for c in credits) != new:
        return UNEXPLAINED
    return joined(c.cause for c in credits if c.cause and (name in c.old or name in c.new))


def old_is_organisation(name):
    """The old page's test for an organisation: not Unmapped, not the volunteers, not an independent person."""
    return name not in ('', UNMAPPED, 'Plone Foundation (community volunteer)') and not name.endswith('(independent)')


def code_organisations(text):
    """The organisations with commits or pull requests in an organisation statistics file."""
    return {row['organisation'] for row in csv.DictReader(io.StringIO(text))
            if int(row['total_commits']) or int(row['total_pull_requests'])}


def classify_headline_organisations(ctx, path, old, new):
    """The number of organisations active in the year or the five years: the old records and events give the old
    set; credited the new way, with the new events, they must give the new set. The organisations that left or
    joined are explained by the causes of the records that credited them."""
    if ctx.old_root is None:
        return UNEXPLAINED
    year = ctx.old_page['year']
    years = [year] if path[1] == 'year' else ctx.old_page['years']
    old_set, new_set, causes = set(), set(), {}
    for y in years:
        code_file = paths.organisation_contributors_file(y).as_posix()
        old_events = legacy_community.events(y, ctx.old_root / paths.COMMUNITY)
        new_events = events(y, ctx.root / paths.COMMUNITY)
        old_set |= code_organisations(ctx.old_text(code_file))
        new_set |= code_organisations(ctx.new_text(code_file))
        old_set |= {ctx.canonical(o) for e in old_events for o in e.organisations}
        new_set |= {ctx.registry.organisation_name(o) for e in new_events for o in e.organisations}
        for credit in ctx.credits(y):
            old_set |= set(credit.old)
            new_set |= set(credit.new)
            for organisation in set(credit.old) ^ set(credit.new):
                causes.setdefault(organisation, set()).add(credit.cause or UNEXPLAINED)
    old_set = {o for o in old_set if old_is_organisation(o)}
    new_set = {o for o in new_set if ctx.registry.is_counted_organisation(o)}
    if len(old_set) != old or len(new_set) != new:
        return UNEXPLAINED
    return joined(cause for o in old_set ^ new_set for cause in causes.get(o, {UNEXPLAINED}))


# The audit


def classify_file(ctx, file, lines):
    if file == PAGE:
        return classify_page(ctx, file, lines)
    if RECOGNITION_CSV.match(file):
        return classify_recognition_csv(ctx, file, lines)
    if file == RECOGNITION_MD:
        return classify_recognition_markdown(ctx, file, lines)
    return classify_plain(ctx, file, lines, [classify_timestamp, classify_person_rename, classify_display_name])


def audit(root=Path('.'), base='main'):
    """[(file, class, line excerpt)] of every line that differs in derived/ and reports/ from the committed one.

    `base` is the revision whose curated files the committed outputs were made from (its merge base with HEAD is
    used); without it, the rules that compare with the old community files find nothing.
    """
    root = Path(root)
    try:
        base = git(root, 'merge-base', 'HEAD', base).strip() if base else None
    except subprocess.CalledProcessError:
        base = None
    ctx = Context(root, base)
    found = []
    try:
        files = changed_files(root)
        # The recognition CSV first: its result decides the summary lines of the markdown report
        for file in sorted(files, key=lambda f: (not RECOGNITION_CSV.match(f), f)):
            lines = []
            for removed, added in hunks(root, file):
                pair_by_position(removed, added)
                lines.extend([*removed, *added])
            if file.endswith('.csv'):
                for line in lines:
                    line.counterpart = None
                pair_by_first_cell(lines)
            found.extend(classify_file(ctx, file, lines))
    finally:
        ctx.close()
    return found


def summary(found):
    """The audit as text: a table of the classes and their counts, then every unexplained line."""
    counts = Counter(kind for _, kind, _ in found)
    width = max([len(kind) for kind in counts] + [len('class')])
    lines = [f'{"class":<{width}}  lines', f'{"-" * width}  -----']
    lines += [f'{kind:<{width}}  {counts[kind]:>5}' for kind in sorted(counts, key=lambda k: (k == UNEXPLAINED, k))]
    unexplained = [(file, excerpt) for file, kind, excerpt in found if kind == UNEXPLAINED]
    if unexplained:
        lines += ['', 'Unexplained:'] + [f'{file}: {excerpt}' for file, excerpt in unexplained]
    return '\n'.join(lines) + '\n'
