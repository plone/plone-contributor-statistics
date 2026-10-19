"""The audit of the regenerated outputs after the migration (#139).

`git diff` shows what the regeneration changed in derived/ and reports/. The specification allows few causes:
code attribution must not change at all; community credit changes only for the rows the migration deferred to
affiliation_proposals.csv and for organiser roles; every other difference must be explained by a defect named in
the analysis (#139, Part 1). The audit gives every changed line one class, the cause it can prove:

- person-rename: a person without a GitHub login, once named, is now the username `person:<id>`.
- deferred: credit that a community row stated and the migration deferred to a proposal, and every number that
  follows from it, recomputed: the points, total and level of the organisation, its rank, the report's sums.
- organiser-role: a sprint or conference organiser's role counts for the person's organisation now, no longer
  for the organising entity.
- positional-fix: a row whose organisations were not one per person credited each organisation once per person.
- unmapped-cell: a row whose organisation cell said Unmapped (or nothing) counts for the organisation that the
  old mapping already gave for the year: the cell was a copy older than the mapping.
- no-host-podcast: a podcast series without a named host credited the organisation of its row; the podcasts
  schema has one row per host and no organisation column, so the migration moved the organisation to the notes
  and the series credits no one. Not a cause the specification names: a reviewer must accept it.
- key-shape: the community page names people by person id, not by `name:` key or lower-case login.
- display-name: a person or an organisation is shown by the name of the register, not by the spelling of the row.
- source-cut: a Source cell lost the notes on people's organisations, which the affiliations hold now.
- reordered: the line's record is unchanged on the other side; only its position (or rank) moved.
- wording: a sentence of a report that the report's code reworded; it holds no number.
- timestamp: the generation time stamp, which the reproducibility test ignores too.
- unexplained: anything else.

A line is unexplained unless a rule proves its class; the rules are deliberately narrow. Numbers are never
accepted for belonging to an organisation the audit knows as deferred: they are recomputed.
"""

import contextlib
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
from scripts.report.generate_community_recognition_report import get_recognition_level, load_recognition_levels
from scripts.tools.migrate_data import legacy_community, legacy_mappings
from scripts.tools.migrate_data.community import NOTES, first_link
from scripts.tools.migrate_data.community import read_rows as read_old_rows
from scripts.tools.migrate_data.legacy_people import is_group

CLASSES = ('person-rename', 'deferred', 'organiser-role', 'positional-fix', 'unmapped-cell', 'no-host-podcast',
           'key-shape', 'display-name', 'source-cut', 'reordered', 'wording', 'timestamp', 'unexplained')
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
# The point categories of the recognition, in the order of its CSV and report
CATEGORIES = ('Strategic Sprint', 'Release Manager', 'Team Leader', 'Board Member', 'Podcast Host', 'WPD Event',
              'WPD Talk', 'Conference Organization', 'Training Session', 'PR Contributions', 'PLIP Contributions')


def rounded(value):
    return round(value, 4)


@dataclass
class Line:
    """A changed line: `-` from the old revision, `+` from the new one, and its counterpart, if paired."""

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


def default_from(base):
    """The base (the merge base with the branch the migration started from): its outputs are those the old code
    made from the old curated files, so the audit replays every output change of the migration branch. Without a
    base, HEAD: a fresh regeneration is compared with the committed outputs."""
    return base or 'HEAD'


def hunks(diff):
    """[(removed lines, added lines)] of the hunks of a `git diff -U0` of one file."""
    found = []
    for text in diff.splitlines():
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

    for line in lines:
        line.counterpart = None
    counts = Counter((line.sign, first_cell(line)) for line in lines)
    pairs = {}
    for line in lines:
        key = first_cell(line)
        if counts[('-', key)] == 1 and counts[('+', key)] == 1:
            pairs.setdefault(key, {})[line.sign] = line
    for pair in pairs.values():
        pair['-'].counterpart, pair['+'].counterpart = pair['+'], pair['-']


