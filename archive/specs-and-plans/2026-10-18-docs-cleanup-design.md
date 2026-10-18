# Design: repository cleanup and method documentation

Date: 2026-10-18
Repository: `plone/plone-contributor-statistics` (local: `/home/jensens/ws/cdev/plone-contributor-statistics`)

## 1. Intent

The repository mixes one-off agent-written analyses, proposals and stale snapshots with the README and agent conventions.
Nobody can tell which markdown file describes the software as it is today.

This work does three things:

1. **Archive** the old agent markdown 1:1 (unchanged content, same relative paths) so history is kept but out of the way.
2. **Write `docs/`**: a Sphinx documentation in Plone documentation style that explains **how the statistics are collected and why the methods were chosen**.
3. **Set rules for future contributors and agents**: a vendor-neutral `AGENTS.md`, and the rule that a PR changing documented behavior must update the docs in the same PR.

### Readers (from the user)

- **A Plone Foundation member** who wonders why their company is at a given rank and wants to understand how the numbers come together (and how to get a mapping corrected).
- **A FOSS researcher** who wants to study the Plone community as an almost 30-year-old example: what data exists, how it was collected, what its gaps and biases are.
- **An early Plonista** who wants to look up names of people they worked with (nostalgia).
- **Agents of any vendor** (not Claude only) who work on the repo later.

## 2. Goals, non-goals, anti-goals

Goals

- Explain the collection method and the decisions behind it (the *why*), with links to the PRs and issues where each decision was made.
- Inventory every data source, the years it covers, and its known gaps.
- Describe the identity and attribution chain: GitHub account → person → organisation, per year.
- Give practical how-tos: correct a mapping, add curated data with a source, regenerate after a mapping change, find a former colleague, update docs with a PR.
- Leave a clean repo root where the current docs are obvious.

Non-goals

- **The statistics themselves**: no rankings, numbers, trend commentary or interpretation. A later report covers that.
- **Code-level documentation**: the code has comments and tests. Docs mention scripts and files only as far as needed to follow the method.
- Fixing broken Makefile targets, missing scripts, the stale Volto method or the recognition-point mismatches. They are documented as known limitations, not fixed.
- Moving generated outputs that scripts still write (would require script changes).

Anti-goals (would be a failure even if it technically works)

- Docs that restate the numbers and go stale with the next data run.
- Docs that read like a code walkthrough.
- An `AGENTS.md` that only works for Claude, or duplicates the docs.
- Changing the content of archived files, or losing any of them.
- Touching the primary data (`data/`, mapping CSVs, `reports/`) — another agent is actively working on data.

## 3. Constraints

