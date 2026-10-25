#!/usr/bin/env python3
"""Turn notes of the registers into data (plan 5, from notes to data); archived once the migration has run.

`fills`: the attribution engine computes the bridged years (rule 5 of docs/explanation/attribution.md), so the
`stated` rows that only wrote them down go. A fill row is a stated row whose notes say `between records of <A> and
<B> of the same organisation`. Its records are the nearest stated rows of the same person and organisation before
and after it that are no fill rows themselves (the years in the notes may be out of date: rows were added since).
The row goes when both records exist and, as rule 5 asks, no stated row of another organisation and no denied row
of the organisation covers a year between them; otherwise it stays and is listed. Nothing is lost: a citation of
the row is dropped when one of the records cites its source already, with the same snippet (any snippet when the
citation has none) and notes that contain the citation's notes; every other one moves, with its snippet and notes,
to the nearer record (the later one when both are as near). The row's notes are appended to that record's notes
as `bridged <from>-<to>: <notes>`.

`svn`: an identity whose notes say `SVN user <name>` (or `SVN user is this login`: the login of the address, or
the name itself) records that the person committed to Subversion as that user. Each distinct (person, SVN user)
becomes an identity of kind `svn`, citing the source of the first identity it was found on, with the clause of the
notes that names it as its notes. Its snippet is the `Author:` line of the excerpt of that source when the line
names the user, else empty. An SVN user is one person's: a user that two people's notes name is an error, and
nothing is written.

`conflicts`: an affiliation whose notes say `not applied, the verified row stands: <record>` or `Kept, not
deciding: <record>; <record>` names records of another organisation that a review kept out; a record is a quote
(optional), a label and an address. Each becomes a proposed `stated` row of the organisation it names (by name or
alias in the quote, else the label; by the first word of a name or, for a freelancer, the person's independent
organisation only as a candidate to check), for the years its label names (else the year of its source), with the
record as its notes, citing the source of the address with the quote as snippet when the excerpt holds it. A
name found by its first word is noted as an abbreviation on the citation. The dry run lists, per person and year,
the organisation and rule today and with the proposed rows, and the conflicts.
--write adds the rows and their citations, and appends `the record is row <id>` to the notes of the
row that named the record; a record without a source in the register stops it.

Without --write, it prints every change it would make. A second run changes nothing.

    python -m scripts.tools.migrate_notes fills [--write]
    python -m scripts.tools.migrate_notes svn [--write]
    python -m scripts.tools.migrate_notes conflicts [--write]
"""

import argparse
import dataclasses
import re
import sys
from datetime import date

from scripts.lib.model import (UNMAPPED, Affiliation, Citation, Identity, affiliation_id, is_uncaptured,
                               load_affiliations, load_citations, load_identities, load_registry, normalize_url,
                               read_excerpt, source_id, split_archive_url, write_affiliations, write_citations,
                               write_identities)
from scripts.lib.model.attribution import DENIED, STATED
from scripts.lib.model.names import fold
from scripts.lib.model.registers import MIN_DOMAIN_KEY

# Not after `bridged <from>-<to>: `: that is the notes of a fill row kept on its record
FILL = re.compile(r'(?<!bridged \d{4}-\d{4}: )between records of (\d{4}) and (\d{4}) of the same organisation')


@dataclasses.dataclass(frozen=True)
class Fill:
    row: object  # the fill row (Affiliation)
    left: object = None  # the record before it, or None
    right: object = None  # the record after it, or None
    target: object = None  # the nearer record, which takes the notes and the citations, when the row goes
    moved: tuple = ()  # the citations of the row that move to the target
    on_neighbour: tuple = ()  # the citations of the row that a record cites already
    reason: str = None  # why the row stays; None when it goes


@dataclasses.dataclass(frozen=True)
class FillPlan:
    removed: list
    kept: list


def is_fill(affiliation):
    """Whether the affiliation is a stated row that writes down a bridge between two records."""
    return affiliation.status == STATED and bool(FILL.search(affiliation.notes or ''))


def _years(affiliation):
    return f'{affiliation.from_year}-{"" if affiliation.to_year is None else affiliation.to_year}'


def _breaker(affiliations, row, first, last):
    """Why the years from first to last don't bridge for the organisation of the row, or None."""
    for other in affiliations:
        if other.person != row.person or not (other.from_year <= last and (other.to_year is None
                                                                           or first <= other.to_year)):
            continue
        covered = max(first, other.from_year)
        if other.status == STATED and other.organisation != row.organisation:
            return f'a stated row of {other.organisation} covers {covered}'
        if other.status == DENIED and other.organisation == row.organisation:
            return f'a denied row of {other.organisation} covers {covered}'
    return None


