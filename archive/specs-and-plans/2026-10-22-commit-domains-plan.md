# Commit domains per person and year — Implementation Plan (plan 2b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A collected yearly file of how many commits each person made under which mail domain, so that plan 2c can compute the tie-break of `docs/explanation/attribution.md` ("the year goes to the organisation whose address most of the person's commits of that year carry") from repository data alone, without the clones.

**Architecture:** The person and domain logic that `scripts/tools/address_proposals.py` already has moves to a library module; a new collector reads the cached clones (as `scripts/collect/plone_changelogs.py` does) and writes `collected/commit-domains/YYYY-plone-commit-domains.csv`; a small reader returns the counts per person and year for the derive stage.

**Tech Stack:** Python 3.12, git (bare clones in the main checkout's `.cache/repositories/plone/*.git`), pandas only if the surrounding collectors use it for writing, pytest.

**Spec:** `archive/specs-and-plans/2026-10-22-sources-and-events-design.md`, section "counting", rule 6b and the note on the commit-domain collector.

## Global Constraints

- Own worktree `.claude/worktrees/commit-domains`, branch `commit-domains`, from `origin/main` at the time of starting. Python from `~/.venvs/plone-contributor-statistics`.
- Only mail **domains** are stored, never local parts or full addresses.
- The `username` column holds what the other collected files hold: `Registry.username_of(person)` (the GitHub login, or `person:<id>`).
- Commits imported from Subversion (trailer `svn path=…; revision=…` or `git-svn-id:`) are skipped: their addresses were assigned in 2011 and say nothing about the year (`git_history.read_authors(converted=False)`). Merge commits are skipped (as the contributor statistics skip them, #39).
- Bots (`load_bot_accounts`) and authors no register identifies are skipped.
- Subversion-UUID and `localhost` domains are skipped; GitHub noreply addresses are stored as the domain `users.noreply.github.com`.
- Tests are offline (fake git output). `scripts/lib/model/` stays the only reader of `curated/`.
- Docs in the same PR: `docs/reference/data-files.md` (the new file), `docs/reference/make-targets.md` (the new target), `docs/how-to/collect-data-again.md` if it lists the collectors.
- No statistics in prose. Commit footers and PR footer as in plan 2a.

## Review Focus

1. **One commit on several branches** must count once (read_authors already deduplicates by sha; keep it so). → Task 2 `test_a_commit_on_two_branches_counts_once`.
2. **The same person under two addresses of one domain** must add up under that domain. → Task 2 `test_counts_add_up_per_domain`.
3. **A year without any identified commit** must still produce a file with the header only, so derive can tell "no data" from "not collected". → Task 2 `test_a_year_without_commits_has_a_header_only_file`.
4. **Upper-case domains and trailing dots** (`Foo.COM.`) must fold to one domain. → Task 1 `test_domain_of_folds_case_and_trailing_dot`.
5. **Address tool unchanged:** moving its helpers must not change `address_proposals` output. → Task 1: its existing tests pass unchanged.

---

### Task 1: Move the author and domain helpers to the library

**Files:**
- Create: `scripts/lib/commit_authors.py`, `tests/test_commit_authors.py`
- Modify: `scripts/tools/address_proposals.py` (import from the new module; no behaviour change), `scripts/lib/git_history.py` (`read_authors(path, converted=True, merges=True)`)

**Interfaces:**
- Produces in `scripts/lib/commit_authors.py`: `NOREPLY`, `PERSONAL_DOMAINS`, `is_company_domain(domain) -> bool`, `class Finder(registry, bots)` with `.person(email, name) -> str | None` (moved unchanged from `address_proposals`), and new `domain_of(email: str) -> str | None` — lower-cased part after the last `@`, trailing dots stripped; `None` for an address without `@`, a Subversion-UUID domain (`changelogs.SVN_DOMAIN`) or `localhost`; `'users.noreply.github.com'` for a noreply address.
- `git_history.read_authors(..., merges=True)`: with `merges=False` it passes `--no-merges` to `git log`.

- [ ] **Step 1:** Failing tests: `test_domain_of_folds_case_and_trailing_dot`, `test_domain_of_skips_svn_and_localhost`, `test_domain_of_noreply`, `test_read_authors_without_merges` (fake `git` runner or a tiny real repo in `tmp_path` built with `git init`; follow `tests/test_git_history.py`).
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement; `address_proposals` imports the moved names.  **Step 4:** `python -m pytest -q` — PASS, `tests/test_address_proposals.py` unchanged and green.
- [ ] **Step 5:** Commit — "Move the commit author helpers to the library".

### Task 2: The collector

**Files:**
- Create: `scripts/collect/plone_commit_domains.py`, `tests/test_commit_domains_collect.py`, `collected/commit-domains/` (via the run in Task 4)
- Modify: `scripts/lib/paths.py` (`COMMIT_DOMAINS_DIR = Path('collected/commit-domains')`, `commit_domains_file(year)` → `COMMIT_DOMAINS_DIR / f'{year}-plone-commit-domains.csv'`), `Makefile` (`run-commit-domains: python -m scripts.collect.plone_commit_domains` plus a help line), `collected/README.md`

**Interfaces:**
- Consumes: `cached_repositories(cache_dir)` from `scripts.collect.plone_changelogs`, `git_history.read_authors(path, converted=False, merges=False)`, `Finder`, `domain_of`, `load_registry`, `load_bot_accounts`, `load_excluded_repositories`.
- Produces: `collect(clones, finder, registry) -> dict[int, Counter[(username, domain)]]`; `write(counts, years)` writes one CSV per year with columns `username,domain,commits`, rows sorted by `username` then `commits` descending then `domain`; every year in `years` gets a file (header only when empty).
- CLI: `python -m scripts.collect.plone_commit_domains [--cache DIR] [--first-year 2002] [--last-year <current year>]`; default cache `git_history.CACHE_DIR`; years from `--first-year` to `--last-year` inclusive. Excluded repositories are skipped. Stops with a clear message when the cache has no clones ("fill the cache with `make run-changelogs`").

- [ ] **Step 1:** Failing tests: `test_a_commit_on_two_branches_counts_once`, `test_counts_add_up_per_domain`, `test_unidentified_authors_and_bots_are_skipped`, `test_converted_commits_are_skipped`, `test_a_year_without_commits_has_a_header_only_file`, `test_username_is_the_collected_key` (`person:<id>` for a person without login).
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once (incl. `tests/test_layout.py`, which runs `--help` and checks `paths.py` folders).
- [ ] **Step 5:** Commit — "Collect the mail domains of the commits per person and year".

### Task 3: Reading the counts for the derive stage

**Files:**
- Create: `scripts/lib/commit_domains.py`, `tests/test_commit_domains_read.py`

**Interfaces:**
- Produces: `load_commit_domains(year: int) -> dict[str, collections.Counter]` — `{username: Counter({domain: commits})}` from `commit_domains_file(year)`; `{}` when the file has only a header; `FileNotFoundError` when the year was never collected.
- Produces: `organisation_commits(counts: Counter, registry) -> tuple[Counter, int, int]` — commits per organisation id (through `registry.match_domain`, company domains only), commits under personal domains (`not is_company_domain`), and commits under company domains no organisation matches. Plan 2c's rule 6b uses it.

- [ ] **Step 1:** Failing tests: `test_load_commit_domains`, `test_header_only_year_is_empty`, `test_missing_year_raises`, `test_organisation_commits_splits_personal_and_unmatched`.
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Read the commit domains per person and year".

### Task 4: Run, documentation, pull request

- [ ] **Step 1:** Run on the real clones: `python -m scripts.collect.plone_commit_domains --cache /home/jensens/ws/cdev/plone-contributor-statistics/.cache/repositories` (no network: it only reads the clones). Expected: one file per year 2002–current year; spot-check three people whose employers are known from `curated/mappings/affiliations.csv` (e.g. a kitconcept, a Zest and a Syslab person) — their company domains appear.
- [ ] **Step 2:** Docs: the new file in `docs/reference/data-files.md` (columns, what is skipped, that only domains are stored), the target in `docs/reference/make-targets.md`, `collected/README.md`; `make docs` (in an environment with the docs requirements; `make docs-install` first if needed).
- [ ] **Step 3:** `python -m pytest -q && python -m scripts.tools.check` — PASS. Commit — "Add the commit domains of 2002 to <year>".
- [ ] **Step 4:** Copy this plan unchanged to `archive/specs-and-plans/2026-10-22-commit-domains-plan.md`; commit. Ask Jens before pushing; open the PR.
