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

Without --write, it prints every change it would make. A second run changes nothing.

    python -m scripts.tools.migrate_notes fills [--write]
    python -m scripts.tools.migrate_notes svn [--write]
"""

import argparse
import dataclasses
import re
import sys

from scripts.lib.model import (Identity, load_affiliations, load_citations, load_identities, read_excerpt,
                               write_affiliations, write_citations, write_identities)
from scripts.lib.model.attribution import DENIED, STATED

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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=['fills', 'svn'], help='the step of the migration')
    parser.add_argument('--write', action='store_true', help='write the registers (default: a dry run)')
    args = parser.parse_args(argv)
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