def json_lines(value):
    """[(path, line)] of `json.dump(value, indent=1, sort_keys=True, ensure_ascii=False)`, one per line.

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


def extract(root, revision, folder):
    """A temporary folder with `folder` of the revision, as `git archive` gives it."""
    temporary = tempfile.TemporaryDirectory(prefix='audit-')
    archive = subprocess.run(['git', 'archive', '--format=tar', revision, folder], cwd=root, capture_output=True,
                             check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(temporary.name, filter='data')
    return temporary


class Context:
    """What the rules need to know, read once.

    The outputs are compared between the revisions `from_rev` and `to_rev` (None: the work tree); the registers,
    proposals and community files are those of `to_rev`. `base` is the revision whose curated files the old
    outputs were made from, the old community files and the old mapping.
    """

    def __init__(self, root, base, from_rev='HEAD', to_rev=None):
        self.root = Path(root)
        self.base = base
        self.from_rev = from_rev
        self.to_rev = to_rev
        self._temporaries = []
        self._credits = {}
        self._people_index = {}
        self._old_mapping = {}

    def close(self):
        for temporary in self._temporaries:
            temporary.cleanup()

    def diff(self, *args):
        return git(self.root, 'diff', self.from_rev, *([self.to_rev] if self.to_rev else []), *args)

    def changed_files(self):
        """The files under derived/ and reports/ that differ between the two revisions."""
        return self.diff('--name-only', '--', 'derived', 'reports').split()

    def old_text(self, file):
        return git(self.root, 'show', f'{self.from_rev}:{file}')

    def new_text(self, file):
        if self.to_rev:
            return git(self.root, 'show', f'{self.to_rev}:{file}')
        return (self.root / file).read_text(encoding='utf-8')

    def in_report_code(self, text, revision):
        """Whether the text is a string literal of a report generator (scripts/report/) in the revision."""
        key = ('_report_code', revision)
        if key not in self.__dict__:
            if revision is None:
                sources = [p.read_text(encoding='utf-8') for p in (self.root / 'scripts/report').glob('*.py')]
            else:
                names = git(self.root, 'ls-tree', '--name-only', revision, 'scripts/report/').split()
                sources = [git(self.root, 'show', f'{revision}:{name}') for name in names if name.endswith('.py')]
            self.__dict__[key] = sources
        return any(f'"{text}"' in source or f"'{text}'" in source for source in self.__dict__[key])

    @cached_property
    def new_root(self):
        """The folder whose curated/ the new outputs were made from."""
        if self.to_rev is None:
            return self.root
        self._temporaries.append(extract(self.root, self.to_rev, 'curated'))
        return Path(self._temporaries[-1].name)

    @cached_property
    def registry(self):
        return load_registry(self.new_root / paths.MAPPINGS_DIR)

    @cached_property
    def proposals(self):
        return read_rows(self.new_root / paths.AFFILIATION_PROPOSALS)

    @cached_property
    def levels(self):
        return load_recognition_levels(self.new_root / paths.RECOGNITION_LEVELS)

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

    def logins(self, person):
        """The GitHub logins of a person, in lower case."""
        found = {person.github.casefold()} if person.github else set()
        return found | {i.value.casefold() for i in self.registry.identities if i.person == person.id
                        and i.kind == 'login'}

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
        """Whether a proposal for the organisation names the old row `file:line` as its evidence, for one of the
        people of that row."""
        org_id = self.registry.organisation_id(organisation)
        people = self.row_people(file, line)
        return any(p['organisation'] == org_id and p['evidence'].startswith(f'{file}:{line};')
                   and p['person'] in people for p in self.proposals)

    # The old curated files: community rows, what they credited, and the old mapping

    @cached_property
    def old_root(self):
        """A folder with the curated files of the base revision, or None without a base."""
        if self.base is None:
            return None
        self._temporaries.append(extract(self.root, self.base, 'curated'))
        return Path(self._temporaries[-1].name)

    @cached_property
    def old_rows(self):
        """{(file, line): old row} of the old community files."""
        return {(row.file, row.line): row for row in read_old_rows(self.old_root)} if self.old_root else {}

    def row_people(self, file, line):
        """The ids of the people of the person column of an old row (by handle where one per name, else name)."""
        old = self.old_rows.get((file, line))
        if old is None or old.kind not in legacy_community.ROLE_KINDS:
            return set()
        _, person_column, handle_column, _ = legacy_community.ROLE_KINDS[old.kind]
        names = legacy_community.split(old.row.get(person_column))
        handles = legacy_community.split(old.row.get(handle_column)) if handle_column else []
        if len(handles) != len(names):
            handles = [''] * len(names)
        people = (person_for(self, name, handle) for name, handle in zip(names, handles))
        return {person.id for person in people if person is not None}

    def relative(self, file):
        return Path(file).relative_to(self.old_root).as_posix()

    def credits(self, year):
        """[Credit] of every old community record of the year: what it credited then and what it credits now."""
        if year not in self._credits:
            records = legacy_community.community_records(year, self.old_root / paths.COMMUNITY)
            self._credits[year] = [credit_of(self, record, year) for record in records]
        return self._credits[year]

    def old_mapping_gives(self, person, year, organisation):
        """Whether the old mapping (organisations.csv and the overrides of the base) gave the person's login the
        organisation in the year."""
        if self.old_root is None:
            return False
        if year not in self._old_mapping:
            with contextlib.redirect_stdout(io.StringIO()):
                mapping = legacy_mappings.load_organisation_mapping(
                    self.old_root / legacy_mappings.OLD_ORGANISATIONS, self.old_root / legacy_mappings.OVERRIDES,
                    year)
            self._old_mapping[year] = {login.casefold(): org for login, org in mapping.items()}
        return any(self.canonical(self._old_mapping[year].get(login, UNMAPPED)) == organisation
                   for login in self.logins(person))


def person_for(ctx, name, handle=''):
    """The person of a name in an old row: by its handle, else by its name."""
    person = ctx.registry.person_for(login=handle) if handle else None
    return person or ctx.registry.person_for(name=name)


# What the old community records credited, and what they credit now


@dataclass
class Credit:
    record: object
    old: list
    new: list
    cause: str | None


def credit_of(ctx, record, year):
    """The organisations an old record credited (the old cell, split) and credits now (the person's organisation).

    A talk of a company team, without a person or with the team in the speaker column, counts for the team's
    organisation then and now; another record without a person (a group) credits no one now.
    """
    file = ctx.relative(record.file)
    row = ctx.old_rows[(file, record.line)].row
    old = [ctx.canonical(o) for o in legacy_community.split(record.organisation)]
    person = person_for(ctx, record.person, record.handle) if record.person else None
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

    Organiser roles first: they count for the person's organisation by design. A podcast without a host whose
    organisation went to the notes. A cell without an organisation, where the old mapping already gave the one
    that counts now: unmapped-cell. A row whose stated organisations all went to proposals: deferred, or
    positional-fix when the row had not one organisation per person.
    """
    if record.kind in ORGANISER_KINDS:
        return 'organiser-role'
    if record.kind == 'podcasts' and not record.person:
        return 'no-host-podcast' if podcast_organisation_in_notes(ctx, row, year) else UNEXPLAINED
    if not old:
        anchored = person is not None and len(new) == 1 and ctx.old_mapping_gives(person, year, new[0])
        return 'unmapped-cell' if anchored else UNEXPLAINED
    stated = [o for o in old if o not in new]
    if not stated:
        return UNEXPLAINED
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
               for item in items(year, 'podcasts', ctx.new_root / paths.COMMUNITY))