- **Worktree only.** Another agent works heavily in the main checkout. All work happens in a new git worktree on a new branch from the current `origin/main` (at time of writing `e1fcde8`, which includes PRs #30, #73, #74, #75). Never modify the main checkout. Before opening the PR, fetch and rebase onto the newest `origin/main`.
- **No data changes.** Only markdown/docs/config files are added or moved. The only non-doc files touched: `Makefile` (docs targets), `requirements-docs.txt` (or similar), `.gitignore` (`docs/_build`), `.github/pull_request_template.md`, `.github/workflows/docs.yml` (new).
- **Plone documentation style** (skill `plone-doc-style:author`): Microsoft Writing Style Guide, American English, Diátaxis (each page exactly one quadrant), MyST markdown, one sentence per line, sentence-case headings, dashes in filenames, `index.md` in every directory, admonitions sparingly, no blog links, `{ref}` labels for cross-references.
- **Build**: Sphinx + `myst_parser` + `plone-sphinx-theme` (+ `sphinx-design`, `sphinx_copybutton`). `make docs` must build with zero warnings (`-W`). Vale and linkcheck are nice-to-have; set up `make docs-linkcheck` if cheap.
- **Tests**: per repo convention, code changes get offline pytest tests. This work adds no Python code. A light offline test that every file listed in the archive README exists is optional (builder's call).
- **Commits/PR**: commit messages and PR description end with `Assisted-by: Claude Opus 5.5` (no email; user's standing rule overrides other attribution). Link issues/PRs as clickable links in the PR text.
- **Docs describe the state of `origin/main` at build time**, not the state of the main checkout. Verify every fact against the branch before writing it.

## 4. Decided parts

### 4.1 Archive

Destination: `archive/` at the repo root, paths preserved 1:1, moved with `git mv` (history follows), content unchanged.
Add `archive/README.md`: one paragraph "historical material, not maintained, does not describe the current method; see `docs/`", plus a table of files with original path, date, and one-line summary (from the inventory below).

Files to archive:

| Original path | Why |
|---|---|
| `DATA-TRENDS.md` | one-off AI trend commentary (2025-08) |
| `FINAL-3-tier-plip-levels.md` | looks like an approved spec, but superseded: implemented PLIP levels differ |
| `comparison-plone-vs-volto.md` | one-off analysis (2025-10) |
| `contributor-levels.md` | one-off analysis; frozen contributor lists |
| `plone-core-team.md` | one-off analysis |
| `plip-contributor-level-analysis/` (all 8 files incl. `SUMMARY-level-comparison.txt` and the moved snapshot `plip-contributor-levels.md`) | one-commit proposal bundle (ed241e0) |
| `volto.md` (root) | orphaned stale copy; generator writes `reports/volto.md` |
| `team-volto.md` | orphaned input; no code reads it since 9b7595f |
| `individual_contributors.txt` | orphaned input; never read by code; superseded by `Name (independent)` entries in `organisations.csv` |
| `.claude/README.md` | agent conventions, partly outdated; still-valid content moves into `AGENTS.md` and docs |

Builder must re-check each file with `grep` against the branch before moving (nothing may read it). If anything references a file, stop and report.

Not archived (stay in place): `README.md`, `reports/*`, `STATISTICS-PAST-*.txt`, `npm-packages-*.md`/`.csv`, `npm_mapping.txt`, `requirements.txt`, all CSVs, all data.

### 4.2 Documentation tree

```
docs/
├── conf.py
├── index.md                              # landing page, grid cards per quadrant, "who is this for"
├── glossary.md                           # Unmapped, independent, override, PLIP, curated data, bot, …
├── explanation/
│   ├── index.md
│   ├── scope.md                          # what is measured and why
│   ├── history-and-coverage.md           # 30 years: CVS → SVN → Git, what is trustworthy from when
│   ├── attribution.md                    # from GitHub account to person to organisation
│   ├── counting-rules.md                 # commits, PRs, merge commits, bots, repos, time attribution
│   ├── pr-interactions.md                # reviews/comments, created-year rule, GraphQL, bots
│   ├── curated-community-data.md         # collected vs curated, "no data without a source"
│   ├── community-recognition.md          # what is verifiable about the program; open #56
│   ├── known-limitations.md              # gaps, biases, stale parts, open questions
│   └── method-history.md                 # dated decision log with PR/issue links
├── reference/
│   ├── index.md
│   ├── data-sources.md                   # table: source, origin/API, years, script, output, make target
│   ├── data-files.md                     # every data/output file: producer, columns, granularity
│   ├── mapping-files.md                  # organisations.csv, overrides, bot_accounts, excluded_repositories, …
│   ├── recognition-files.md              # community-recognition points/levels CSVs, report; columns only
│   └── make-targets.md                   # targets grouped by purpose, with status (works / broken)
├── how-to/
│   ├── index.md
│   ├── correct-an-organisation-mapping.md
│   ├── add-curated-community-data.md
│   ├── regenerate-after-a-mapping-change.md
│   ├── find-a-contributor.md             # nostalgia reader: where names live, how to search
│   └── collect-data-again.md             # token, rate limits, checkpoints, run-stats-all-years
└── contributing/
    ├── index.md
    └── documentation.md                  # the docs-update rule, how to build docs, style pointer
```

No tutorials (no reader needs a guided learning path here).

Page intent (each page exactly one Diátaxis quadrant):

- **explanation/scope.md** — Why the `plone` GitHub org is the core source; why only merged PRs (README: reflect actual contributions); why default-branch commits only; why archived repos are included (history belongs to the years it happened, #36/#57) and why an explicit exclusion list with reasons replaces automatic exclusion (#60); what is deliberately outside (zopefoundation and other Foundation projects pending #58; non-GitHub work #35, except the curated categories).
- **explanation/history-and-coverage.md** — Git history reaches back to 2002 via CVS → SVN → Git (svn-migrate 2011); 2001 not in Git; no PRs before ~2011; SVN-era `@localhost` emails without linked accounts are dropped (37% of CMFPlone 2003 commits, #69); pre-egg history on release branches missing (#68; unmerged branch `history-all-branches` addresses it); CVS initial imports and mass commits distort early years (#67); pre-2010 organisations largely unsourced (#70). What a researcher can and cannot conclude per era. Pre-2020 curated data (conference organisers 2003–2019).
- **explanation/attribution.md** — The rule: attribute to the organisation that **sponsors the contributor's time on Plone, in the year of the contribution**. `organisations.csv` = current affiliation; `organisation_mapping_overrides.csv` = historical exceptions (~1%). Why Independent was split into Unmapped and `Name (independent)` (#53/#64: Independent mixed volunteers with unknowns and appeared as one big organisation). Why Unmapped is not ranked (f83913b). "A mapping needs a source or a confirmation; when in doubt, stays unmapped." Corrections come from people themselves via PRs (#47, #49, #55). Case-sensitive lookup caveat. Multi-year summaries sum per-year files, so a person who moved is split across organisations.
- **explanation/counting-rules.md** — Commits: GitHub account linked to author email; committer date decides the year (rebase can move a commit); merge commits excluded because merging is not code creation and counts would depend on merge strategy (#39/#77c47c7; review/merge credit deferred to #61). PRs: credited to the opener, by merge date, any base branch, backports included (#42/#62). Bots excluded (`*[bot]`, account type, `bot_accounts.csv`). Why collection is once per repo for the whole range (ff1d5f8/#63: per-person queries cost ~15,000 requests per year and missed contributors beyond the first 500). Why errors stop the run instead of being recorded as zero (#41/#59).
- **explanation/pr-interactions.md** — What is counted (issue comments, code review comments, submitted reviews, first response time excluding author and bots); PRs in any state (engagement, not contribution); year = PR creation year (#37/#54); why GraphQL (#74: REST needed ~85,000 calls/17 hours and lost data silently); why bots are excluded (pre-commit-ci ~a third of 2024 PRs; bot comments made 0-hour response times); 2010–2025 re-collected (faae81d).
- **explanation/curated-community-data.md** — Second kind of data: hand-curated under `data/community-contributions/` (release managers, team leaders, strategic sprints, podcasts, World Plone Day, conference organisers and trainings, board). Principle: no data without a public source; memories count when confirmed by participants. Why fetch scripts were removed (would overwrite corrections: 2805484, 353de64). Definitions decided: strategic sprint = designated by the Board (Board minutes); release managers = approved by the Board / Release Team page; only in-person WPD events; organisation per row as of that year, no "Independent". Board data still heuristic and without Source column.
- **explanation/community-recognition.md** — "About the Community Recognition Program". Only what is verifiable: what the program is; that the original authors published the levels on plone.org (cite the page); which inputs the repo holds (`community-recognition-points.csv`, `community-recognition-levels.csv`, curated data, code summaries, PLIPs); that the published levels cannot currently be reproduced from the repo and that code and points CSV disagree (trainings 6 vs 4 points, sprint and WPD splitting, PLIP all-time vs 5 years) — link #56. **No numbers, no reconstruction of how the published result was computed.** When #56 is resolved, that PR updates this page (docs rule). The PLIP tier scripts (`generate_plip_3tier_levels.py`, `analyze_plip_contributor_levels.py`) are mentioned as remnants of the archived proposals.
- **explanation/known-limitations.md** — Consolidated list: Volto uses an older method and stale data (before #42/#39 fixes; `/contributors` max 500; hard-coded `main`; still shows "Independent"); PLIP caveats (3 repos, "closed" as proxy, all-time, #14, #44, missing generator, old org names); community recognition not reproducible from the repo (#56) and code vs `community-recognition-points.csv` mismatches; npm/PyPI are one-off snapshots with heuristic org detection; broken Make targets and missing scripts; Flourish charts use commits and outdated name maps; `yearly_activity_analysis.py` counts Unmapped as an organisation. Link the open issues. **Each item states the limitation and its effect on interpretation, not a number.**
- **explanation/method-history.md** — Kept as a chronological journal (user decision, 2026-10-18). Purpose: lets a reader see when the method changed, so data collected before and after a fix is not compared naively. Topical pages carry the *why* of each decision briefly and link here for the sequence; the journal links back to topical pages. Prose grouped by phase (2025-08 to 2026-03 initial build by Timo Stollenwerk; 2026-06 community data by Mikel Larreategi; 2026-10 method review by Jens W. Klein). Each entry: date, decision, why, link to PR/issue/commit. Source material: appendix A.
- **reference/data-sources.md** — One table, one row per source (appendix B), columns: source, origin/API, years covered, script, output, make target, method status.
- **reference/data-files.md** — Every committed data/output file pattern: producer, columns, one row = what, year semantics. No numbers.
- **reference/mapping-files.md** — `organisations.csv` (format, sorted case-insensitively, one login once, `;` separator, canonical names), `organisation_mapping_overrides.csv` (`github_username,organisation,from_year,to_year`), `bot_accounts.csv`, `excluded_repositories.csv`, `mapping-github-username-to-fullname.csv` (manual aid, no script uses it), `npm_mapping.txt`. Include the CSV conventions from `.claude/README.md` that are still valid (semicolons for multi-value cells, quoting commas, canonical organisation spellings — verify each against `organisations.csv`).
- **reference/make-targets.md** — Grouped by purpose, mark broken targets (`run-plip-organisations`, `generate-plip-report`, `pypi-packages`, `run-all`) — verify on the branch.
- **how-to/correct-an-organisation-mapping.md** — For the Foundation member: decide current vs past affiliation → edit `organisations.csv` or add an override row → provide source/confirmation in the PR → run `make test` → regenerate (link) → open PR.
- **how-to/add-curated-community-data.md** — Add or correct a row in `data/community-contributions/YYYY-*.csv` with Source; organisation as in `organisations.csv` for that year; run format tests.
- **how-to/regenerate-after-a-mapping-change.md** — Which targets to run in which order (no re-collection needed).
- **how-to/find-a-contributor.md** — Where names and logins live (per-year contributor CSVs, curated CSVs, `organisations.csv`, full-name mapping), how to search them (`grep`, GitHub search on the repo), what the earliest years can show. No lists of people in the page.
- **how-to/collect-data-again.md** — Token in `.env`, rate limits, checkpoint behavior, exit codes, `run-stats-all-years`, `pr-interactions-all-years`.
- **contributing/documentation.md** — The rule (below), how to build (`make docs`), style pointer.

Facts in pages must be verified against the branch (code, git log, `gh issue view`). The appendices are research notes from 2026-10-18 at `faae81d`, not ground truth.

### 4.3 Docs-update rule

Rule text (same wording everywhere): "A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request."

Placed in:

- `AGENTS.md` (hard rule).
- `docs/contributing/documentation.md` (for humans).
- `.github/pull_request_template.md` with a checkbox: "Docs updated, or not needed because: …".

No CI enforcement (user decision).

### 4.4 Agent instructions

- `AGENTS.md` at the repo root (vendor-neutral convention read by Codex, Cursor, Gemini CLI, Copilot, Aider, Claude Code and others). Short. Contents:
  - Purpose of the repo in two sentences; link to `docs/`.
  - Setup and commands (`make setup`, `make test`, `make check`, `make docs`).
  - Layout: where code, data, curated data, reports, docs, archive live.
  - House rules: use a git worktree when other agents may be active; offline pytest tests for code changes, format checks for data; no data without a source; mapping changes need a source or confirmation; keep `organisations.csv` sorted; canonical organisation names; never commit `.env`; the docs-update rule; attribution footer `Assisted-by: <model>` (no email) in commits, PRs and issues.
  - `archive/` is historical, never edit or rely on it.
  - Specs and plans of future work are drafted outside `docs/` and, as the last step before the PR, added unchanged to `archive/specs-and-plans/` (user rule, 2026-10-18). This work's own spec and plan go there too.
  - It links to docs pages instead of repeating them.
- `CLAUDE.md`: one line `@AGENTS.md` (Claude Code import syntax) and nothing else.

### 4.5 README

Shrink `README.md` to: what the project is, who it's for, quick start (`make setup`, `make test`, `make docs`), links into `docs/`. Method sections move into the docs. Drop stale figures (contributor/organisation counts, PLIP numbers, "current year 2025").

### 4.6 State of main to document

- PR #73 (GitHub Actions tests, `.github/workflows/tests.yml`) is merged. Docs get their own workflow (see 4.7), `tests.yml` stays untouched.
- PR #75 (`history-all-branches`) is **merged** (`e1fcde8`). The docs describe its method: commits read from local bare treeless clones (`git_history.py`, `.cache/repositories/`); default-branch commits plus release-branch commits older than the default branch's first commit (later ones are mostly backports with another SHA, not counted twice; backport PRs still count as PRs); email → GitHub account via GraphQL; GitHub Apps are bots. Fixes #68, part of #67. Affects scope, counting rules, history-and-coverage, collect-data-again, data sources, data files, method history, and the method-changes framing in known limitations (#68 is no longer a gap; #67, #69, #70 remain). Read the PR description and `git_history.py` on main, do not rely on the appendix, which predates it.
- Still open, waiting for input from Mikel Larreategi (erral): PR #34 (`community-recognition-weighting`, year weighting) and branch `split-code-and-community-contributions` (no PR yet, Beethoven Sprint 2026). Mention both as pending on the community recognition page; do not describe their content as current.
- Before opening the PR, fetch, rebase and re-verify every page that touches collection or recognition against the newest `origin/main`. If a method PR lands during the work, stop and ask the user.

### 4.7 Autobuild and publish to GitHub Pages

- New workflow `.github/workflows/docs.yml`, separate from `tests.yml` (Pages needs its own permissions and concurrency group).
- **On every pull request** (and push to any branch): build the docs with `make docs` (warnings as errors). A broken build fails the check. This is a build check, not the docs-update rule (which stays unenforced).
- **On push to `main`** (and `workflow_dispatch`): build, upload the HTML with `actions/upload-pages-artifact`, deploy with `actions/deploy-pages`. Permissions `pages: write`, `id-token: write`, `contents: read`; environment `github-pages`; concurrency group `pages`, no cancel of a running deploy.
- Use the same action major versions as `tests.yml` (checkout and setup-python v7, Node.js 24, per 6b0d02e); pick current majors for the Pages actions.
- Published URL: `https://plone.github.io/plone-contributor-statistics/`. Set it as `html_baseurl` in `conf.py`, and link it from `README.md`, `AGENTS.md` and the GitHub repo "About" (the last only after confirmation).
- **Manual step, outward-facing:** GitHub Pages must be enabled with source "GitHub Actions" (repo Settings → Pages, or `gh api -X POST repos/plone/plone-contributor-statistics/pages -f build_type=workflow`). The builder must not do this without the user's confirmation; it needs admin rights on the repo. Until then the deploy job fails; the PR description says so.
- Optional: `make docs-linkcheck` as a separate, non-blocking job.

## 5. Left to the builder

- Exact page wording, headings and order within pages; `html_meta` on landing and section index pages only.
- `conf.py` details (theme options, repository URL `https://github.com/plone/plone-contributor-statistics`, `myst_enable_extensions` per the skill), whether to use `requirements-docs.txt` or a `docs` section in an existing file, venv handling in the `docs` Make target.
- Whether to add `make docs-linkcheck` / Vale.
- Glossary entries.
- Splitting or merging pages if one gets too long or too thin, as long as each stays in one quadrant.
- Commit granularity (suggested: archive move; docs scaffold; explanation; reference; how-to; AGENTS/CLAUDE/PR template/README).
- Draft list of issues for broken targets and missing scripts in the PR description — **do not file issues without the user's confirmation** (outward-facing).

## Appendix A — decision log raw material (from git history and PRs, 2026-10-18)

Initial build (Timo Stollenwerk, mostly no commit bodies):

- f454b4c 2025-08-18 first collector; bfbaeb8 org guessing from profiles/email domains, later replaced by manual mapping.
- a00ffa9 2025-08-19 "company" → "organisation"; d0b6fe9 `analyze_independent_contributors.py` to find unmapped people worth researching.
- 1217ba3 2025-08-20 summaries sorted by PRs instead of commits (no rationale recorded).
- 7402c8f 2025-08-22 individuals moved out of org mapping into `individual_contributors.txt`.
- 9b7595f 2026-03-12 Volto stats cover all Volto contributors, not the team list.
- 6120217 / 0987a25 2026-03 generated CSVs moved to `data/` (#7).
- 5465435 2026-03-13 PR #10 single mapping file `organisations.csv`.
- 369107e, 65ae5f0, 65451e5, f604d63 2026-03-14 PRs #12, #13 only merged PRs; PR interactions count all PRs (engagement).
- 5d02b5c 2026-03-15 `/stats/contributors` → `/commits?sha=<default branch>` ("accurate and up-to-date commit counts without caching issues").
- 3388c54 only in-person WPD events; 811c78d no podcasts in 2025; 26598df UNAM variants merged; 928ba64 Steve Piercy as individual.
- 949296c 2026-03-20 PR #17 / issue #16 yearly override file.
- 0681176 2026-05-22 PR #20 / issue #19 recognition levels 6 → 5 tiers to balance organisations per tier; b9ec46d 2026-06-24 PR #21 "as discussed in Bonn".
- PR #23 2026-06-24 five-year reports. PRs #25–#33 2026-06-25 community data 2020–2024 (Mikel Larreategi).

Method review (Jens W. Klein, 2026-10):

- 6b5345c (#38) login typo sent Wildcard Corp activity to Independent → login format test.
- f398ee6, b735b3c, 41df3b7, ec97300 conference organisers 2003–2019 with plone.org sources; participant confirmations as sources.
- 207840e / ba8dc4f PRs #47, #49 Syslab corrections from the people themselves.
- c9b56ee (#37, PR #54) PR interaction paging bug; assign by creation year; first pytest tests and `make test`.
- 0a208b5 podcast 2024 correction; one host per row.
- 2805484 / 7c7af5c unsourced WPD 2020 removed; placeholder fetch scripts removed.
- 2cf7a47, 2f9ff51 strategic sprint definition (Board designated).
- d2ee1e7 Sorrento Fan Zone credited to organisers' organisations (they sponsored the time).
- eeba894 team leaders aligned with Board minutes and team pages; c8119e5 release managers per Board / Release Team page.
- 7e379fe, aa880f0, 7ed781a, 40fe9ae PR #55 Zest / Py76 overrides: sponsoring employer per year.
- 82ad56c, d99da01, 4a45fd8 (#40, PR #51) scripts read stale root files after move to `data/`; all org files regenerated.
- 6222d83 (#36, PR #57) archived repos collected; explicit exclusion list with reasons; 634b53d same selection for PR interactions; list open for review #60.
- bb87697 (#41, PR #59) API errors no longer recorded as zero; wait on rate limits; checkpoints and exit 1 on failure.
- 77c47c7 (#39) merge commits not counted; review/merge credit deferred to #61.
- b19858e (#42, PR #62) merge date everywhere, backports count.
- ff1d5f8 PR #63 collect once per repo for the whole range; validated against old per-person queries.
- 9c1ede6 (#53, PR #64) Independent → Unmapped + `Name (independent)`; 42 contributors mapped after review.
- f83913b Unmapped not ranked in summaries.
- 32e99cb (#36, #43, PR #65) all years 2003–2025 re-collected.
- 9414874 PR #74 PR interactions via GraphQL; bots removed; six bots added.
- faae81d (fixes #37) PR interactions 2010–2025 re-collected.
- 353de64 PR #30 trainings checked against conference websites; fetch script removed; open questions #66.

Open issues relevant to limitations: #14, #35, #44, #45, #46, #56, #58, #60, #61, #66, #67, #68, #69, #70, #71, #72. Open PRs/branches with method changes: #73 (CI), #34 (recognition weighting), `history-all-branches` (#68), `split-code-and-community-contributions`.

## Appendix B — data sources (research notes)

| Source | Script | Origin | Years | Output |
|---|---|---|---|---|
| Core commits + merged PRs | `plone_contributors.py` (+ `github_api.py`) | REST, all `plone` org repos minus `excluded_repositories.csv` | 2003–2025 | `data/YYYY-plone-contributors.csv` |
| Organisation aggregation | `organisation_stats.py` | per-year contributors + mapping files | per year | `data/YYYY-plone-organisation-contributors.csv` |
| Multi-year summaries | `multi_year_summary.py` | per-year files | 3/5/10 years | `summary-past-*.csv`, `STATISTICS-PAST-*.txt` |
| PR interactions | `plone_pr_interactions.py` | GraphQL + REST fallback | 2010–2025 | `data/YYYY-plone-pr-interactions.csv`, `reports/github-pr-interactions-report-YYYY.md` |
| Volto | `volto_stats.py` | REST `/contributors`, Search API per person | 2016–2025 | `data/YYYY-volto-stats.csv`, `reports/volto.md` |
| PLIPs | `plone_plips.py` | issues with PLIP label in CMFPlone, volto, plone.restapi | 2013–2025 | `plone-plips.csv`, `plone-plips-detailed.csv` |
| PyPI | `pypi_package_statistics.py` | pypi.org | snapshot | not committed |
| npm | `npm_package_stats.py` + `npm_mapping.txt` | npm registry | snapshot 2025-08-20 | `npm-packages-*` |
| CMFPlone releases | `fetch_cmfplone_releases.py`, `filter_releases.py` | REST releases | 2022–2025 | `cmfplone-releases*.csv` |
| Board of Directors | `fetch_board_members.py` | plone.org REST, heuristic org | 2020–2025 | `data/community-contributions/YYYY-board-of-directors.csv` |
| Curated community data | manual | Board minutes, plone.org, conference sites, Wayback, YouTube | conferences 2003–2025, others 2020–2025 | `data/community-contributions/YYYY-*.csv` |
| Community recognition | `generate_community_recognition_report.py` | curated 2025 data + 5-year summary + PLIPs | 2025 | `reports/community-recognition.md` |
| Graphs / Flourish | `yearly_activity_analysis.py`, `generate_yearly_graphs.py`, Flourish scripts | per-year files | various | `graphs/`, `data/*flourish*.csv` |
