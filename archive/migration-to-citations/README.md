# Migration to citations, 2026-10-23

The code that migrated the registers in `curated/mappings/` to citations (plan 2c of the data structure work), with its audit and its tests.
It ran once, on 2026-10-23: the code that reads the new registers and the migrated data are the single commit 1c8e0bb, because neither can read the registers of the other.
The files are kept unchanged, except that mail addresses were masked on 2026-10-27; they do not run any more: the old registers and their schemas were removed by the switch.

## Files

- `migrate_registers.py`: read the old registers (`people.csv`, `identities.csv`, `affiliations.csv`, `rejected_proposals.csv`, `affiliation_proposals.csv`) and wrote the new ones: identities that cite one source, affiliations with a status and an opaque id, one citation row per verbatim snippet, denied rows for the rejected proposals, and a source row for every cited URL.
- `cited_sources.py`: the tool of plan 2a that built the work list of the cited URLs from the old `source` cells, and the parser of those cells (`split_segments`, `parse_segment`) that the migration and the audit used.
- `audit_migration.py`: the lossless check. It read the old registers with `git show <rev>:…` and the new ones through the model, and reported every URL, quote, label and note of an old `source` cell that was missing in the new data.
- `tests/`: the offline tests of the three scripts. `pytest.ini` collects only `tests/`, so they do not run.
- `tests/test_username_of_unchanged.py` with `tests/people-github-before-citations.csv`: the migration check that every person counts under the same username as before (the `github` column of `people.csv` before the switch). It reads the current registers, so it held for the migrated data and stops holding with the first person added after it; run it with `python -m pytest archive/migration-to-citations/tests/test_username_of_unchanged.py` only against the data of 1c8e0bb.

## Audit result

The audit of the migrated data (`python -m scripts.tools.audit_migration --rev ab0d416`) reported 0 losses.

| Checked | Count |
|---|---|
| people | 788 |
| identities | 966 |
| affiliations | 1411 |
| rejections | 17 |
| open proposals | 0 |
| source cell segments | 2712 |
| cited addresses | 2665 |
| labels | 2301 |
| addresses | 2689 |
| quotes | 897 |

## Input from plan 2a

The capture of plan 2a (`archive/migration-to-sources/`) fed the migration:

- `capture-results.jsonl` named the source id of every captured URL, so that the citations point to the recorded sources and their excerpts.
- `searches.json` named the commits that each GitHub commit search found, so that a search is cited through its commits.
- `worklist.jsonl` and `review.jsonl` held the quotes and the segments that could not be attached with certainty.

URLs that the capture did not record became source rows of their own, with the reason in the notes.