def joined(causes):
    """One class for a line that several credit changes explain, e.g. `deferred+organiser-role`."""
    causes = set(causes)
    if not causes or UNEXPLAINED in causes:
        return UNEXPLAINED
    return '+'.join(c for c in CLASSES if c in causes)


# The recognition: deferred organisations and what follows from their lost points


def deferred_organisations(ctx):
    """{name: {category: points lost}} of the organisations whose recognition changed only by deferred rows.

    The community page lists every contribution with its row. A contribution that only the old page has must be a
    row that a proposal for the organisation names as evidence, for one of the row's people; no contribution may
    be new, and the contributions both have must have the same points.
    """
    if '_deferred' in ctx.__dict__:
        return ctx._deferred
    found = {}
    old_orgs, new_orgs = ctx.old_page['organisations'], ctx.new_page['organisations']
    for slug in set(old_orgs) | set(new_orgs):
        old, new = old_orgs.get(slug, {}), new_orgs.get(slug, {})
        name = old.get('name') or new.get('name')
        lost, explained = {}, bool(old)
        for category in set(old.get('categories', {})) | set(new.get('categories', {})):
            before = old.get('categories', {}).get(category, {}).get('contributions', [])
            after = new.get('categories', {}).get(category, {}).get('contributions', [])
            for contribution in before:
                counterpart = contribution_counterpart(contribution, after)
                if counterpart is None:
                    lost.setdefault(category, []).append(contribution)
                    explained &= ctx.row_proposal(contribution['file'], contribution['line'], name)
                elif counterpart['points'] != contribution['points']:
                    explained = False
            explained &= all(contribution_counterpart(c, before) is not None for c in after)
        if lost and explained:
            found[name] = lost
    ctx._deferred = found
    return found


