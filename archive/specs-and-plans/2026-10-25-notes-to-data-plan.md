# From notes to data — Implementation Plan (plan 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridging is computed by the engine, decisions come after the rules, the bridged fill rows disappear, conflicting "not applied" records become rows, "SVN user" phrases become identities, and a review list shows decisions that later facts may overrule. Every change in who counts where is listed for Jens before it is written.

**Architecture:** First the engine (rule order, computed bridging, an explanation per person-year, outdated decisions) with a difference tool that compares today's counting (from git) with the new one. Then the data steps, each keeping `make check` green and each proven by the difference tool. Decisions for the cases the rules leave open go through the GitHub issue "Attribution decisions".

**Tech Stack:** Python 3.12, pytest, frictionless; `gh` only with Jens's OK.

**Spec:** `2026-10-25-notes-to-data-design.md` (scratchpad; archived with this plan), on top of `archive/specs-and-plans/2026-10-22-sources-and-events-design.md`.

## Global Constraints

- Worktree `.claude/worktrees/notes-to-data`, branch `notes-to-data`, from `origin/main` 1c64265.
- **Rule order** (Jens): 1 proposed ignored, denied removes its organisation; 2 the rules — one organisation left (stated over assumed), change year, bridging, tie-breaks 6a–6d; 3 decisions settle only what the rules leave open; 4 conflict.
- **Bridging** (Jens, documented rule): two years covered by `stated` rows of organisation X cover the years between for X when no `stated` row of another organisation covers any of them and no `denied` row of X covers them; no distance limit; notes never block a bridge; assumed rows are not records for bridging.
- **No credit changes without a listed decision:** every person-year whose counting differs from today's (active years: commits, PRs, changelog entries, PLIPs, community roles) is listed before any data commit; Jens decides; outdated decisions are listed, not silently dropped.
- Lossless: no URL, quote, label or note lost; citations of removed rows move to the rows that keep the evidence.
- `gh` (issue creation, comments) only on Jens's explicit OK; Claude drafts, Jens or the person posts.
- Model only reader/writer of `curated/`; tests offline; docs in the same PR; footers `Assisted-by: <model>`, `Assisted-by: Claude Opus 5.5`, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, each once.

## Review Focus

1. **A bridge across an "Unmapped" note** (Kim Nguyen 2012–2013) must bridge. → Task 1 `test_old_notes_never_stop_a_bridge`.
2. **A bridge that only reaches an assumed row** must not bridge, and the difference tool lists it. → Task 1 `test_assumed_rows_are_not_records_for_bridging`, Task 2.
3. **A decision the rules now decide** is not applied and is reported as outdated. → Task 1 `test_a_decision_the_rules_decide_is_outdated`.
4. **Removing a fill row that cites a source its neighbours don't** keeps the citation (moved). → Task 3 `test_a_fill_rows_own_source_moves_to_a_neighbour`.
5. **Two SVN users of one person** become two identities, one per user. → Task 4 test.

---

### Task 1: Engine — rule order, computed bridging, explanation, outdated decisions

**Files:** `scripts/lib/model/attribution.py`, `scripts/lib/model/checks.py` (if `decision_errors` wiring changes), `scripts/tools/affiliation.py` (print the rule per year), tests `tests/test_attribution.py`, `tests/test_tool_affiliation.py`.

**Interfaces:**
- `Attribution.organisation(person_id, year)` unchanged in signature; the order of `_decide` becomes 1 → 3 → 4 → 5 (bridging) → 6 → 2 (decisions) → 7.
- `Attribution.explain(person_id, year) -> tuple[str | None, str]`: the organisation and the rule that gave it: `'one organisation'`, `'stated over assumed'`, `'change year'`, `'bridged'`, `'named first'`, `'commits'`, `'own statement'`, `'records'`, `'decision'`, `'conflict'`, `'unmapped'`.
- Bridging (rule 5): for every organisation X with stated rows of the person, the years strictly between two stated years of X that no stated row of X covers are bridged years of X unless a stated row of another organisation or a denied row of X covers any year in that gap; bridged years enter the candidates as stated years of X.
- `Attribution.outdated_decisions(until) -> list[(person_id, year, decision source id, organisation the rules give)]`: decisions cited for a person-year the rules decide.
- Module docstring: the new rule order, verbatim from the Global Constraints.

- [ ] Failing tests: `test_bridging_fills_the_years_between_two_records`, `test_a_record_of_another_organisation_breaks_a_bridge`, `test_a_denied_row_breaks_a_bridge`, `test_old_notes_never_stop_a_bridge` (a row whose notes say "Unmapped: no public record" between two records → bridged), `test_assumed_rows_are_not_records_for_bridging`, `test_decisions_settle_only_what_the_rules_leave_open`, `test_a_decision_the_rules_decide_is_outdated`, `test_explain_names_the_rule`, `test_affiliation_tool_prints_the_rule`; the property test of today's data shapes (non-overlapping rows → first match) still holds when no gaps exist.
- [ ] Implement; full suite; **real data**: with today's rows (fill rows still present) the computed counting must equal today's for every person-year (bridging adds nothing where fill rows already cover the gap) — the reproducible-outputs test passes; commit — "Compute bridging and put decisions after the rules".