def _cited_already(citation, others):
    """Whether one of the other citations says all that the citation says: its source, its snippet (any snippet
    when it has none) and its notes."""
    return any(other.source == citation.source and (not citation.snippet or citation.snippet == other.snippet)
               and (citation.notes or '') in (other.notes or '') for other in others)


def plan_fills(affiliations, citations):
    """Which fill rows go, where their notes and citations go, and which rows stay and why."""
    fill_ids = {affiliation.id for affiliation in affiliations if is_fill(affiliation)}
    cited = {}
    for citation in citations:
        cited.setdefault(citation.affiliation, []).append(citation)
    removed, kept = [], []
    for row in affiliations:
        if row.id not in fill_ids:
            continue
        records = [other for other in affiliations
                   if (other.person, other.organisation, other.status) == (row.person, row.organisation, STATED)
                   and other.id not in fill_ids]
        left = max((other for other in records if other.to_year is not None and other.to_year < row.from_year),
                   key=lambda other: other.to_year, default=None)
        right = None
        if row.to_year is not None:
            right = min((other for other in records if other.from_year > row.to_year),
                        key=lambda other: other.from_year, default=None)
        if left is None or right is None:
            where = f'before {row.from_year}' if left is None else (
                f'after {row.to_year}' if row.to_year is not None else 'after it: it is open-ended')
            kept.append(Fill(row, left, right, reason=f'no record of {row.organisation} {where}'))
            continue
        reason = _breaker(affiliations, row, left.to_year + 1, right.from_year - 1)
        if reason:
            kept.append(Fill(row, left, right, reason=reason))
            continue
        target = left if row.from_year - left.to_year < right.from_year - row.to_year else right
        there = [citation for record in (left, right) for citation in cited.get(record.id, [])]
        own = cited.get(row.id, [])
        moved = tuple(c for c in own if not _cited_already(c, there))
        on_neighbour = tuple(c for c in own if _cited_already(c, there))
        removed.append(Fill(row, left, right, target, moved, on_neighbour))
    return FillPlan(removed, kept)


def _citation_key(citation):
    return (citation.affiliation, citation.source, citation.snippet or '')


def apply_fills(affiliations, citations, plan):
    """(affiliations, citations) without the removed fill rows, with their notes and citations on the records."""
    if not plan.removed:
        return affiliations, citations
    gone = {fill.row.id for fill in plan.removed}
    notes = {}
    for fill in sorted(plan.removed, key=lambda fill: fill.row.from_year):
        notes.setdefault(fill.target.id, []).append(f'bridged {_years(fill.row)}: {fill.row.notes}')
    new_affiliations = []
    for affiliation in affiliations:
        if affiliation.id in gone:
            continue
        if affiliation.id in notes:
            parts = ([affiliation.notes] if affiliation.notes else []) + notes[affiliation.id]
            affiliation = dataclasses.replace(affiliation, notes='; '.join(parts))
        new_affiliations.append(affiliation)
    moved = [dataclasses.replace(citation, affiliation=fill.target.id)
             for fill in plan.removed for citation in fill.moved]
    new_citations = [citation for citation in citations if citation.affiliation not in gone] + moved
    return new_affiliations, sorted(new_citations, key=_citation_key)


def fill_report(plan):
    """The lines that say what `fills` changes."""
    lines = []
    for fill in plan.removed:
        before, after = FILL.search(fill.row.notes).groups()
        stale = '' if (int(before), int(after)) == (fill.left.to_year, fill.right.from_year) else (
            f' (the notes name {before} and {after})')
        lines.append(f'remove {fill.row.id} {fill.row.person} {fill.row.organisation} {_years(fill.row)}: records '
                     f'{fill.left.id} {_years(fill.left)} and {fill.right.id} {_years(fill.right)}{stale}; '
                     f'notes -> {fill.target.id}')
        lines.extend(f'  move {c.source} -> {fill.target.id}' + (f' (snippet "{c.snippet}")' if c.snippet else '')
                     for c in fill.moved)
        lines.extend(f'  on a record already: {c.source}' for c in fill.on_neighbour)
    lines.extend(f'keep {fill.row.id} {fill.row.person} {fill.row.organisation} {_years(fill.row)}: {fill.reason}'
                 for fill in plan.kept)
    lines.append(f'fill rows: {len(plan.removed) + len(plan.kept)}, removed {len(plan.removed)}, '
                 f'kept {len(plan.kept)}, citations moved {sum(len(fill.moved) for fill in plan.removed)}')
    return lines