def lost_points(ctx, name):
    """{category: points} that a deferred organisation lost."""
    return {category: sum(c['points'] for c in lost) for category, lost in deferred_organisations(ctx)[name].items()}


def contribution_counterpart(contribution, others):
    """The contribution of the same row on the other side, or None."""
    same = [c for c in others if (c['file'], c['line']) == (contribution['file'], contribution['line'])]
    return same[0] if len(same) == 1 else None


def expected_organisation(ctx, slug):
    """The page entry of a deferred organisation recomputed from the old one minus the lost points: its category
    points, total, level, next level and points to it; None when nothing is left (it drops out)."""
    old = ctx.old_page['organisations'][slug]
    lost = lost_points(ctx, old['name'])
    categories = {category: rounded(value['points'] - lost.get(category, 0))
                  for category, value in old['categories'].items()}
    categories = {category: points for category, points in categories.items() if points > 0}
    total = rounded(sum(categories.values()))
    level = get_recognition_level(total, ctx.levels)
    if level == 'No Level':
        return None
    higher = [lvl for lvl in ctx.levels if lvl['min_points'] > total]
    next_level = min(higher, key=lambda lvl: lvl['min_points']) if higher else None
    return {'categories': categories, 'points': total, 'level': level,
            'next_level': next_level['name'] if next_level else None,
            'points_to_next': rounded(next_level['min_points'] - total) if next_level else None}


@dataclass
class Recognition:
    """The two recognition CSVs: their rows by organisation, in file order."""

    header: list
    old: dict
    new: dict


def recognition(ctx):
    """The recognition CSVs of the page's year, or None when they are missing."""
    if '_recognition' not in ctx.__dict__:
        file = f'{paths.RECOGNITION_REPORT_DIR.as_posix()}/{ctx.new_page["year"]}-community-recognition-report.csv'
        try:
            old, new = (list(csv.DictReader(io.StringIO(text))) for text in (ctx.old_text(file), ctx.new_text(file)))
        except (subprocess.CalledProcessError, FileNotFoundError):
            ctx._recognition = None
        else:
            header = csv_cells(ctx.new_text(file).splitlines()[0])
            ctx._recognition = Recognition(header, {r['Organisation']: r for r in old},
                                           {r['Organisation']: r for r in new})
    return ctx._recognition


def recognition_row_deferred(ctx, name):
    """Whether the recognition row of an organisation is its old row minus the deferred points: each category,
    the total and the level recomputed; no row when nothing is left."""
    rows = recognition(ctx)
    if rows is None or name not in deferred_organisations(ctx) or name not in rows.old:
        return False
    old, new = rows.old[name], rows.new.get(name)
    lost = lost_points(ctx, name)
    expected = {category: rounded(float(old[category]) - lost.get(category, 0)) for category in CATEGORIES}
    total = rounded(float(old['Total Points']) - sum(lost.values()))
    if any(points < 0 for points in expected.values()) or total != rounded(sum(expected.values())):
        return False
    if total <= 0:
        return new is None
    return (new is not None and all(rounded(float(new[c])) == expected[c] for c in CATEGORIES)
            and rounded(float(new['Total Points'])) == total
            and new['Recognition Level'] == get_recognition_level(total, ctx.levels))


