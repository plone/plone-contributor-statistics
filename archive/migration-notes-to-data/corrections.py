"""Two corrections after the `fills` and `conflicts` steps of migrate_notes.py, run once on 2026-10-26.

    PYTHONPATH=. python archive/migration-notes-to-data/corrections.py earlier-review [--write]
    PYTHONPATH=. python archive/migration-notes-to-data/corrections.py checked BEFORE_DIR [--write]

`earlier-review`: the notes of the rows whose records were reviewed and are now stated rows ("not applied, the verified
row stands: ..." and "Kept, not deciding: ...") are prefixed with "earlier review: ", the old text kept verbatim.

`checked`: the `checked` date of a fill row that `fills` removed is appended as " (checked YYYY-MM-DD)" right after
the "bridged <from>-<to>: ..." fragment that moved to the neighbour row. BEFORE_DIR holds affiliations.csv and
citations.csv as they were before the removal (git show 4b4947b~1:curated/mappings/...).
It ran when migrate_notes.py was still `scripts/tools/migrate_notes.py`, which it imports.
"""

import dataclasses
import sys
from pathlib import Path

from scripts.lib.model import load_affiliations, load_citations, write_affiliations
from scripts.tools import migrate_notes

PREFIX = 'earlier review: '


def earlier_review(affiliations):
    return [dataclasses.replace(a, notes=PREFIX + a.notes)
            if (a.notes or '').startswith(migrate_notes.CONFLICT_MARKERS) else a for a in affiliations]


def checked(affiliations, before_dir):
    before = load_affiliations(before_dir)
    plan = migrate_notes.plan_fills(before, load_citations(before_dir))
    by_id = {a.id: a for a in affiliations}
    appended = 0
    for fill in sorted(plan.removed, key=lambda fill: fill.row.from_year):
        if not fill.row.checked:
            continue
        fragment = f'bridged {migrate_notes._years(fill.row)}: {fill.row.notes}'
        target = by_id[fill.target.id]
        assert target.notes.count(fragment) == 1, (target.id, fragment)
        notes = target.notes.replace(fragment, f'{fragment} (checked {fill.row.checked})')
        by_id[target.id] = dataclasses.replace(target, notes=notes)
        appended += 1
    print(f'removed fill rows: {len(plan.removed)}, with a checked date: {appended}')
    return [by_id[a.id] for a in affiliations]


def main(argv):
    write = '--write' in argv
    args = [a for a in argv if a != '--write']
    affiliations = load_affiliations()
    if args[0] == 'earlier-review':
        new = earlier_review(affiliations)
    else:
        new = checked(affiliations, Path(args[1]))
    print(f'rows changed: {sum(1 for a, b in zip(affiliations, new) if a != b)}')
    if write:
        write_affiliations(new)


if __name__ == '__main__':
    main(sys.argv[1:])