SVN_USER = re.compile(r'SVN user (is this login|[^\s,;:()]+)')
THIS_LOGIN = 'is this login'
SVN = 'svn'


@dataclasses.dataclass(frozen=True)
class SvnPlan:
    added: list  # the new `svn` identities
    found: dict  # {(person, SVN user): [the identities whose notes name it]}
    errors: list


def _svn_user(identity):
    """(SVN user, the clause of the notes that names it) of the identity, or None."""
    for clause in (identity.notes or '').split(';'):
        match = SVN_USER.search(clause)
        if match:
            user = match.group(1)
            if user == THIS_LOGIN:
                user = identity.value.partition('@')[0]
            return user, clause.strip()
    return None


def _author_line(text, user):
    """The `Author:` line of a commit excerpt when it names the user, else None."""
    match = re.search(rf'^Author: {re.escape(user)} <[^>\n]*>$', text or '', re.M)
    return match.group(0) if match else None


def plan_svn(identities, excerpt):
    """The `svn` identities that the notes of the identities name; excerpt(source id) is the text of a source."""
    found, clauses = {}, {}
    for identity in identities:
        if identity.kind == SVN:
            continue
        named = _svn_user(identity)
        if named is None:
            continue
        key = (identity.person, named[0])
        found.setdefault(key, []).append(identity)
        clauses.setdefault(key, [])
        if named[1] not in clauses[key]:
            clauses[key].append(named[1])
    recorded = {identity.value.casefold(): identity for identity in identities if identity.kind == SVN}
    added, errors, owner = [], [], {}
    for (person, user), rows in found.items():
        first = owner.setdefault(user.casefold(), (person, user))
        other = recorded.get(user.casefold())
        if first[0] != person or (other is not None and other.person != person):
            them = first if first[0] != person else (other.person, other.value)
            errors.append(f'the SVN user {user} of {person} is the SVN user {them[1]} of {them[0]}')
            continue
        if other is not None:
            continue
        source = rows[0].source
        added.append(Identity(person, SVN, user, source, _author_line(excerpt(source), user) if source else None,
                              '; '.join(clauses[person, user])))
    return SvnPlan(added, found, errors)


def svn_report(plan):
    """The lines that say what `svn` changes."""
    lines = []
    for identity in plan.added:
        snippet = f'snippet "{identity.snippet}"' if identity.snippet else 'no snippet'
        on = ', '.join(f'{row.kind} {row.value}' for row in plan.found[identity.person, identity.value])
        lines.append(f'add {identity.person} svn {identity.value} (source {identity.source}, {snippet}); '
                     f'found on {on}; notes: {identity.notes}')
    lines.extend(f'error: {error}' for error in plan.errors)
    lines.append(f'svn identities: {len(plan.added)} to add, {len(plan.errors)} errors')
    return lines


CONFLICT_MARKERS = ('not applied, the verified row stands: ', 'Kept, not deciding: ')
URL = re.compile(r'https?://[^\s)]+')
YEAR = re.compile(r'(?<!\d)(?:19[89]\d|20\d\d)(?!\d)')
QUOTED = re.compile(r'"(.*)",\s*([^"]*)$', re.S)
TRAILING_GROUP = re.compile(r'\s*(\([^()]*\))\s*$')
FREELANCER = re.compile(r'\b(?:freelanc\w*|self-employed)\b', re.I)
INDEPENDENT, FOUNDATION = 'independent', 'foundation'
NO_SOURCE = 'no source of the address in the register: capture it first'


@dataclasses.dataclass(frozen=True)
class Record:
    affiliation: object  # the row whose notes name the record (the verified row)
    clause: str  # the marker, the record and the attribution of the notes: the notes of the new row
    text: str  # the record as the notes cite it: quote, label and address
    quote: str | None
    label: str
    url: str


@dataclasses.dataclass(frozen=True)
class Proposal:
    record: Record
    organisation: str | None  # the organisation the record names, None when unclear
    how: str  # 'named', 'first word', 'freelancer', or why the organisation is unclear
    years: tuple | None  # (from, to)
    source: str | None
    row: object = None  # the stated row (Affiliation), None without an organisation or years
    citation: object = None  # its citation (Citation), None without a source
    check: tuple = ()  # what Jens checks before the row is written