def recognition_changes_deferred(ctx):
    """Whether every row that differs between the recognition CSVs is a deferred row."""
    rows = recognition(ctx)
    if rows is None:
        return False
    changed = {name for name in set(rows.old) | set(rows.new) if rows.old.get(name) != rows.new.get(name)}
    return all(recognition_row_deferred(ctx, name) for name in changed)


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
    """display-name: the line equals its counterpart once every spelling of a person in the old line is
    replaced by the person's display name."""
    old, new = (line, line.counterpart) if line.sign == '-' else (line.counterpart, line)
    if old is None or old.text == new.text:
        return None
    return 'display-name' if ctx.with_display_names(old.text) == new.text else None


def classify_wording(ctx, line):
    """wording: a sentence of a report generator that the code reworded. Neither line holds a digit, the old line
    is a string in scripts/report/ of the old revision and the new line one of the new revision."""
    old, new = (line, line.counterpart) if line.sign == '-' else (line.counterpart, line)
    if old is None or re.search(r'\d', old.text + new.text) or not old.text.strip() or not new.text.strip():
        return None
    return 'wording' if ctx.in_report_code(old.text, ctx.from_rev) and ctx.in_report_code(new.text, ctx.to_rev) \
        else None


def classify_plain(ctx, file, lines, rules):
    return [(file, next((c for c in (rule(ctx, line) for rule in rules) if c), UNEXPLAINED), line.excerpt())
            for line in lines]


def classify_recognition_csv(ctx, file, lines):
    """deferred: a recognition row that is its old row minus the deferred points (see recognition_row_deferred)."""
    found = []
    for line in lines:
        cells = csv_cells(line.text)
        deferred = bool(cells) and recognition_row_deferred(ctx, cells[0])
        found.append((file, 'deferred' if deferred else UNEXPLAINED, line.excerpt()))
    return found


# The markdown report of the recognition


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


def organisation_sections(text, sections):
    """{organisation: [lines]} of the sections of the Detailed Breakdown."""
    found = {}
    for text_line, (h2, h3) in zip(text.splitlines(), sections):
        if h2 == 'Detailed Breakdown by Organization' and h3:
            found.setdefault(h3, []).append(text_line)
    return found


def summary_lines(rows, levels):
    """The lines of the Executive Summary, Recognition Levels and Statistics by Category that the rows of a
    recognition CSV give, as the report writes them."""
    totals = [float(row['Total Points']) for row in rows]
    lines = {f'- **Total Organizations**: {len(rows)}', f'- **Total Points Awarded**: {sum(totals):.1f}'}
    if rows:
        lines.add(f'- **Average Points per Organization**: {sum(totals) / len(rows):.1f}')
    counts = Counter(row['Recognition Level'] for row in rows)
    for level in levels:
        points_range = (f"{level['min_points']}+" if level['max_points'] == float('inf')
                        else f"{level['min_points']}-{level['max_points']}")
        lines.add(f"| {level['name']} | {points_range} | {counts.get(level['name'], 0)} |")
    for category in CATEGORIES:
        values = [float(row[category]) for row in rows if float(row[category]) > 0]
        lines.add(f'| {category} | {len(values)} | {sum(values):.1f} |')
    return lines


def leaderboard_lines(rows):
    """The leaderboard rows that a recognition CSV gives: rank by file order, which is by total."""
    return {f"| {rank} | {row['Organisation']} | {row['Recognition Level']} | {float(row['Total Points']):.1f} |"
            for rank, row in enumerate(rows, 1)}


CATEGORY_ROW = re.compile(r'^\| (.+?) \| ([\d.]+) \| (.*) \|$')


def expected_section(ctx, name, old_lines):
    """The new section of an organisation: the old one with the display names of the register, its total from
    the new CSV and, for a deferred organisation, each category that lost points with its new points and without
    the titles of the lost rows; None when a lost title is not in the old section."""
    rows = recognition(ctx)
    new = rows.new.get(name)
    lost = deferred_organisations(ctx).get(name, {})
    found = []
    for text in old_lines:
        text = ctx.with_display_names(text)
        match = CATEGORY_ROW.match(text)
        if text.startswith('**Total Points:'):
            text = f"**Total Points: {float(new['Total Points']):.1f}**"
        elif match and match.group(1) in lost:
            items_ = match.group(3).split('<br>')
            for contribution in lost[match.group(1)]:
                title = f"• {ctx.with_display_names(contribution['text'])}"
                if title not in items_:
                    return None
                items_.remove(title)
            points = float(new[match.group(1)])
            if points <= 0:
                continue
            text = f"| {match.group(1)} | {points:.1f} | {'<br>'.join(items_) or '—'} |"
        found.append(text)
    return found


