# Events and community records — Implementation Plan (plan 3b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The 190 yearly community files become one file per kind: events as records (conference, symposium, wpd, sprint), talks, trainings and organisers pointing to them, and the roles (Board, team leaders, release managers, podcasts) with a year column. Every row cites source ids captured in plan 3a and keeps its old `source` cell verbatim. Every number stays the same.

**Architecture:** Same shape as plan 2c: a pure migration library (tested on fixtures, run once), a lossless audit, then one switch of schemas, model, checks, tests and data together. The model keeps its public API (`items(year, kind)`, `roles(year)`, `talks(year)`, `events(year)`, `recognition_levels()`), so derive and report code doesn't change.

**Tech Stack:** Python 3.12, frictionless, pytest.

**Spec:** `archive/specs-and-plans/2026-10-22-sources-and-events-design.md`, section "events and community data". Inputs: plan 3a's `archive/migration-to-events/` (`worklist.jsonl`, `capture-results.jsonl` for pages; `videos-worklist.jsonl`, `videos-capture-results.jsonl` for videos), the source register, and `scripts/lib/cells.py` (the cell parser). A passage that holds only a person's name is evidence of presence on that page, nothing more.

## Decisions taken in this plan (controller's calls, for Jens to check)

1. **Folder and files.** `curated/community-contributions/` becomes `curated/community/` with `events.csv`, `talks.csv`, `trainings.csv`, `organisers.csv`, `board-of-directors.csv`, `team-leaders.csv`, `release-managers.csv`, `podcasts.csv`, and the unchanged `community-recognition-levels.csv` and `community-recognition-points.csv`.
2. **Sources.** Every row has `sources` (source ids separated by semicolons, a set cell checked against `sources`) and `cited_as` (the old `source` cell, verbatim — lossless by construction). No snippets on community rows (the design's call: the row itself is the reading).
3. **Events** `id, kind, name, start, end, location, format, level, sources, cited_as, notes`.
   - `kind`: `conference` (the Plone Conference of a year), `symposium` (a regional conference: `conference-talks` rows with scope `regional`), `wpd` (one per World Plone Day location, including the online editions), `sprint`.
   - `format` (in person, hybrid, online) for WPD events; `level` for sprints (strategic…); empty otherwise.
   - Ids are opaque slugs, never renamed: `plone-conference-<year>`, a symposium's slugified name, `wpd-<date>-<location slug>` (online editions `wpd-<year>-online`), a sprint's slugified name (with `-2` on a clash).
   - A Plone Conference event exists for every year that has a `plone-conference` file, talks or trainings.
4. **Talks** `id, event, type, title, speakers, organisations, video, sources, cited_as, notes` — conference talks and World Plone Day talks together; `type` keeps today's values (Keynote, Talk, Panel, Full stream, Opening, Recap, Announcement, Newsroom, Duplicate …); a WPD talk's event is the WPD event of its year and location. Id `t` + 8 hex of SHA-1 over `event|title|type`.
5. **Trainings** `id, event, title, trainers, sources, cited_as, notes`; event = that year's Plone Conference. Id `r` + 8 hex over `event|title`.
6. **Organisers** `event, person, organisation, sources, cited_as, notes`, exactly one of person and organisation, one row per organiser: from the `organisers` and `organisations` cells of sprints and WPD events, and from `plone-conference.csv` (`organisation` and `organisers`). A plone-conference file row's notes stay on its organiser rows. How organisers count is not changed: the recognition report reads organiser rows with an organisation exactly as it reads today's `organisations` cells. Credit and points are decisions of the Board and the Marketing Team; this project prepares and shows the data, it doesn't change how anything is credited.
7. **Roles.** `board-of-directors` (`year, person, role, sources, cited_as, notes`), `team-leaders` (`year, person, team, …`), `release-managers` (`year, person, …`), `podcasts` (`year, series, person, episodes, …`).
8. **Provenance.** The model's `file`/`line` now name the new file and row; the `source` attribute becomes the row's source URLs joined (for the community page's links). In `derived/` and `reports/` only these provenance columns may change; every count, point, level and name stays identical — an acceptance test compares the outputs column by column.
9. **Policy tests** that checked "a file for every year" check "rows for every year" instead.

## Global Constraints

- Worktree `.claude/worktrees/events`, branch `events`, from `origin/main` after plan 3a (#177) is merged.
- Lossless: the audit proves every old cell value is in the new rows (verbatim `cited_as`, people, organisations, titles, notes), per old file and row.
- Numbers identical; provenance only may change (decision 8).
- Model is the only reader; Frictionless schemas; regenerate `curated/datapackage.json` and `docs/reference/curated-files.md`.
- Tests offline; commit footers as in plan 3a; docs in the same PR; migration code archived (`archive/migration-to-events/`).

## Review Focus

1. **Two WPD events on one date in one city** (two organisers holding separate events) → two events with distinct ids. → Task 1 `test_wpd_events_on_one_day_stay_apart`.
2. **A WPD talk whose location matches no WPD event row** (online videos) → the online event of its year. → Task 1 `test_wpd_talk_without_event_row_goes_online`.
3. **A sprint without an end date or with the same name in two years** → stable distinct ids. → Task 1 `test_sprint_ids`.
4. **Recognition points and levels** must be identical, including the split of points among organisations. → Task 3 `test_outputs_identical_except_provenance`.
5. **The community page's links** (the "data" link and the source links of a contribution) must point to the new rows and to the captured sources. → Task 3 test on `derived/community-page.json`.

---

### Task 1: Migration library (pure, on fixtures)

`scripts/tools/migrate_community.py` + `tests/test_migrate_community.py`: `migrate(old_rows_by_kind_and_year, results, sources) -> Migrated` with lists per new file (decisions 2–7), deterministic order (events by start, id; talks by event, type, title; trainings by event, title; organisers by event, person, organisation; roles by year then their old order keys), and a CLI with a dry-run summary and `--write` (writes the new folder, removes the old one; not run in this task). URL → source id as in plan 2c (results line, else a deterministic uncaptured source with `not captured on <date>: <reason>`).

- [ ] Failing tests per decision plus the Review Focus 1–3 tests; implement; full suite; commit — "Migrate the community data to events (library)".

### Task 2: Lossless audit

`scripts/tools/audit_community.py` + test: per old file and row (from git at the base commit), every column's value is in the new rows: `cited_as` equals the old `source` verbatim, people and organisations sets equal, titles, types, videos, levels, dates, locations, notes equal; every old row maps to exactly one new row (organiser and role rows: one per element). Output counts and losses (must be 0). Run it on a dry-run migration in memory.

- [ ] Failing tests; implement; run on the real data in memory; commit — "Audit the migration of the community data".

### Task 3: The switch

Schemas for the eight new kinds (+ the moved recognition files), delete the ten old ones; `scripts/lib/paths.py` (`COMMUNITY = Path('curated/community')`, file constants); `scripts/lib/model/community.py` readers on the new files with the same public API and dataclasses (`Event.kind` keeps today's values `plone-conference`/`sprints`/`world-plone-day` for consumers, mapped from the new kinds); checks (foreign keys event→events, people, organisations, sources; organiser exactly one of person/organisation; unique ids; set cells); `tests/conftest.py`, `tests/test_schemas.py`, `tests/test_curated_policy.py`, the community model tests; the data via `python -m scripts.tools.migrate_community --write`; `tests/test_outputs_identical_except_provenance` (compare `derived/` and `reports/` regenerated against the committed ones, ignoring only the provenance columns of decision 8), then regenerate the committed outputs whose provenance changed.

- [ ] Failing tests; switch; `python -m scripts.tools.check`; `python -m pytest -q`; commit (code and data together, as in plan 2c).

### Task 4: Tools and docs

`scripts/tools/person.py` (if it lists community rows), any tool that writes or prints community rows; docs: `docs/explanation/curated-community-data.md`, `docs/how-to/add-curated-community-data.md`, `docs/how-to/prepare-a-new-year.md`, `docs/explanation/community-page.md`, `docs/explanation/community-recognition.md`, `docs/reference/data-files.md`, `docs/glossary.md`, `curated/README.md`, `AGENTS.md` (Layout: `curated/community/`), `README.md`; every mention of `community-contributions` (53 today).

- [ ] Update; `make docs`; full suite; commit — "Document events and the community records".

### Task 5: Archive and pull request

Move `migrate_community.py`, `audit_community.py`, `community_sources.py` (plan 3a) and their tests to `archive/migration-to-events/`; README with the audit result; copy this plan to `archive/specs-and-plans/2026-10-25-events-plan.md`; verify; ask Jens before pushing; open the PR with the decisions above.