def _split_records(text):
    """The parts of the text between `; ` outside parentheses and quotes."""
    parts, depth, quoted, start = [], 0, False, 0
    for at, char in enumerate(text):
        if char == '"':
            quoted = not quoted
        elif not quoted and char == '(':
            depth += 1
        elif not quoted and char == ')':
            depth = max(0, depth - 1)
        elif not quoted and depth == 0 and text.startswith('; ', at):
            parts.append(text[start:at])
            start = at + 2
    parts.append(text[start:])
    return parts


def records_of(affiliation):
    """The records of another organisation that the notes of the row name after `not applied, the verified row
    stands: ` or `Kept, not deciding: `: each a quote (optional), a label and an address, separated by `; `. A
    closing group without an address, such as `(Jens, #171)`, is the attribution of all of them."""
    notes, found = affiliation.notes or '', []
    for marker in CONFLICT_MARKERS:
        at = notes.find(marker)
        if at < 0:
            continue
        texts = []
        for part in _split_records(notes[at + len(marker):]):
            if not URL.search(part):
                break
            texts.append(part.strip())
        if not texts:
            continue
        attribution = ''
        group = TRAILING_GROUP.search(texts[-1])
        if group and not URL.search(group.group(1)):
            attribution = f' {group.group(1)}'
            texts[-1] = texts[-1][:group.start()]
        for text in texts:
            quoted = QUOTED.match(text)
            quote, rest = (quoted.group(1), quoted.group(2)) if quoted else (None, text)
            url = URL.findall(text)[-1].rstrip('.,;')
            label = re.sub(r'\s+', ' ', URL.sub('', rest)).replace(': )', ')').strip(' :;,')
            found.append(Record(affiliation, f'{marker}{text}{attribution}', text, quote, label, url))
    return found


def _source_of(url, sources):
    """The id of the source of the address in the register, else None."""
    original, stamp = split_archive_url(url) or (url, None)
    sid = source_id(original, stamp)
    if sid in sources:
        return sid
    key = normalize_url(url)
    return next((s.id for s in sources.values() if normalize_url(s.archive_url or s.url) == key), None)


def _named_organisations(registry, text):
    """The ids of the organisations whose name or alias the text names, or whose GitHub login it names as
    `@login`."""
    # Imported here: scripts.lib.capture imports the model
    from scripts.lib.capture.passages import find_name

    found = set()
    for organisation in registry.organisations.values():
        names = [name for name in (organisation.name, *organisation.aliases) if name]
        if any(find_name(text, name) is not None for name in names) or (
                organisation.github and re.search(rf'@{re.escape(organisation.github)}\b', text, re.I)):
            found.add(organisation.id)
    return sorted(found)


def _organisation_of(registry, record):
    """(organisation id or None, how, [what to check]) of the organisation the record names: by its name or an
    alias in the quote (else the label); else, to check, by the first word of its name, or, for a freelancer, the
    independent organisation of the person; else None and why."""
    text, person = record.quote or record.label, record.affiliation.person
    named, check = _named_organisations(registry, text), []
    if len(named) > 1:
        foundation = [org for org in named if registry.organisations[org].kind == FOUNDATION]
        if len(foundation) < len(named):
            check += [f'the record also names {registry.organisation_name(org)}' for org in foundation]
            named = [org for org in named if org not in foundation]
    if len(named) == 1:
        return named[0], 'named', check
    if named:
        return None, f'several organisations are named: {", ".join(named)}', check
    own = set(fold(registry.people[person].name).split()) if person in registry.people else set()
    words = {fold(word) for word in re.findall(r'\b[A-Z]\w+', text)} - own
    by_first_word = sorted(org.id for org in registry.organisations.values()
                           if org.kind == 'organisation' and (first := fold(org.name).split()[:1])
                           and len(first[0]) >= MIN_DOMAIN_KEY and first[0] in words)
    if len(by_first_word) == 1:
        return by_first_word[0], 'first word', check + ['check the organisation: found by the first word of its name']
    if FREELANCER.search(text):
        independent = sorted({row.organisation for row in registry.affiliations if row.person == person
                              and row.organisation in registry.organisations
                              and registry.organisations[row.organisation].kind == INDEPENDENT})
        if len(independent) == 1:
            return independent[0], 'freelancer', check + [
                'check the organisation: a freelancer, the independent organisation of the person']
    return None, 'no organisation of the register is named', check