def classify_recognition_markdown(ctx, file, lines):
    """The lines of the recognition report, by the section they are in, recomputed from the two CSVs.

    - the summaries (Executive Summary, Recognition Levels, Statistics by Category): the line is what that side's
      CSV gives, and every changed CSV row is deferred: deferred.
    - the leaderboard: the line is what that side's CSV gives (rank, level, points); deferred for a deferred
      organisation, reordered for one whose row is unchanged.
    - an organisation's section: the new section is the old one recomputed (expected_section); deferred for a
      deferred organisation, else reordered for an unchanged line and display-name for a changed one. The section
      of an organisation that dropped out is deferred when its CSV row is.
    - timestamp and display-name elsewhere.
    """
    rows = recognition(ctx)
    texts = {'-': ctx.old_text(file), '+': ctx.new_text(file)}
    sections = {sign: markdown_sections(text) for sign, text in texts.items()}
    blocks = {sign: organisation_sections(texts[sign], sections[sign]) for sign in texts}
    sides = {'-': list(rows.old.values()), '+': list(rows.new.values())} if rows else None
    summaries = ('Executive Summary', 'Recognition Levels', 'Statistics by Category')
    deferred = deferred_organisations(ctx)

    def section_class(name, line):
        if name in deferred:
            if not recognition_row_deferred(ctx, name):
                return UNEXPLAINED
            if name not in blocks['+']:
                return 'deferred' if name not in rows.new else UNEXPLAINED
            return 'deferred' if expected_section(ctx, name, blocks['-'].get(name, [])) == blocks['+'][name] \
                else UNEXPLAINED
        if name not in blocks['-'] or name not in blocks['+'] or rows.old.get(name) != rows.new.get(name):
            return UNEXPLAINED
        if expected_section(ctx, name, blocks['-'][name]) != blocks['+'][name]:
            return UNEXPLAINED
        return 'reordered' if line.text in blocks['-'][name] and line.text in blocks['+'][name] else 'display-name'

    def kind(line):
        h2, h3 = sections[line.sign][line.number - 1]
        if classify_timestamp(ctx, line):
            return 'timestamp'
        if sides is None:
            return classify_display_name(ctx, line) or UNEXPLAINED
        if h2 in summaries and h3 is None and line.text.strip():
            fits = line.text in summary_lines(sides[line.sign], ctx.levels)
            return 'deferred' if fits and recognition_changes_deferred(ctx) else UNEXPLAINED
        if h2 == 'Recognition Leaderboard' and line.text.startswith('| ') and line.text[2:3].isdigit():
            name = line.text.split(' | ')[1]
            if line.text not in leaderboard_lines(sides[line.sign]):
                return UNEXPLAINED
            if name in deferred:
                return 'deferred' if recognition_row_deferred(ctx, name) else UNEXPLAINED
            return 'reordered' if rows.old.get(name) == rows.new.get(name) else UNEXPLAINED
        if h2 == 'Detailed Breakdown by Organization' and h3:
            return section_class(h3, line)
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
    try:
        if path[:1] == ('people',) and len(path) >= 3:
            year = path[1]
            key = value_at(this, path[:3])['id']
            index = ctx.people_index(year)['+' if side == '-' else '-'].get(ctx.page_key(key) if side == '-' else key)
            return None if index is None else ('people', year, index, *path[3:])
        if path[:1] == ('organisations',) and len(path) >= 6 and path[4] == 'contributions':
            contribution = value_at(this, path[:6])
            others = value_at(that, path[:5])
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
        value_at(that, path)
        return path
    except KeyError:
        return None