### Task 2: The difference tool and the decisions review

**Files:** create `scripts/tools/attribution_changes.py`, `scripts/tools/decisions_review.py`, tests.

**Interfaces:**
- `python -m scripts.tools.attribution_changes [--base <commit>] [--all-years]`: computes the organisation per person and active year at `--base` (default `origin/main` at the start of the branch, read through `git show` into a temporary repository copy and the model) and now; prints every difference as `person, year, before, after, rule now, activity` (activity: what makes the year active), and a summary; exit 0. Active years from the collected data (as `scripts/tools/github_evidence.active_years` and the community roles do); `--all-years` lists inactive years too.
- `python -m scripts.tools.decisions_review`: every citation of a `decision` source: person-years, status `needed` (the rules leave the year open) or `outdated` (the rules decide, with what), and the sources cited for that person-year whose `date` is after the decision's date. Markdown table to stdout.

- [ ] Failing tests on fixtures (a changed year, an unchanged year, an inactive year hidden by default; a needed and an outdated decision; a later source listed); implement; run both on the real data (expect: no differences yet; the decisions of #153 listed with their status); commit — "List changes of the attribution and the decisions to review".

### Task 3: Remove the bridged fill rows

**Files:** data (`curated/mappings/affiliations.csv`, `citations.csv`), a migration script `scripts/tools/migrate_notes.py` (archived in Task 6) with tests.

- Fill rows: `stated` rows whose notes contain `between records of <A> and <B> of the same organisation` (132). For each, the rows of the same organisation covering A and B must exist (else the row stays and is listed). Citations of the fill row whose source no neighbour row cites move to the nearer neighbour (same snippet, notes); the fill row's notes are appended to that neighbour's notes prefixed `bridged <from>-<to>: ` (lossless).
- [ ] Failing tests (incl. `test_a_fill_rows_own_source_moves_to_a_neighbour`, `test_a_fill_row_without_both_neighbours_stays`); implement; dry run lists the rows; `--write`; `attribution_changes` must list **no** difference, except the cases the design names (Kim Nguyen 2012–2013 → UW Oshkosh, and any bridge-to-assumed case, listed); `python -m scripts.tools.check`; full suite incl. reproducible outputs (regenerate the outputs only for listed, decided changes — Jens decides before the commit); commit — "Compute the bridged years instead of writing them".

### Task 4: SVN identities

- Identities whose notes contain `SVN user <name>` (25): one identity `kind=svn`, `value=<name>` per distinct (person, SVN user), citing the same source as the identity it was found on, `notes` = the phrase. `scripts/lib/changelogs.py` NameMapper keeps working (it may use the new kind; behaviour identical).
- [ ] Failing tests; implement in `migrate_notes.py`; `--write`; check; difference tool empty; full suite; commit — "Record the SVN users as identities".

### Task 5: Conflicting records and decisions

- The 9 rows with `not applied` / `Kept, not deciding`: for each record named in the note (a URL + quote), a `stated` row of the other organisation for the years the record speaks for (the source's date year, or the years the note names), citing that source with the quote as snippet when verified. Then `attribution_changes`: for each person-year where the engine now gives a different organisation or a conflict, Claude drafts a decision text (evidence, rule, proposed outcome = today's unless facts and rules say otherwise) into `scratchpad/decisions-drafts.md`.
- [ ] Implement + tests; dry run; show Jens the drafts; **stop** until Jens has created the issue "Attribution decisions" and posted (or OK'd posting) the decisions; capture each decision comment (`python -m scripts.tools.capture <comment URL> --kind decision --quote …`), cite it on the row it decides; `attribution_changes` must then list only the changes Jens accepted; check; full suite; commit — "Record the conflicting records and their decisions".

### Task 6: Docs, archive, PR

- Docs: `docs/explanation/attribution.md` (rule order; bridging computed; decisions settle what the rules leave open; the decisions issue; outdated decisions and the review list), `docs/how-to/add-an-affiliation.md` (no fill rows; when to ask for a decision; the decisions issue; `decisions_review`), `docs/reference/make-targets.md` if targets are added, AGENTS.md if a rule is affected.
- Archive `migrate_notes.py` and its tests to `archive/migration-notes-to-data/` with a README (what ran, the lists); copy the design and this plan to `archive/specs-and-plans/`.
- Verify; ask Jens before pushing; the PR lists every changed person-year and every decision with its issue comment.