def _cited_as(registry, record, organisation, how):
    """The record as the notes cite it; a name found by its first word is noted as an abbreviation."""
    if how != 'first word':
        return record.text
    first = fold(registry.organisation_name(organisation)).split()[0]
    word = next(word for word in re.findall(r'\b[A-Z]\w+', record.quote or record.label) if fold(word) == first)
    remark = f' ({word}: an abbreviation of {registry.organisation_name(organisation)})'
    quoted = f'"{record.quote}"'
    if record.quote and record.text.startswith(quoted):
        return quoted + remark + record.text[len(quoted):]
    return record.text + remark


def plan_conflicts(registry):
    """A proposal for each record of another organisation that the notes of a row name (`records_of`): a stated
    row of that organisation for the years the record speaks for (those its label names, else the year of the
    source's date), citing the source with the quote as snippet when the excerpt holds it."""
    from scripts.lib.capture.passages import find_quote

    sources, proposals = registry.sources, []
    for affiliation in registry.affiliations:
        for record in records_of(affiliation):
            organisation, how, check = _organisation_of(registry, record)
            sid = _source_of(record.url, sources)
            years = sorted({int(year) for year in YEAR.findall(record.label)})
            if not years and sid is not None:
                years = [sources[sid].date.year]
            years = (years[0], years[-1]) if years else None
            if sid is None:
                check.append(NO_SOURCE)
            elif is_uncaptured(sources[sid]):
                check.append('the source was never captured: no text to verify')
            snippet = None
            if record.quote and sid is not None:
                if find_quote(registry.excerpt(sid), record.quote) is not None:
                    snippet = record.quote
                elif not is_uncaptured(sources[sid]):
                    check.append('the quote is not in the excerpt of the source')
            if years is None:
                check.append('no year: neither the label nor a source names one')
            row = citation = None
            if organisation is not None and years is not None:
                row = Affiliation(affiliation_id(affiliation.person, organisation, *years), affiliation.person,
                                  organisation, years[0], years[1], STATED, None, record.clause)
                if sid is not None:
                    citation = Citation(row.id, sid, snippet, None,
                                        f'cited as: {_cited_as(registry, record, organisation, how)}')
            proposals.append(Proposal(record, organisation, how, years, sid, row, citation, tuple(check)))
    return proposals


def apply_conflicts(affiliations, citations, proposals):
    """(affiliations, citations, errors) with the proposed rows and their citations added, and the verified rows'
    notes saying where their records are now (`; the record is row <id>`). A proposal without a row or a citation
    is an error, and then nothing is added. A row recorded already is left as it is."""
    known = {affiliation.id for affiliation in affiliations}
    new = [p for p in proposals if not (p.row and p.row.id in known)]
    errors = [f'{p.record.affiliation.id}: '
              + (p.how if p.row is None else f'no source of {p.record.url} in the register: capture it first')
              for p in new if p.row is None or p.citation is None]
    if errors or not new:
        return affiliations, citations, errors
    rows_of = {}
    for p in new:
        rows_of.setdefault(p.record.affiliation.id, []).append(p.row.id)
    updated = []
    for affiliation in affiliations:
        ids = rows_of.get(affiliation.id)
        if ids:
            where = (f'the record is row {ids[0]}' if len(ids) == 1 else
                     f'the records are rows {", ".join(ids[:-1])} and {ids[-1]}')
            affiliation = dataclasses.replace(affiliation, notes=f'{affiliation.notes}; {where}')
        updated.append(affiliation)
    return updated + [p.row for p in new], list(citations) + [p.citation for p in new], []


@dataclasses.dataclass(frozen=True)
class YearResult:
    person: str
    year: int
    before: str | None  # the organisation id today
    before_rule: str
    after: str | None  # the organisation id with the proposed rows
    rule: str
    conflict: tuple  # the organisations no rule decides between, with the proposed rows
    activity: str  # what the person is credited with in the year, empty when inactive

    @property
    def changed(self):
        """Whether the year counts differently with the proposed rows, or is a conflict."""
        return self.before != self.after or bool(self.conflict)


def with_proposals(registry, proposals):
    """The registry with the proposed rows and their citations."""
    return registry.with_affiliations([p.row for p in proposals if p.row],
                                      [p.citation for p in proposals if p.citation])


