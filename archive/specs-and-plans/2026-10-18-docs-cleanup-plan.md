# Repository cleanup and method documentation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Archive the old agent markdown 1:1, add a Sphinx/MyST documentation in Plone style under `docs/` that explains how the statistics are collected and why, publish it to GitHub Pages from CI, and add vendor-neutral agent instructions with a docs-update rule.

**Architecture:** Pure docs/config change on a new branch in its own git worktree. `git mv` for the archive; Sphinx + `myst_parser` + `plone-sphinx-theme` under `docs/`, built by `make docs` with warnings as errors; a separate GitHub Actions workflow builds on every PR and deploys on `main`. One offline pytest module keeps the archive and the docs' references to files and Make targets honest.

**Tech Stack:** Sphinx 9, myst-parser, plone-sphinx-theme 1.4, sphinx-design, sphinx-copybutton, sphinxcontrib-mermaid, GitHub Actions (`actions/upload-pages-artifact`, `actions/deploy-pages`), pytest.

**Spec:** `/tmp/claude-1000/-home-jensens-ws-cdev-plone-contributor-statistics/19399b3a-84cc-4bda-a99b-df8eda16c26e/scratchpad/2026-10-18-docs-cleanup-design.md` (sections cited as "spec §N"). Read it before starting; page contents are specified there, not repeated here.

## Global Constraints

- Work only in the worktree `/tmp/claude-1000/-home-jensens-ws-cdev-plone-contributor-statistics/19399b3a-84cc-4bda-a99b-df8eda16c26e/scratchpad/wt-docs` on branch `docs-method-and-archive`, created from the newest `origin/main` (at planning time `e1fcde8`). Never modify `/home/jensens/ws/cdev/plone-contributor-statistics` itself — another agent works there.
- Never change `data/`, `reports/`, any CSV, any `*.py` script in the root, or `tests.yml`. Allowed non-doc files: `Makefile`, `requirements-docs.txt`, `.gitignore`, `.github/pull_request_template.md`, `.github/workflows/docs.yml`, `tests/test_docs_and_archive.py`.
- Plone documentation style (load skill `plone-doc-style:author` before writing any page): American English, active voice, "you", **one sentence per line**, sentence-case headings, dashes in filenames, `index.md` per directory, each page exactly one Diátaxis quadrant, `(label)=` above every H1, cross-references with `{doc}`/`{ref}`, at most 1–2 admonitions per page, no blog links.
- Docs explain method and the *why*. **No statistics**: no rankings, no counts of commits/PRs/people/organisations, no trend statements. Exception: numbers that describe the method itself (e.g. "about 85,000 API calls", "37% of CMFPlone 2003 commits had no linked account") may appear in explanation pages when they justify a decision.
- Every fact is verified against the worktree (`git log`, `grep`, the code, `gh pr view`/`gh issue view`) before it is written. The spec appendices are research notes from before PR #75, not ground truth.
- Link PRs/issues as `[#75](https://github.com/plone/plone-contributor-statistics/pull/75)` / `.../issues/NN`.
- Docs-update rule, verbatim wherever it appears: "A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request."
- Published URL: `https://plone.github.io/plone-contributor-statistics/`.
- Every commit message ends with a blank line and `Assisted-by: Claude Opus 5.5` (no email, no Co-Authored-By).
- Do not file issues, push, open the PR, or enable GitHub Pages without the user's explicit confirmation.

## Review Focus

- A file path or `make` target named in the docs that does not exist on main (stale docs) → `test_docs_reference_existing_files` and `test_docs_reference_existing_make_targets` fail (Task 2).
- An archived file that something still reads, or an archived path that reappears in the root → `test_archived_files_not_referenced` / `test_archive_readme_lists_every_file` fail (Task 1).
- A page not in any toctree, a broken `{ref}`/`{doc}`, or a bad MyST directive → `make docs` fails (warnings as errors), locally and in CI (Tasks 2, 3).
- Deploy job running on pull requests or forks → `docs.yml` deploy job has `if: github.event_name != 'pull_request' && github.repository == 'plone/plone-contributor-statistics' && github.ref == 'refs/heads/main'` (Task 3).
- Statistics creeping into the docs (anti-goal) → reviewer greps `docs/` for digits outside dates, years, PR/issue numbers and code blocks in the final task (Task 9 step 3).

