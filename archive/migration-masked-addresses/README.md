# Migration to masked mail addresses, 2026-10-27

The mail addresses of the tracked files were masked once: a company address became a hash that keeps the company domain where the evidence needs it, every other address became a bare hash.
The method is documented in `docs/` (`docs/explanation/attribution.md`), the design and the plan are in `archive/specs-and-plans/2026-10-27-masked-addresses-design.md` and `2026-10-27-masked-addresses-plan.md`.
The code ran in the commits named below, with the data it changed; it is archived unchanged.
The archived tests are not run: pytest collects only `tests/`.

## Files

- `mask_addresses.py`: the steps `list`, `write` and `verify` (`python -m scripts.tools.mask_addresses <step>` while it lived in `scripts/tools/`).
- `tests/test_mask_addresses.py`: its offline tests.

## What ran

The shared code stayed in `scripts/lib/addresses.py` (`mask_address`, `readable_addresses`); the guard `tests/test_no_readable_addresses.py` keeps readable addresses out of every tracked text file.

1. `write` on the curated, collected and generated files (commit `c2a7fca`): 561 files changed, 556 excerpts, `identities.csv`, `citations.csv` and 3 files of `collected/changelogs`.
   Address occurrences masked: 628 company addresses, 144 complete addresses (general service or machine names) and 14 spelled-out ones.
   The excerpts and the `snippet` cells keep the company domain; all other cells are bare.
   `derived/`, `reports/` and `docs/` needed no change.
2. `write` on the archive (commit `8c34249`): 18 files, 14 npm lists of the package statistics and 4 migration logs.
   1257 company addresses, 1218 complete addresses and 15 spelled-out ones.
3. The guard and the test addresses it found (commit `ea9e16e`).
4. A correction after review (commit `3d8815d`): in the `notes` cells of the registers a company address is named in words, `h-<hash> (an address at <domain>)`, so the notes keep the organisation evidence.
   Four files changed again, 22 lines; one more spelled-out address (`b.buehlmann at 4teamwork.ch`) was masked.
   After it the counts are 15 spelled-out occurrences in the data and 16 in the archive.

Distinct addresses masked: 366 (301 company and 65 complete), plus 14 spelled-out ones, each checked by hand in its context.
Placeholders (`example.com`, `.example`, `.invalid`, `.localhost`), Subversion, noreply and not personal addresses stayed as they were.
Line counts did not change.

## Result

- `identities.csv`: 986 rows before and after; 93 rows changed, 87 of them email values.
  `citations.csv`: 2643 rows before and after, 14 rows changed.
  Every snippet is still found in its excerpt.
- `verify` compared, over 441 cached clones and 2103 distinct commit authors (address and name), the person that the registers found at the base `a1541e6` with the person the masked registers find: 0 differences, and 0 differences in the index of the email identities.
- A second `write` reported 0 files changed; the tool run on a clean copy gives byte-identical files.
- `python -m scripts.tools.attribution_changes` listed 0 changes: no organisation counts for another.

## Follow-up

The privacy notice and the opt-out procedure are separate work for the Plone Foundation Board.
An erasure request is handled one by one; the git history is not rewritten, so addresses that were readable before this migration stay in earlier commits.
