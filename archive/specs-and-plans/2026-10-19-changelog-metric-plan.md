# Plan: changelog entries as a contribution metric

Refs #71.
The feasibility study and the draft spec are in `2026-10-19-changelog-metric-feasibility.md`.

## Decisions (Jens Klein)

- D1: collect all years; report 2004–2012, with 2013–2015 as a transition.
- D2: level B, a column of its own: `changelog_entries` next to commits and pull requests in the yearly organisation statistics and the multi-year summaries, and a section on 2004–2012 in the contributor report. Never added to commits or pull requests; the tables keep their order. No change to the recognition or the community page.
- D3: an entry with several names counts in full for each person.
- D4: an entry is dated by its release header, the tag of the version as a fallback; the lag is documented.
- D5/D6: a new curated file `curated/mappings/changelog_names.csv`; a tool proposes rows from commit evidence, a person confirms each row. This change adds the file with its header only; the rows follow in a separate pull request, reviewed row by row.
- D7: the repositories and branches of the commit collector: all repositories minus `excluded_repositories.csv`, the default branch and the release branches.
- D8: `scripts/lib/git_history.py` fetches only the trees of the branch tips and the changelog files into the existing clones; no second cache.
- D9: GNU-style ChangeLogs are skipped, a follow-up.
- D10: second accounts are not part of this change.

## Collect

- `scripts/lib/changelogs.py`: file selection, parser (headers, entries, names, dates), deduplication, `NameMapper`, credit; ported from the prototype of the study.
- `scripts/lib/git_history.py`: `update_clone(tags=True)`, `files_at_tips`, `branch_tips`, `tag_dates`, `commit_messages`.
- `scripts/collect/plone_changelogs.py`, `make run-changelogs`: one file per year from 2002 to the last completed year, `collected/changelogs/YYYY-plone-changelog-entries.csv`, one row per person, sorted with `tables.by_count`; prints the coverage per year and the most frequent names without a mapping.
- Name mapping, in order: `changelog_names.csv`, `commit_authors.csv` (Subversion local part, address, full name), `account_aliases.csv`, `bot_accounts.csv` (dropped), logins in `collected/contributors/`, `mapping-github-username-to-fullname.csv`; unmatched names count as written.
- `scripts/tools/unmatched_changelog_names.py`: lists names without a mapping; `--propose` prints rows from the commits that repeat the entries, with the entry and the commit as public records.

## Derive and report (D2)

- `scripts/derive/organisation_stats.py`: column `changelog_entries`; unmatched names count for Unmapped; no new rows for organisations without code work in the year; 0 when a year has no changelog file.
- `scripts/derive/multi_year_summary.py`: the sum of the column.
- `scripts/report/generate_contributor_report.py`: section "Changelog Entries 2004–2012", per person (with their commits) and per organisation.
- Regenerate the derived data and reports; the recognition and the community page stay unchanged.

## Tests and docs

- Offline tests: parser, dating, deduplication, mapping order, credit, output format, the collector with a fake git layer, `files_at_tips` against a local repository, the proposal tool, the format of `changelog_names.csv`, the new column and the report section.
- Docs: data sources, data files, mapping files, Make targets, counting rules, history and coverage, known limitations, the how-to guides for collecting and linking names, method history, and the folder READMEs.

Assisted-by: Claude Opus 5.5