---

### Task 0: Worktree and docs environment

- [ ] **Step 1: Create the worktree** (use superpowers:using-git-worktrees conventions)

```shell
cd /home/jensens/ws/cdev/plone-contributor-statistics
git fetch origin
git worktree add /tmp/claude-1000/-home-jensens-ws-cdev-plone-contributor-statistics/19399b3a-84cc-4bda-a99b-df8eda16c26e/scratchpad/wt-docs -b docs-method-and-archive origin/main
```

Expected: new worktree at `origin/main`; `git -C <wt> log -1 --oneline` shows the newest main merge.

- [ ] **Step 2: Create a venv outside the worktree** with Python 3.12 (Sphinx 9 needs ≥3.12, plone-sphinx-theme needs <3.14): `python3.12 -m venv <scratchpad>/venv-docs`, then `pip install -r requirements.txt pytest pytest-timeout` in the worktree. All later commands run with this venv active and the worktree as cwd.

- [ ] **Step 3: Baseline:** `make test` → all pass. Record the count.

### Task 1: Archive

**Files:**
- Move (`git mv`, content unchanged, path kept under `archive/`): `DATA-TRENDS.md`, `FINAL-3-tier-plip-levels.md`, `comparison-plone-vs-volto.md`, `contributor-levels.md`, `plone-core-team.md`, `plip-contributor-level-analysis/` (whole directory), `volto.md`, `team-volto.md`, `individual_contributors.txt`, `.claude/README.md` → `archive/.claude/README.md`
- Create: `archive/README.md`
- Test: `tests/test_docs_and_archive.py`

**Interfaces:**
- Produces: `archive/README.md` contains a markdown table whose first column is the original path in backticks (e.g. `` `DATA-TRENDS.md` ``, `` `plip-contributor-level-analysis/` ``). The test parses that column.

- [ ] **Step 1: Re-check readers on the branch.** For each file: `grep -rn --include='*.py' --include=Makefile --include='*.yml' -F '<basename>' .` excluding `archive/`. Expected only known harmless hits: `analyze_plip_contributor_levels.py` writes a *new* `plip-contributor-levels.md` in the root (writer, not reader); cross-links inside `plip-contributor-level-analysis/`. Any other hit: stop and report.

- [ ] **Step 2: Write the failing tests** in `tests/test_docs_and_archive.py` (module docstring: `"""Checks that keep the archive and the docs honest (docs cleanup)."""`; `ROOT = Path(__file__).resolve().parent.parent`):

```python
ARCHIVED = ['DATA-TRENDS.md', 'FINAL-3-tier-plip-levels.md', 'comparison-plone-vs-volto.md',
            'contributor-levels.md', 'plone-core-team.md', 'plip-contributor-level-analysis',
            'volto.md', 'team-volto.md', 'individual_contributors.txt', '.claude/README.md']

@pytest.mark.parametrize('name', ARCHIVED)
def test_archived_file_moved(name):
    assert (ROOT / 'archive' / name).exists()
    assert not (ROOT / name).exists()

def test_archive_readme_lists_every_file():
    # every top-level entry of archive/ except README.md appears in the table
    ...  # assert set(listed) == set(on_disk)

def test_archived_files_not_referenced():
    # no *.py in the root, Makefile, or .github/workflows/*.yml mentions an archived
    # name as a path it reads; allow analyze_plip_contributor_levels.py writing
    # its default output 'plip-contributor-levels.md' (a writer, see archive/README.md)
```

`test_archive_readme_lists_every_file` compares the backticked paths in column 1 (strip trailing `/`) with `{p.name for p in (ROOT/'archive').iterdir() if p.name != 'README.md'}`, treating `.claude` as listed when `.claude/README.md` is.

- [ ] **Step 3: Run** `python -m pytest tests/test_docs_and_archive.py -v` → FAIL (files not moved).