def values(ctx, side, path):
    """(old value, new value, old path) of a line's path and its counterpart; None when there is no counterpart."""
    counterpart = page_counterpart(ctx, side, path)
    if counterpart is None:
        return None
    try:
        this = value_at(ctx.old_page if side == '-' else ctx.new_page, path)
        that = value_at(ctx.new_page if side == '-' else ctx.old_page, counterpart)
    except KeyError:
        return None
    return (this, that, path) if side == '-' else (that, this, counterpart)


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
        return classify_organisation_line(ctx, side, path)
    if section == 'wall' and len(path) >= 4:
        return classify_wall_line(ctx, side, path)
    found = values(ctx, side, path)
    if found is None:
        return UNEXPLAINED
    old, new, old_path = found
    if isinstance(old, (dict, list)) or old == new:
        return 'reordered'
    return classify_page_value(ctx, old_path, old, new)


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


def classify_organisation_line(ctx, side, path):
    """A line of an organisation entry of the page.

    Its history has its own rules. For a deferred organisation, every number is recomputed (expected_organisation)
    and must be the new value; a category or contribution that only the old page has must be a lost one. An
    organisation of the old page only must be deferred and have nothing left. Other values must be equal, or
    differ in a display name or a cut source.
    """
    slug = path[1]
    page = ctx.old_page if side == '-' else ctx.new_page
    name = page['organisations'][slug]['name']
    present = slug in ctx.old_page['organisations'] and slug in ctx.new_page['organisations']
    deferred = name in deferred_organisations(ctx)
    expected = expected_organisation(ctx, slug) if deferred and slug in ctx.old_page['organisations'] else None
    if path[2:3] == ('history',):
        return classify_organisation_history(ctx, side, path, name, present, deferred and expected is None)
    if not present:
        return 'deferred' if side == '-' and deferred and expected is None else UNEXPLAINED
    if len(path) == 3 and path[2] in ('points', 'level', 'next_level', 'points_to_next'):
        found = values(ctx, side, path)
        if found is None:
            return UNEXPLAINED
        old, new, _ = found
        if old == new:
            return 'reordered'
        return 'deferred' if deferred and expected is not None and new == expected[path[2]] else UNEXPLAINED
    if len(path) >= 4 and path[2] == 'categories':
        category = path[3]
        if category not in ctx.new_page['organisations'][slug]['categories']:
            dropped = side == '-' and deferred and expected is not None and category not in expected['categories']
            return 'deferred' if dropped else UNEXPLAINED
        if category not in ctx.old_page['organisations'][slug]['categories']:
            return UNEXPLAINED
        if path[4:] == ('points',):
            found = values(ctx, side, path)
            if found is None:
                return UNEXPLAINED
            old, new, _ = found
            if old == new:
                return 'reordered'
            fits = deferred and expected is not None and expected['categories'].get(category) == new
            return 'deferred' if fits else UNEXPLAINED
        if len(path) >= 6:  # a contribution
            found = values(ctx, side, path[:6])
            if found is None:
                lost = deferred and side == '-' and value_at(ctx.old_page, path[:6]) in \
                    deferred_organisations(ctx)[name].get(category, [])
                return 'deferred' if lost else UNEXPLAINED
    found = values(ctx, side, path)
    if found is None:
        return UNEXPLAINED
    old, new, old_path = found
    if isinstance(old, (dict, list)) or old == new:
        return 'reordered'
    return classify_page_value(ctx, old_path, old, new)


def classify_organisation_history(ctx, side, path, name, present, dropped):
    """The yearly counts of an organisation. On both pages: equal, or a role count that recomputes (see
    classify_role_count). Of an organisation that dropped out (deferred, nothing left): every count must still be
    what the new data gives, commits and pull requests from the new organisation statistics, events from the new
    events, roles from the old records."""
    if present:
        found = values(ctx, side, path)
        if found is None:
            return UNEXPLAINED
        old, new, old_path = found
        if isinstance(old, (dict, list)) or old == new:
            return 'reordered'
        return classify_role_count(ctx, old_path, old, new) if path[-1] == 'roles' else UNEXPLAINED
    if side != '-' or not dropped:
        return UNEXPLAINED
    if len(path) < 5:
        return 'deferred'
    year, field = int(path[3]), path[4]
    value = value_at(ctx.old_page, path)
    if field in ('commits', 'pull_requests'):
        code = code_work(ctx.new_text(paths.organisation_contributors_file(year).as_posix())).get(name, (0, 0))
        return 'deferred' if value == code[0 if field == 'commits' else 1] else UNEXPLAINED
    if field == 'events':
        count = sum(ctx.registry.organisation_name(o) == name for e in events(year, ctx.new_root / paths.COMMUNITY)
                    for o in e.organisations)
        return 'deferred' if value == count else UNEXPLAINED
    if field == 'roles' and ctx.old_root is not None:
        credits = ctx.credits(year)
        if sum(c.old.count(name) for c in credits) != value:
            return UNEXPLAINED
        causes = [c.cause for c in credits if c.cause and (name in c.old or name in c.new)]
        return joined(causes) if causes else 'deferred'
    return UNEXPLAINED


