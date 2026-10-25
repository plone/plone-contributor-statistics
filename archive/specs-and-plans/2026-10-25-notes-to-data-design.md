# From notes to data: design (plan 5)

Date: 2026-10-25. State: `origin/main` 1c64265 (after #178). Builds on `archive/specs-and-plans/2026-10-22-sources-and-events-design.md` (migration step 3, "reviewed restructuring") and the computed attribution of #175 (`scripts/lib/model/attribution.py`).

## Intent

The affiliation notes still carry evidence and conclusions as prose: bridged years, reviewed "stays Unmapped" decisions, conflicting records "not applied", tie-break reasoning, and "SVN user …" phrases in identity notes. They should become data the engine and the checks can use, so that the registers say what records say and the engine draws the conclusions by the documented rules. Decisions become public records in one place.

## What Jens decided

- **Bridging is computed.** Rationale: if a record says a person worked for X in 2017 and another in 2019, it is very unlikely they didn't in 2018. The rule stays as documented (two records of one organisation cover the years between, no distance limit, unless a record of another organisation lies between). The bridged fill rows go; the engine fills the years.
- **All note categories become data** (table below).
- **Decisions live in one GitHub issue**, "Attribution decisions": one comment per decision. A decision can be stated by Jens, by someone else, or by the person or organisation in question. A comment by the person is also their own statement.
- **Old notes never stop a bridge.** The "no public record, stays Unmapped" notes (#86) are probably outdated; bridging always follows the documented rule (first case: Kim Nguyen 2012–2013 counts for UW Oshkosh, listed in the PR).
- **Recorded facts and the rules come before decisions.** New rule order: (1) proposed ignored, denied rows remove their organisation (a denial is a recorded fact); (2) the rules — one organisation left (stated over assumed), change year, bridging, tie-breaks 6a–6d; (3) decisions settle only what the rules leave open; (4) else a conflict. A decision that facts and rules now decide is no longer applied and is listed as outdated.
- **A review list of decisions.** Because older decisions were made with fewer recorded facts, a report lists every decision with its person-years: still needed (the rules leave the year open), outdated (the rules now decide), and the sources recorded after the decision's date that bear on those person-years — for Jens to review.
- **Credit is never changed by this project** (memory rule): restructuring may change which organisation a person counts for only where a decision says so, and every such change is listed for Jens.

## The categories (origin/main, 1,428 affiliation rows, 333 with notes)

| Notes | Rows | Becomes |
|---|---|---|
| "between records of A and B of the same organisation" | 132 fill rows | removed; computed bridging (rule 5) |
| "N–M Unmapped: no public record" | 58 | stay as historical notes (*Claude's call*: a `denied` row would claim "not at X", which the notes don't record, and has no effect on counting); never block a bridge; the evidence tools keep proposing those years when they find something |
| "not applied, the verified row stands" / "Kept, not deciding" | 9 | a `stated` row of the other organisation, citing the record named in the note; if the engine then picks the other organisation, a decision in the issue keeps today's |
| tie-break reasoning, "(Jens, #…)" | ~11 | nothing if the engine reaches the same result by its rules; else a decision in the issue |
| "SVN user …" in identity notes | 25 | identities of kind `svn` (value = the SVN user), citing the same source |
| "not verified", "current entry without a record of 2026", "range from the current entry" | 104/53/51 | stay as notes (status `assumed` already says it) |

## Goals

- The registers hold readings of records; conclusions (bridges, tie-breaks) are computed; reviewed decisions are cited sources.
- **Numbers identical** except where a listed decision changes them. Every difference between today's counting and the new counting is listed per person and year before anything is written.
- Lossless: the notes text of every touched row is kept (moved to the row that now carries the evidence, or kept on the remaining row); no URL or quote lost.

## Non-goals

- No new research, no new evidence beyond what the notes already cite.
- No change of rules; bridging and tie-breaks as documented.
- No trimming of the `assumed` rows (Jens decided not to trim yet).

## Engine and checks

- Rule 5 (bridging) computed in `Attribution`: between two years covered by `stated` rows of organisation X (records), the years between count for X when no `stated` row of another organisation covers any of them and no `denied` row of X covers them. Bridged years then act like stated years of X for the later rules (*builder's call*, keeps today's numbers). Assumed rows are not records for bridging (the difference list shows any bridge that only reaches an assumed row; Jens decides with it). Bridging is computed for every year, active or not; the difference list is limited to active person-years.
- The rule order changes as Jens decided (denials, rules, decisions, conflict); `decision_errors`/`supersedes` stay; a new `outdated_decisions()` lists decisions the rules now decide.
- The bridged years are visible: the engine reports why a year counts (`rule` per person-year), the `affiliation` tool prints "bridged", the community page may show it later (out of scope).
- Checks: an `svn` identity value is unique within its kind (several SVN users of one person, e.g. aclark, maurits, become one identity each). Three fill rows cite a source their end rows don't cite (aadc4b504, ad2e3b6fe, afdea5bc6): their citations move to the neighbouring record rows, so no source is lost.
- Report: `python -m scripts.tools.decisions_review` lists every decision with its person-years, status (needed / outdated) and the sources dated after the decision that bear on them.

## Decisions workflow

1. The tool lists every person-year whose counting differs from today's, and every conflict the new rows create.
2. Claude drafts one decision text per case (evidence, the rule, the proposed outcome). Jens (or the person, or someone else) posts it in the issue — Claude posts with `gh` only on Jens's explicit OK per batch.
3. The decision comment is captured as a source (kind `decision`) and cited by the affiliation it decides; `supersedes` names an earlier decision when it overrules one.

## Migration

One reviewed PR, in steps that each keep `make check` green:
1. Engine: computed bridging + the `rule` explanation; the difference list tool (old counting from git vs new).
2. Data: remove the 132 fill rows; difference list must be empty except listed cases.
3. Data: the 25 SVN identities (the 58 Unmapped notes stay as notes).
4. Data: the 9 conflicting records → stated rows; difference list → decision drafts → Jens posts → decisions cited → difference list empty.
5. Docs (attribution.md: bridging computed, decisions issue; add-an-affiliation.md: the decisions workflow), archive the migration scripts.

## Builder notes

- Whether a bridge may end at an `assumed` row is to be settled by the data: list the bridges that only reach an assumed row; Jens decides with the list (rule says "records").
- The two existing decision sources (comments on #153, cited by 9 denied rows) stay where they are; the new issue is for decisions from now on; the docs say decisions may also sit in older PR comments.
- The issue must exist before step 4; its URL goes into the docs.