- [ ] **Step 4: `git mv` all files**, then write `archive/README.md`: H1 "Archive"; one paragraph "Historical material: one-off analyses, proposals and snapshots, mostly written with AI agents in 2025–2026. Not maintained. It does not describe the current method; see the documentation at https://plone.github.io/plone-contributor-statistics/ and `docs/`."; table `| Original path | Added | Summary |` with the date from `git log --diff-filter=A -1 --format=%ad --date=short -- <path>` and the one-line summary from spec §4.1. Note under the table that `make analyze-plip-levels` still writes `plip-contributor-levels.md` to the root. If `.claude/` is now empty, it disappears; leave it so.

- [ ] **Step 5: Run** `make test` → all pass.

- [ ] **Step 6: Commit** `git add -A archive tests/test_docs_and_archive.py` plus the deletions; message "Move the old analyses and agent notes to archive/" with a body listing why (spec §1) and the footer.

### Task 2: Docs scaffold, build, and reference checks

**Files:**
- Create: `requirements-docs.txt`, `docs/conf.py`, `docs/index.md`, `docs/glossary.md`, `docs/explanation/index.md`, `docs/reference/index.md`, `docs/how-to/index.md`, `docs/contributing/index.md`
- Modify: `Makefile` (targets + `.PHONY` + `help`), `.gitignore`
- Test: `tests/test_docs_and_archive.py`

**Interfaces:**
- Produces: `make docs` (HTML to `docs/_build/html`, warnings are errors), `make docs-install`, `make docs-linkcheck`, `make docs-clean`. Section indexes each hold a `{toctree}` with `:maxdepth: 1`; later tasks add their pages to the toctree of their section.
- Produces: test helpers `docs_pages() -> list[Path]` (all `docs/**/*.md` except `_build`) and `KNOWN_MISSING: set[str]` (paths and targets the docs name deliberately because they are broken or missing; each entry has a comment pointing to `docs/explanation/known-limitations.md`).

- [ ] **Step 1: Write the failing tests:**

