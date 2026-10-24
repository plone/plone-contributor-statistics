# Citations, decisions and computed counting — Implementation Plan (plan 2c)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The registers switch to the structure of the design: `people` (id, name), `identities` with typed kinds and a source id, `affiliations` with an id and a status, a new `citations` table that ties each affiliation to its sources with verbatim snippets, and the organisation a person counts for computed by the attribution rules. `affiliation_proposals.csv` and `rejected_proposals.csv` disappear into affiliation statuses. Every statistic stays byte-identical.

**Architecture:** A pure migration library turns the old rows plus the capture results of plan 2a into the new rows (tested on fixtures, then run once on the real data). A pure attribution engine in the model computes the organisation per person and year from affiliations, citations, sources and the commit domains of plan 2b. The model, the checks, the tools and the tests switch to the new files in one task, together with the migrated data, so the repository is never half-switched.

**Tech Stack:** Python 3.12, frictionless (Table Schema), pytest.

**Spec:** `archive/specs-and-plans/2026-10-22-sources-and-events-design.md` (sections person, identity, source, decision, affiliation, citation, counting, Migration steps 1–2). Inputs from earlier plans: `archive/migration-to-sources/` (work list, searches, capture results, review file; plan 2a, #174), `collected/commit-domains/` with `scripts/lib/commit_domains.py` (plan 2b, #173). A survey of every reader of the registers: `/tmp/claude-1000/-home-jensens-ws-cdev-plone-contributor-statistics/79c121a4-992f-4cb9-a898-a2531bf02971/scratchpad/p2/consumers-notes.md`.

## Decisions taken in this plan (controller's calls, for Jens to check)

1. **Main account and further accounts.** `people.github` becomes an identity of kind `github` (at most one per person; it is the username the collected files count under). Today's `login` identities (second accounts) become kind `github-alias`. Other kinds: `email`, `name` (unchanged). `svn`, `irc`, `discourse` are allowed by the schema but no row is created now (the "SVN user …" phrases move in plan 5).
2. **A person without GitHub** keeps the public record of the name as an identity of kind `name` with the display name as value.
3. **Identities cite one source.** `identities.source` is a source id (the first captured URL of the old cell), `snippet` the first verbatim quote of the old cell found in that source's excerpt (for an email identity: the email address when the excerpt contains it), and `notes` keeps the old cell text verbatim, so no URL or wording is lost. The CVS/SVN exception stays: an `email` identity may have an empty source when its notes state what it rests on (none today).
4. **One citation row per verbatim snippet.** A cited source with several snippets for one affiliation gets several citation rows; a cited source without any verified snippet gets one row with an empty snippet. `citations.notes` keeps the cell's own words for that URL (the segment label) and every quote of the cell that is not verified in the excerpt.
5. **Every cited URL is a source.** URLs the capture of plan 2a didn't record (nothing found, errors, videos pending) get a source row too: kind by the work-list hint (else `page`), title = the URL, date = the capture day 2026-10-22, `fetched` = the migration time, notes `not captured on 2026-10-22: <reason from the results>`, and an excerpt file with that sentence as its only passage. A later `capture` of the URL adds the real passages. A GitHub commit-search URL is cited through the commits it found (`searches.json`), with the search URL kept in the citation's notes.
6. **Statuses.** `stated` for every row today, except rows whose notes contain `not verified` → `assumed`. Rows of `rejected_proposals.csv` → `denied` rows (organisation, years, notes = the reason) citing their decision source (the PR comment; source kind `decision`). `proposed` replaces `affiliation_proposals.csv` (empty today).
7. **Affiliation ids** are opaque and stable: `a` + 8 hex digits of SHA-1 over `person|organisation|from|to` at creation; never recomputed when a row changes later.
8. **Counting rules computed now:** 1 (proposed ignored, denied removes), 2 (decision wins; latest decision of a person-year wins; `supersedes` must name the earlier one), 3 (one organisation; stated beats assumed), 4 (change year), 6a–6d (tie-breaks, automatic), 7 (conflict → check fails). **Not computed in this plan: rule 5 (bridging).** Today's rows already include bridged years and bridging stays a rule for writing rows, as documented; computing it would add years to some people and break the byte-identical goal. Plan 5, which narrows rows to their records, computes it.
9. **Own domains are personal** in rule 6b: a domain that `is_own_domain` recognises for the person (e.g. `vanrees.org`) counts as a personal address (plan 2b note).
10. **Own statements** for rule 6c are sources of kind `speaker-page` and `profile`.

## Global Constraints

- Worktree `.claude/worktrees/registers`, branch `citations-registers`, from `origin/main` ab0d416. Python from `~/.venvs/plone-contributor-statistics`.
- **Byte-identical statistics:** after the switch, `tests/test_reproducible_outputs.py` passes against the committed `derived/` and `reports/` without regenerating them, except `derived/community-page.json` if (and only if) it embeds register-derived search keys whose format changes — then regenerate it and show in the report that only those keys changed.
- **Lossless:** an audit (Task 5) proves that every URL, every quote and every label of the old `source` cells and every old `notes` text exists in the new data (sources' url/archive_url, citation/identity snippets and notes, affiliation notes), per person. A loss is a blocker, not a minor.
- `scripts/lib/model/` stays the only reader of `curated/`; Frictionless schemas stay the format authority; `curated/datapackage.json` and `docs/reference/curated-files.md` are regenerated.
- Snippets are verbatim: the check `snippet appears in its source's excerpt` (with `find_quote`) passes for every non-empty snippet.
- Tests offline; commit footers as before; docs in the same PR; migration code archived in the same PR (`archive/migration-to-citations/`), together with `scripts/tools/cited_sources.py` from plan 2a.

## Review Focus

1. **A person whose only GitHub record is a second account** (`login` identity, no `people.github`) must keep the same username in the collected files. → Task 1 `test_login_identity_without_people_github_stays_alias`, Task 3 `test_username_of_unchanged_on_real_registers`.
2. **A cell whose quote is in the live page but the cited copy is archived (or the reverse)** — the snippet goes only to the source whose excerpt holds it. → Task 1 `test_snippet_only_where_verified`.
3. **A rejected proposal overlapping a stated row of another organisation** (Maurits: Zest 2024–2025 denied, Py76 2024 stated) — denied removes Zest only. → Task 2 `test_denied_removes_only_its_organisation`.
4. **Two decisions for the same person-year without `supersedes`** must fail the check, with `supersedes` the later wins. → Task 2 and Task 3 tests.
5. **Uncaptured URLs** (errors, nothing found, pending videos) must still be cited, never dropped. → Task 1 `test_uncaptured_url_becomes_a_source`, Task 5 audit.

---

### Task 1: Migration library (pure, on fixtures)

**Files:** Create `scripts/tools/migrate_registers.py`, `tests/test_migrate_registers.py`.

**Interfaces:**
- Consumes: `split_segments`, `parse_segment` from `scripts/tools/cited_sources.py`; `find_quote` from `scripts/lib/capture/passages.py`; `source_id`, `split_archive_url` from the model.
- Input objects (plain dicts, so the old schemas need not stay importable after the switch): `old_people`, `old_identities`, `old_affiliations`, `old_rejections` (rows as read by `csv.DictReader`), `results` (capture-results lines), `searches` (dict), `worklist` (lines), `sources` (dict id → {kind,url,archive_url,…}), `excerpt(id) -> str`.
- Produces `migrate(...) -> Migrated` with lists of new rows: `people` (`id,name`), `identities` (`person,kind,value,source,snippet,notes`), `affiliations` (`id,person,organisation,from,to,status,checked,notes`), `citations` (`affiliation,source,snippet,supersedes,notes`), `new_sources` (rows for uncaptured URLs, decision kind updates for rejection comments) and `new_excerpts` ({id: text}). Deterministic order: people by id; identities by person, kind, value; affiliations by person, from, organisation; citations by affiliation, source, snippet.
- Mapping rules: decisions 1–7 above. URL → source id: the results line's `source_id` when not null, else the deterministic id of decision 5 (`source_id(original, timestamp)`); a Wayback URL's id comes from its result (it may name another timestamp, plan 2a Task 1).

- [ ] **Step 1:** Failing tests on small fixtures, one per rule: `test_people_lose_github_and_source`, `test_people_github_becomes_github_identity`, `test_login_identity_without_people_github_stays_alias`, `test_person_without_github_gets_name_identity`, `test_identity_cell_kept_in_notes`, `test_snippet_only_where_verified`, `test_citation_per_snippet_and_label_in_notes`, `test_unverified_quote_kept_in_notes`, `test_uncaptured_url_becomes_a_source`, `test_search_url_cited_through_its_commits`, `test_not_verified_rows_are_assumed`, `test_rejection_becomes_denied_with_decision_source`, `test_affiliation_id_is_stable`, `test_output_is_sorted`.
- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Migrate the registers to citations (library)".

### Task 2: Attribution engine (pure)

**Files:** Create `scripts/lib/model/attribution.py`, `tests/test_attribution.py`.

**Interfaces:**
- `@dataclass(frozen=True) class Affiliation: id, person, organisation, from_year, to_year, status, checked, notes` with `covers(year)`; `@dataclass(frozen=True) class Citation: affiliation, source, snippet, supersedes, notes`.
- `class Attribution(affiliations, citations, sources, excerpt, commit_domains, registry)`; `organisation(person_id, year) -> str | None` (organisation id or None for Unmapped); `conflicts() -> list[(person_id, year, [organisation ids])]` over all person-years any affiliation covers; `decision_errors() -> list[str]` (two decisions for one person-year where the later doesn't name the earlier in `supersedes`).
- Rules in order (decisions 6, 8, 9, 10): 1 proposed ignored, denied removes its organisation (empty-organisation denied rows are ignored here); 2 an affiliation citing a source of kind `decision` counts for its years, the latest decision (source `date`) wins; 3 one organisation left → it, stated beats assumed; 4 change year: one organisation also covers year−1 and not year+1, the other covers year+1 → the first; 6a both cite the same source and one is named first in that source's excerpt (position of `find_quote` of the snippets) → the first; 6b commits: `organisation_commits` (plan 2b) of the person's username for the year, with own domains (`is_own_domain`) moved to personal; the organisation with most commits wins when company commits are the majority of all commits; 6c most commits personal → the organisation an own statement (citation of a source of kind `speaker-page`/`profile` whose `date` falls in the year) names; 6d the organisation more distinct cited sources name for that year; 7 else conflict.
- `commit_domains` is a callable `year -> {username: Counter}` (`load_commit_domains`; a year without a file → `{}`).

- [ ] **Step 1:** Failing tests: one per rule with minimal fixtures, plus `test_denied_removes_only_its_organisation`, `test_latest_decision_wins`, `test_decisions_without_supersedes_are_reported`, `test_own_domain_counts_as_personal` (vanrees.org case), `test_unmapped_without_rows`, `test_non_overlapping_rows_equal_first_match` (property: for random non-overlapping rows the engine equals today's first-match lookup).
- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Compute the organisation of a person and year by the attribution rules".

### Task 3: The switch — schemas, model, checks, data

**Files:**
- Schemas: modify `curated/schemas/people.json`, `identities.json`, `affiliations.json`; create `citations.json`; delete `affiliation-proposals.json`, `rejected-proposals.json`. `sources.json`: no change.
- Data: run `migrate()` on the real files (CLI of Task 1: `python -m scripts.tools.migrate_registers --write`) — rewrites `people.csv`, `identities.csv`, `affiliations.csv`, writes `citations.csv`, adds source rows/excerpts, deletes `affiliation_proposals.csv`, `rejected_proposals.csv`.
- Model: `scripts/lib/model/registers.py` (Person(id, name); Identity(person, kind, value, source, snippet, notes); `Registry` indexes `github` and `github-alias` as logins, `username_of` = the `github` identity else `person:<id>`, `organisation_of` delegates to `Attribution`), `scripts/lib/model/__init__.py`, `scripts/lib/paths.py` (`CITATIONS`; remove the two proposal paths), `scripts/lib/model/checks.py`, `scripts/tools/schema_docs.py`, `tests/conftest.py` (`EMPTY_MAPPINGS`, `write_registers` → new formats, same signature), `tests/test_schemas.py`, `tests/test_model_is_the_only_reader.py`, every test file the survey lists that builds old-format rows.
- New model helpers replacing the proposal files: `append_proposals(rows)` writes `proposed` affiliations plus their citations (keeps its name and signature shape: rows carry `person, organisation, from, to, sources` = list of (source id, snippet)); `load_rejections()` returns the (person, organisation, year) set of `denied` rows.

**Checks (in `checks_for`):**
- people: `Sorted(id)`. identities: `Sorted(person, kind, value)`, `UniqueCasefold(value, scope=kind)`, at most one `github` per person, a `github-alias` is nobody's `github`, `source` required unless kind `email`; foreign keys person→people, source→sources.
- affiliations: `Sorted(person, from, organisation)`, `AffiliationPeriod` (unchanged), unique `id`, `status` enum, foreign keys; `ReachingBackPastRecord` reads `status == 'assumed'` instead of the note; `AffiliationOverlap` removed; new `UnresolvedConflict` (from `Attribution.conflicts()`) and `DecisionSupersedes` (from `decision_errors()`), reported on the affiliations resource.
- citations: foreign keys affiliation→affiliations.id, source→sources.id, supersedes→sources.id; `SnippetInExcerpt` (non-empty snippet found by `find_quote` in the source's excerpt); `Sorted(affiliation, source, snippet)`; every non-proposed affiliation has at least one citation.

- [ ] **Step 1:** Write the failing tests for the new checks and model (`tests/test_checks.py`, `tests/test_model_registers.py`), including `test_username_of_unchanged_on_real_registers` (compare every `username_of` on the migrated registers with the old `people.github` values, read from git `HEAD:curated/mappings/people.csv` before the switch and stored as a fixture file in `tests/fixtures/`).
- [ ] **Step 2:** Schemas, model, checks, fixtures; run the migration on the real data; regenerate `curated/datapackage.json` and `docs/reference/curated-files.md`.
- [ ] **Step 3:** `python -m scripts.tools.check` → no errors (no unresolved conflict, no decision error); `python -m pytest -q` → all pass, including `tests/test_reproducible_outputs.py` **without** regenerating `derived/`/`reports/` (see the constraint on `community-page.json`).
- [ ] **Step 4:** Commit in two commits: code + tests ("Switch the registers to citations and computed counting"), data ("Migrate the registers to citations").

### Task 4: Tools and consumers

**Files:** `scripts/tools/person.py` (`--add NAME [--github LOGIN] --source URL_OR_ID`: the source must be in the register — an URL is looked up by its id; if missing, the tool says to run `python -m scripts.tools.capture` first; it writes the person and a `github` or `name` identity citing it), `scripts/tools/affiliation.py` (prints the computed organisation per year and, per affiliation, its citations with snippets; no own first-match loop), `scripts/tools/address_proposals.py` and `scripts/tools/github_evidence.py` (evidence commits are captured as sources through `capture()` — local clones, no network for commits in them — and proposals written with `append_proposals`; `is_own_domain` takes the person's logins from the registry), `scripts/tools/unmatched_names.py`, `scripts/tools/unmatched_changelog_names.py` (prints identity rows in the new format), `scripts/lib/changelogs.py` (`NameMapper` unchanged in behaviour), `scripts/derive/community_page.py` (`people_names` from `github`/`github-alias`/`name` identities), their tests.

- [ ] **Step 1:** Update the failing tests to the new behaviour (one per tool). **Step 2:** Implement. **Step 3:** Full suite, check, reproducible outputs — PASS.
- [ ] **Step 4:** Commit — "Let the tools write and read citations".

### Task 5: Lossless audit and docs

**Files:** Create `scripts/tools/audit_migration.py` (migration code, archived in Task 6) and its test; docs: `docs/explanation/attribution.md` (registers, statuses, citations, decisions and the computed rules, the order of the rules; bridging still applied when writing rows), `docs/reference/mapping-files.md`, `docs/how-to/add-an-affiliation.md` (capture → affiliation → citation; proposals and denials as statuses), `docs/how-to/add-a-person.md`, `docs/how-to/link-old-commits-to-a-person.md`, `docs/how-to/find-a-contributor.md`, `docs/how-to/prepare-a-new-year.md`, `docs/how-to/regenerate-after-a-mapping-change.md`, `docs/explanation/counting-rules.md`, `docs/glossary.md`, `curated/README.md`, `curated/mappings/README.md`, `AGENTS.md`, `README.md` — every place the survey lists.

- [ ] **Step 1:** The audit: for each old row (read from git `ab0d416:curated/mappings/…`), every URL of its cells is the `url` or `archive_url` of a source the person's new rows cite (or a commit of its search), every quote and every label is a snippet or inside a notes field of the person's new rows, every old `notes` text is unchanged in the new row. Output: counts and the list of losses (must be empty). Test on fixtures.
- [ ] **Step 2:** Run it on the real data; fix the migration (Task 1 code) for any loss and rerun Task 3's data step.
- [ ] **Step 3:** Docs; `make docs` (Sphinx `-W`).
- [ ] **Step 4:** Commit — "Document citations and the computed attribution".

### Task 6: Archive and pull request

- [ ] **Step 1:** Move `scripts/tools/migrate_registers.py`, `scripts/tools/audit_migration.py`, `scripts/tools/cited_sources.py` and their tests to `archive/migration-to-citations/` (README with what ran when, the audit summary; a row in `archive/README.md`); `scripts/tools/capture.py --batch` stays.
- [ ] **Step 2:** Copy this plan unchanged to `archive/specs-and-plans/2026-10-22-citations-plan.md`.
- [ ] **Step 3:** `python -m pytest -q && python -m scripts.tools.check && make docs` — PASS. Ask Jens before pushing; open the PR with the decisions list above and the audit summary.