def classify_wall_line(ctx, side, path):
    """A line of the wall of organisations by level. An entry of an organisation that is not deferred must be
    equal on the other side, in the same level (reordered). A new entry of a deferred organisation must have its
    recomputed points, in its recomputed level; an old one must be the old page's points and level."""
    page = ctx.old_page if side == '-' else ctx.new_page
    entry = value_at(page, path[:4])
    level = page['wall'][path[1]]['level']
    name = entry['name']
    if name not in deferred_organisations(ctx) or entry['slug'] not in ctx.old_page['organisations']:
        found = values(ctx, side, path)
        return 'reordered' if found is not None and found[0] == found[1] else UNEXPLAINED
    expected = expected_organisation(ctx, entry['slug'])
    new_entries = [(w['level'], o['points']) for w in ctx.new_page['wall'] for o in w['organisations']
                   if o['name'] == name]
    if not new_entries == ([] if expected is None else [(expected['level'], expected['points'])]):
        return UNEXPLAINED
    if side == '-':
        old = ctx.old_page['organisations'][entry['slug']]
        if (level, entry['points']) != (old['level'], old['points']):
            return UNEXPLAINED
    return 'deferred'


def classify_page_value(ctx, old_path, old, new):
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

    display-name when the cell named that organisation in another spelling; unmapped-cell when the cell said
    Unmapped and the old mapping already gave the organisation; deferred when every organisation the cell stated
    that is not the one the affiliations give is a proposal for the person and year, positional-fix when the cell
    stated several organisations for the one person, which the old page credited each.
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
    if cell == [new]:
        return 'display-name'
    stated = [o for o in cell if o not in (UNMAPPED, new)]
    if not stated:
        return 'unmapped-cell' if new != UNMAPPED and ctx.old_mapping_gives(person, year, new) else UNEXPLAINED
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


def code_work(text):
    """{organisation: (commits, pull requests)} of an organisation statistics file."""
    return {row['organisation']: (int(row['total_commits']), int(row['total_pull_requests']))
            for row in csv.DictReader(io.StringIO(text))}


def code_organisations(text):
    """The organisations with commits or pull requests in an organisation statistics file."""
    return {name for name, (commits, pulls) in code_work(text).items() if commits or pulls}


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
        new_events = events(y, ctx.new_root / paths.COMMUNITY)
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
    return classify_plain(ctx, file, lines, [classify_timestamp, classify_person_rename, classify_display_name,
                                             classify_wording])


def audit(root=Path('.'), base='main', from_rev=None, to_rev=None):
    """[(file, class, line excerpt)] of every line that differs in derived/ and reports/ between two revisions.

    `from_rev` defaults to default_from(base), `to_rev` to the work tree. `base` is the branch whose curated files
    the old outputs were made from; its merge base with HEAD is used. Without it, the rules that compare with the
    old community files and the old mapping find nothing.
    """
    root = Path(root)
    try:
        base = git(root, 'merge-base', 'HEAD', base).strip() if base else None
    except subprocess.CalledProcessError:
        base = None
    ctx = Context(root, base, from_rev or default_from(base), to_rev)
    found = []
    try:
        for file in sorted(ctx.changed_files()):
            lines = []
            for removed, added in hunks(ctx.diff('-U0', '--', file)):
                pair_by_position(removed, added)
                lines.extend([*removed, *added])
            if file.endswith('.csv'):
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