```python
def test_docs_reference_existing_files():
    # every inline-code span in docs/**/*.md that looks like a repo path
    # (regex r'`([\w./*-]+\.(?:py|csv|txt|md|yml|ini))`'), with 'YYYY' replaced by '*',
    # globs to at least one file under ROOT, unless it is in KNOWN_MISSING
    # or starts with 'archive/' and exists there

def test_docs_reference_existing_make_targets():
    # every r'`make ([a-z0-9-]+)' in docs has a rule r'^<target>:' in the Makefile,
    # with 'YYYY' replaced by a concrete year present in the Makefile, unless in KNOWN_MISSING
```

Start `KNOWN_MISSING` empty; entries are added only when a page documents a broken target or missing script (Task 6, known limitations), e.g. `plip_organisation_stats.py`, `generate_plip_report.py`, `pypi_package_stats.py` — verify each is still missing on main before adding.

Add a third test `test_docs_exist`: `assert (ROOT / 'docs' / 'index.md').exists()`.

- [ ] **Step 2: Run** `python -m pytest tests/test_docs_and_archive.py -v` → `test_docs_exist` FAILS (the two reference tests pass vacuously while `docs/` is absent).

- [ ] **Step 3: Create the scaffold.**
  - `requirements-docs.txt`: `plone-sphinx-theme`, `myst-parser`, `sphinx-design`, `sphinx-copybutton`, `sphinxcontrib-mermaid` (no pins; let the theme constrain Sphinx).
  - `docs/conf.py`: project "Plone Contributor Statistics", author "Plone Foundation and contributors", `extensions = ["myst_parser", "sphinx_copybutton", "sphinx_design", "sphinxcontrib.mermaid"]`, `myst_enable_extensions = ["attrs_block", "attrs_inline", "colon_fence", "deflist", "linkify", "strikethrough", "substitution"]`, `myst_heading_anchors = 3`, `html_theme = "plone_sphinx_theme"`, `html_baseurl = "https://plone.github.io/plone-contributor-statistics/"`, `exclude_patterns = ["_build"]`, theme options per the skill's recommended block with `repository_url = "https://github.com/plone/plone-contributor-statistics"`, `path_to_docs = "docs"`, `repository_branch = "main"`, edit/issues/repository buttons on, `logo: {"text": "Plone Contributor Statistics"}`. If `linkify` needs `linkify-it-py`, add it to `requirements-docs.txt`.
  - `docs/index.md`: `html_meta` block (description/og:description identical, og:title); H1 "Plone Contributor Statistics"; who this is for (the three readers of spec §1, one sentence each, each linking to its best entry page); what is out of scope (the statistics themselves; code details); a `{grid}` of four cards (Explanation, Reference, How-to guides, Contributing); a hidden `{toctree}` with the four section indexes and `glossary`.
  - Section `index.md` files: `html_meta`, H1, two-sentence purpose, `{toctree}` (empty for now — Sphinx warns on an empty toctree? if so, add pages as later tasks create them and keep a placeholder sentence only).
  - `docs/glossary.md`: `{glossary}` with terms: Unmapped, independent contributor, override, organisation mapping, curated data, PLIP, bot account, excluded repository, merge commit, default branch, release branch, PR interaction. One-sentence definitions, each verified against the code.
  - `Makefile`: `docs-install: pip install -r requirements-docs.txt`; `docs: python -m sphinx -W --keep-going -n -b html docs docs/_build/html`; `docs-linkcheck: python -m sphinx -b linkcheck docs docs/_build/linkcheck`; `docs-clean: rm -rf docs/_build`; add to `.PHONY` and `help` (follow the existing `@echo "  name  description"` alignment).
  - `.gitignore`: `docs/_build/`.

- [ ] **Step 4: Verify:** `make docs-install && make docs` → "build succeeded" with no warnings; `make test` → all pass; `make check` → passes (`docs/conf.py` is outside `*.py` root glob; confirm flake8 in CI also only checks `*.py tests/`).

- [ ] **Step 5: Commit** "Add a Sphinx documentation skeleton in Plone style".

### Task 3: Build and publish in CI

**Files:**
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Write `docs.yml`:**
  - `name: Docs`; `on: push: branches: [main]`, `pull_request:`, `workflow_dispatch:`.
  - Top-level `permissions: contents: read`; `concurrency: group: pages, cancel-in-progress: false` on the deploy job only (builds of PRs may cancel: `group: docs-${{ github.ref }}`, `cancel-in-progress: true` on the build job).
  - Job `build`: `actions/checkout@v7`, `actions/setup-python@v7` with `python-version: '3.12'`, `cache: pip`, `cache-dependency-path: requirements-docs.txt`; `make docs-install`; `make docs`; on non-PR events `actions/configure-pages` and `actions/upload-pages-artifact` with `path: docs/_build/html`. Look up the current major versions of the three Pages actions and of `actions/deploy-pages` on GitHub (`gh api repos/actions/<name>/releases/latest -q .tag_name`) and use those majors.
  - Job `deploy`: `needs: build`, `if: github.event_name != 'pull_request' && github.repository == 'plone/plone-contributor-statistics' && github.ref == 'refs/heads/main'`, `permissions: pages: write, id-token: write`, `environment: name: github-pages, url: ${{ steps.deployment.outputs.page_url }}`, step `actions/deploy-pages` with `id: deployment`.

- [ ] **Step 2: Verify:** `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/docs.yml'))"` succeeds; if `actionlint` is installed, `actionlint .github/workflows/docs.yml` is clean.

- [ ] **Step 3: Commit** "Build the docs on every pull request and publish them to GitHub Pages". Body: Pages must be enabled with source "GitHub Actions" before the first deploy succeeds.

### Task 4: Reference pages

**Files:**
- Create: `docs/reference/data-sources.md`, `docs/reference/data-files.md`, `docs/reference/mapping-files.md`, `docs/reference/recognition-files.md`, `docs/reference/make-targets.md`
- Modify: `docs/reference/index.md` (toctree)

Content per spec §4.2 (reference bullets). Reference rules: describe only, same pattern for every entry, tables or definition lists, no "why". Links to explanation pages are added in Task 6 step 2, once those pages exist.

- [ ] **Step 1: Gather facts on the branch:** for every script in spec appendix B plus `git_history.py`, read the docstring/argparse and output paths; `ls data/ data/community-contributions/` for file patterns; `head -1` of each CSV pattern for columns; `grep -n '^[a-z0-9-]*:' Makefile` for targets; for each target, check the script it calls exists.
- [ ] **Step 2: Write the five pages.** `data-sources.md`: one table (source, origin, years covered, script, output, Make target). Years covered are read from the files present (`ls data/*-plone-contributors.csv`), not copied from the appendix. `make-targets.md`: grouped tables (collection, aggregation, reports, community, packages, maintenance, docs) with a "Status" column (`works` / `broken: <reason>`). `mapping-files.md` includes the still-valid CSV conventions and canonical organisation spellings from `archive/.claude/README.md`, each verified against `organisations.csv` (drop "Simples Consultoria" if absent).
- [ ] **Step 3: Verify:** `make docs` clean; `make test` → reference checks pass (add broken targets/missing scripts to `KNOWN_MISSING` with a comment).
- [ ] **Step 4: Commit** "Document the data sources, files, mapping files and Make targets".

### Task 5: Explanation — collection

**Files:**
- Create: `docs/explanation/scope.md`, `docs/explanation/history-and-coverage.md`, `docs/explanation/counting-rules.md`, `docs/explanation/pr-interactions.md`
- Modify: `docs/explanation/index.md`

Content per spec §4.2 explanation bullets and §4.6 (PR #75 method: local bare treeless clones, release-branch commits older than the default branch's first commit, email → account via GraphQL). Read `gh pr view 75`, `git_history.py` and its tests before writing `counting-rules.md` and `history-and-coverage.md`. `scope.md` contains one `{mermaid}` flowchart of the pipeline (sources → per-year contributor files → organisation files → summaries/reports; curated data and PLIPs as separate inputs), with `:alt:`.

- [ ] **Step 1: Write the four pages.** Titles accept an implicit "About …" (e.g. "What the statistics measure", "Thirty years of history"). Each decision states its why and links its PR/issue.
- [ ] **Step 2: Verify:** `make docs` clean; `make test` passes; `grep -nE '[0-9]{3,}' docs/explanation/*.md` shows only years, dates, PR/issue numbers, SHAs, or method-justifying numbers.
- [ ] **Step 3: Commit** "Explain what is collected and how it is counted".

### Task 6: Explanation — attribution, curated data, recognition, limitations, history

**Files:**
- Create: `docs/explanation/attribution.md`, `docs/explanation/curated-community-data.md`, `docs/explanation/community-recognition.md`, `docs/explanation/known-limitations.md`, `docs/explanation/method-history.md`
- Modify: `docs/explanation/index.md`, reference pages (add "see explanation" links), `tests/test_docs_and_archive.py` (`KNOWN_MISSING` entries)

Content per spec §4.2 and §4.6. `community-recognition.md`: only verifiable facts, cite the plone.org page (find its URL with `grep -rn 'plone.org' generate_community_recognition_report.py reports/community-recognition.md` or the issue #56 text), list the code vs points-CSV disagreements after re-checking them in the code, link #56, name PR #34 and branch `split-code-and-community-contributions` as pending input from Mikel Larreategi (erral). `method-history.md`: chronological journal in three phases (spec §4.2), entries re-checked with `git show --stat <sha>`, including #73, #75 and this docs PR's own entry last. `known-limitations.md`: each item = limitation + effect on interpretation + link; #68 is resolved by #75 and is not listed as a gap.

- [ ] **Step 1: Write the five pages.**
- [ ] **Step 2: Cross-links:** each explanation page links to the reference pages it relies on; each reference page gets a one-line `{seealso}`-free "See {doc}`/explanation/<page>` for why." sentence at its top.
- [ ] **Step 3: Verify:** `make docs` clean; `make test` passes; digit grep as in Task 5.
- [ ] **Step 4: Commit** "Explain attribution, curated data, recognition, limitations and the method history".

### Task 7: How-to guides and contributing

**Files:**
- Create: `docs/how-to/correct-an-organisation-mapping.md`, `docs/how-to/add-curated-community-data.md`, `docs/how-to/regenerate-after-a-mapping-change.md`, `docs/how-to/find-a-contributor.md`, `docs/how-to/collect-data-again.md`, `docs/contributing/documentation.md`
- Modify: `docs/how-to/index.md`, `docs/contributing/index.md`

Content per spec §4.2 how-to bullets and §4.3. How-to rules: title states the goal, opens with "This guide shows you how to …", action only, conditional imperatives, link to explanation/reference instead of explaining. Commands use the `shell` lexer without prompts. `collect-data-again.md` covers the `.env` token, `.cache/repositories/` clones (PR #75), rate-limit waits, checkpoint files and exit code 1 on failure — verify each in `github_api.py`, `git_history.py`, `plone_contributors.py`. `contributing/documentation.md` contains the docs-update rule verbatim, `make docs-install`/`make docs`, the style pointer to the Plone authors guide (`https://6.docs.plone.org/contributing/documentation/`), and that CI builds every PR and publishes `main`.

- [ ] **Step 1: Write the six pages.**
- [ ] **Step 2: Verify:** `make docs` clean; `make test` passes; every `make` command in the how-tos was dry-run with `make -n <target>` and resolves.
- [ ] **Step 3: Commit** "Add how-to guides and the documentation contributing rules".

### Task 8: Agent instructions, PR template, README

**Files:**
- Create: `AGENTS.md`, `CLAUDE.md`, `.github/pull_request_template.md`
- Modify: `README.md`

- [ ] **Step 1: `AGENTS.md`** per spec §4.4, at most ~80 lines, links to docs pages on the published URL and relative `docs/` paths. Includes the docs-update rule verbatim; "`archive/` is historical: never edit it or rely on it."; and the rule "Draft specs and plans outside `docs/`. As the last step before opening the pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename, for transparency."
- [ ] **Step 2: `CLAUDE.md`:** exactly one line `@AGENTS.md`.
- [ ] **Step 3: PR template:** sections "What and why", "Sources / confirmations (for data and mapping changes)", "Checklist" with `- [ ] Tests pass (`make test`)`, `- [ ] Docs updated, or not needed because: …`, `- [ ] Data changes have a source`.
- [ ] **Step 4: `README.md`:** rewrite to: one-paragraph purpose; who it's for; quick start (`make setup`, `make test`, `make docs`); link to the published docs and `docs/`; keep the CI paragraph added by PR #73 and the Flourish links if still valid. Remove stale figures and method sections (they live in the docs now — check each removed section has a home in `docs/`, else move it there first).
- [ ] **Step 5: Verify:** `make test` passes (reference checks also cover nothing here; manually `grep -o '`make [a-z0-9-]*' README.md AGENTS.md` and confirm each target exists); `make docs` clean.
- [ ] **Step 6: Commit** "Add AGENTS.md, a pull request template and a shorter README".

### Task 9: Rebase, re-verify, hand over

- [ ] **Step 1:** `git fetch origin && git rebase origin/main`. If new commits touched collection, mapping, recognition, Makefile or workflows (`git log --stat ORIG_HEAD..origin/main`), re-verify the affected pages; if a method PR (e.g. #34 or the split branch) landed, stop and ask the user.
- [ ] **Step 2:** `make test`, `make check`, `make docs` all clean; `make docs-linkcheck` run and broken links fixed or reported.
- [ ] **Step 3: Statistics check:** `grep -rnE '\b[0-9]{2,}\b' docs --include='*.md'` reviewed by hand; remove anything that is a statistic rather than a method fact.
- [ ] **Step 4: One-sentence-per-line check:** `grep -rnE '[a-z]\. [A-Z]' docs --include='*.md'` outside code blocks and tables → split lines.
- [ ] **Step 5: Archive spec and plan** (user rule, 2026-10-18): copy the spec and this plan unchanged to `archive/specs-and-plans/2026-10-18-docs-cleanup-design.md` and `archive/specs-and-plans/2026-10-18-docs-cleanup-plan.md`, add the row `specs-and-plans/` ("design specs and implementation plans of past work, kept for transparency") to `archive/README.md`, run `make test`, commit "Archive the design and plan of the docs cleanup".
- [ ] **Step 6:** Draft (do not file) the issues for broken Make targets and missing scripts; draft the PR description (what, why, archive list, docs tree, Pages manual step, issue drafts; ends with `Assisted-by: Claude Opus 5.5` per the user's standing rule). Present both to the user and ask before pushing, opening the PR, filing issues, or enabling Pages.