def dry_run(registry, proposals, credited, until):
    """[YearResult] of every year of the people of the proposed rows, before and with them; credited is
    {(person, year): {what: count}} (attribution_changes.activity)."""
    from scripts.tools.attribution_changes import describe, person_years

    after = with_proposals(registry, proposals)
    people = {p.row.person for p in proposals if p.row}
    pairs = {pair for pair in person_years(registry, until) | person_years(after, until) if pair[0] in people}
    results = []
    for person, year in sorted(pairs):
        before, before_rule = registry.attribution.explain(person, year)
        now, rule = after.attribution.explain(person, year)
        results.append(YearResult(person, year, before, before_rule, now, rule,
                                  tuple(after.attribution.conflict(person, year)),
                                  describe(credited.get((person, year), {}))))
    return results


def _name(registry, org_id):
    return registry.organisation_name(org_id) if org_id is not None else UNMAPPED


def _result_line(registry, result):
    conflict = f', conflict: {", ".join(_name(registry, o) for o in result.conflict)}' if result.conflict else ''
    return (f'{result.person} {result.year}: {_name(registry, result.before)} ({result.before_rule}) -> '
            f'{_name(registry, result.after)} ({result.rule}){conflict}; {result.activity or "inactive"}'
            f'{"; CHANGED" if result.changed else ""}')


def conflict_report(registry, proposals, results):
    """The lines that say what `conflicts` would add and what the rules then give."""
    lines = []
    for p in proposals:
        verified = p.record.affiliation
        lines.append(f'record on {verified.id} {verified.person} {verified.organisation} {_years(verified)}: '
                     f'{p.record.text}')
        if p.row:
            snippet = f', snippet "{p.citation.snippet}"' if p.citation and p.citation.snippet else ''
            lines.append(f'  -> stated {p.row.id} {p.organisation} {_years(p.row)} ({p.how}), source '
                         f'{p.source or "none"}{snippet}')
        else:
            lines.append(f'  -> no row: {p.how}' + ('' if p.years else ', no year'))
        lines.extend(f'  check: {item}' for item in p.check)
    years = {(p.row.person, year) for p in proposals if p.row
             for year in range(p.row.from_year, p.row.to_year + 1)}
    lines.extend(_result_line(registry, r) for r in results if r.changed or (r.person, r.year) in years)
    changed = [r for r in results if r.changed]
    lines.append(f'records: {len(proposals)}, rows proposed: {sum(1 for p in proposals if p.row)}, without a row: '
                 f'{sum(1 for p in proposals if not p.row)}, to check: {sum(1 for p in proposals if p.check)}; '
                 f'person-years changed or in conflict: {len(changed)} (active '
                 f'{sum(1 for r in changed if r.activity)}), conflicts: {sum(1 for r in changed if r.conflict)}')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['fills', 'svn', 'conflicts'], help='the step of the migration')
    parser.add_argument('--write', action='store_true', help='write the registers (default: a dry run)')
    args = parser.parse_args(argv)
    if args.step == 'conflicts':
        # Imported here: it reads the collected data
        from scripts.tools.attribution_changes import activity

        registry = load_registry()
        proposals = plan_conflicts(registry)
        results = dry_run(registry, proposals, activity(registry), date.today().year)
        for line in conflict_report(registry, proposals, results):
            print(line)
        if not args.write:
            print('dry run: nothing written to the registers; use --write to write')
            return 0
        affiliations, citations, errors = apply_conflicts(registry.affiliations, registry.citations, proposals)
        for error in errors:
            print(f'error: {error}')
        if errors:
            return 1
        added = len(affiliations) - len(registry.affiliations)
        if added:
            write_affiliations(affiliations)
            write_citations(citations)
        print(f'written: {added} rows, {len(citations) - len(registry.citations)} citations')
        return 0
    if args.step == 'svn':
        identities = load_identities()
        plan = plan_svn(identities, read_excerpt)
        for line in svn_report(plan):
            print(line)
        if plan.errors:
            return 1
        if not args.write:
            print('dry run: nothing written; use --write to write')
        elif plan.added:
            write_identities(identities + plan.added)
        return 0
    affiliations, citations = load_affiliations(), load_citations()
    plan = plan_fills(affiliations, citations)
    for line in fill_report(plan):
        print(line)
    if not args.write:
        print('dry run: nothing written; use --write to write')
        return 0
    if plan.removed:
        new_affiliations, new_citations = apply_fills(affiliations, citations, plan)
        write_affiliations(new_affiliations)
        write_citations(new_citations)
    return 0


if __name__ == '__main__':
    sys.exit(main())
