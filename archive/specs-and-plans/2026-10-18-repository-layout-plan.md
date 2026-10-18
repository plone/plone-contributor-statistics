# Repository layout restructure: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganise the repository so that the tree shows the pipeline.
Curated input and collected data go into scripts, and the scripts produce derived data and reports.
Dead material moves to `archive/`, and the change alters no numbers.

**Architecture:** The work comes as five pull requests.

1. Safety net: shared path, loader and year modules, and loud errors on missing input.
2. Archive the dead material.
3. Move the scripts into `scripts/{lib,collect,derive,report,tools}/`, run as `python -m`.
4. Move the data into `curated/`, `collected/`, `derived/` and `reports/`.
5. Regenerate stale outputs, only if the maintainer approves.

Stages 1–4 are checked by regenerating every derived output and report offline, before and after, and comparing them.

**Tech stack:** Python 3.12, plain scripts (no packaging), pandas, matplotlib, pytest with pytest-timeout, GNU Make, Sphinx with MyST for `docs/`.

**Spec:** `2026-10-18-repository-layout-design.md`, next to this plan in the scratchpad.
It is archived to `archive/specs-and-plans/` in PR 1.

## Global constraints

- Work in a git worktree on its own branch, one branch per PR: `layout-1-safety-net`, `layout-2-archive`, `layout-3-scripts`, `layout-4-data` and `layout-5-regenerate`.
  Each branch starts from the then-current `origin/main`, after the previous PR has merged.
- Commit messages, PR descriptions, issues and comments end with `Assisted-by: Claude Opus 5.5`, with no email address and no `Co-Authored-By` line.
  This is the maintainer's rule.
- Each PR updates `docs/`, `AGENTS.md` and `README.md` for everything it changes, in the same PR.
  `make docs` builds with warnings as errors.
- In stages 1–4, no output changes: `verify_outputs.sh` (Task 1) reports no differences.
- Archive, never delete.
  Don't edit or move existing files in `archive/`.
  The only deletion is `.DS_Store`.
- Code changes get offline pytest tests, and data changes get format checks.
  `make test`, `make check` and `make docs` pass before each PR.
- Never put the GitHub token on a command line.
  Collectors read `GITHUB_TOKEN` from the environment or from `.env`.
- Don't run the collectors that use the GitHub API as part of verification.
- In the docs, don't write statistics or rankings into prose.
- Link issues and PRs as clickable Markdown links in PR descriptions.

## Review focus

1. **A path missed after a move.** A loader must raise `FileNotFoundError` naming the path, never return `{}` or zero points.
   Tests: Task 2, `test_loader_raises_on_missing_file`; Task 3, `test_recognition_raises_without_community_year`.
2. **Tests that `chdir` into `tmp_path`** and write fixtures by bare file name must keep exercising the fixtures, not the real repository files.
   After Task 12 these fixtures need parent folders.
   The `tmp_repo` fixture from Task 12 creates them, and `test_tmp_repo_has_layout` pins this.
3. **Volto override semantics.** `generate_volto_team_report.resolve_org` returns the *first* matching override, while `organisation_stats` applies overrides in file order, so the *last* one wins.
   Sharing a loader must not merge these two behaviours.
   Task 2 keeps `resolve_org` and shares only the file reading.
   Task 1's `verify_outputs.sh` catches a change in `reports/volto.md`.
4. **Running a script directly** (`python scripts/collect/plone_contributors.py`) instead of with `python -m` fails with `ModuleNotFoundError: scripts`.
   `scripts/README.md` and `docs/how-to/collect-data-again.md` must show the `python -m` form.
   Task 8 adds `test_scripts_run_as_modules`.
5. **Summary year windows** must stay at 2020–2024, 2022–2024 and 2015–2024 until stage 5.
   Task 3, `test_default_windows_unchanged`, pins this.

---

## Stage 1 — PR 1: safety net

### Task 1: Output verification harness (not committed)

**Files:**
- Create: `<scratchpad>/verify_outputs.sh`, outside the repository, used by every stage.

**Interfaces:**
- Produces: `verify_outputs.sh <base-ref> "<make targets at base>" "<make targets at HEAD>"`.
  Exit code 0 means no differences.

- [ ] **Step 1: Write the script.** It must do the following:
  1. Create two detached temporary worktrees, one at `<base-ref>` and one at `HEAD`.
  2. Run `make <targets>` in each, sequentially, with the current Python environment.
  3. In each tree, collect every `*.csv`, `*.md`, `*.txt` and `*.png` file outside `docs/`, `archive/`, `tests/` and `.git/` whose content changed or which was created by the run.
     Use `git status --porcelain` plus the committed outputs.
  4. Pair the two sides by **file name**, since paths move in stages 3 and 4.
  5. Compare the files after dropping lines that match `^\*?Generated( on)?:`.
     Compare PNGs byte for byte.
     If PNGs differ, report them as `WARN`, not as a failure, because matplotlib metadata may differ.
  6. Print `MISSING <name>` for a file that exists on one side only, and `DIFF <name>` with a short unified diff for each mismatch.
  7. Remove both worktrees.
- [ ] **Step 2: Sanity check.** Run `verify_outputs.sh origin/main "$TARGETS" "$TARGETS"` on an unchanged branch.
  Expected: exit 0.
  The base target list for stages 1–3 is:

  ```
  TARGETS="run-organisation-stats run-plip-organisations three-year-summary five-year-summary ten-year-summary yearly-activity yearly-graphs generate-report generate-volto-report community-recognition"
  ```

### Task 2: Shared paths and mapping loaders that fail loudly

**Files:**
- Create: `paths.py`, `mappings.py` at the root. They move to `scripts/lib/` in Task 7.
- Modify:
  - `plone_contributors.py:46-97`: the constants and the four loaders move to `mappings.py`; keep re-exports for the existing imports.
  - `organisation_stats.py:26-56`
  - `plip_organisation_stats.py:15-16,32`
  - `generate_volto_team_report.py:27-66`
  - `generate_community_recognition_report.py:58-64`
  - `analyze_independent_contributors.py:138-150`
  - Every literal `data/...`, `reports/...` or root CSV path in the live scripts listed in spec §6.
- Test: `tests/test_mappings.py`; modify `tests/test_repository_selection.py:52-53`.

**Interfaces:**
- Produces in `paths.py`: `pathlib.Path` constants relative to the repository root.
  - Mapping files: `ORGANISATIONS`, `OVERRIDES`, `SOURCES`, `PROPOSALS`, `BOT_ACCOUNTS`, `EXCLUDED_REPOSITORIES`, `COMMIT_AUTHORS`, `ACCOUNT_ALIASES` and `FULLNAMES`.
  - Data folders: `COMMUNITY` (today `data/community-contributions`), `CONTRIBUTORS_DIR`, `PR_INTERACTIONS_DIR`, `VOLTO_DIR` and `ORGANISATION_CONTRIBUTORS_DIR`.
    All four are `data` for now.
  - Report locations: `REPORTS_DIR`, `PR_INTERACTION_REPORTS_DIR` (today `reports`), `GRAPHS_DIR` (`graphs`) and `SUMMARIES_DIR` (`.`).
  - Other files: `PLIPS`, `PLIPS_DETAILED`, `PLIP_ORGANISATIONS`, `YEARLY_ACTIVITY`, `RECOGNITION_LEVELS` and `RECOGNITION_REPORT_DIR` (`data/community-contributions`).
  - Functions: `contributors_file(label) -> Path`, `organisation_contributors_file(year) -> Path`, `pr_interactions_file(label) -> Path`, `volto_file(label) -> Path` and `checkpoint_file(label) -> Path`.
- Produces in `mappings.py`, all raising `FileNotFoundError` when the file is missing:
  - `load_excluded_repositories(path=paths.EXCLUDED_REPOSITORIES) -> dict[str, str]`
  - `load_bot_accounts(path=paths.BOT_ACCOUNTS) -> dict[str, str]`
  - `load_commit_authors(path=paths.COMMIT_AUTHORS) -> dict[str, str]`
  - `load_account_aliases(path=paths.ACCOUNT_ALIASES) -> dict[str, str]`
  - `read_organisations(path=paths.ORGANISATIONS) -> dict[str, str]`: login → organisation, from the `Team` column split on `;`.
  - `organisation_names(path=paths.ORGANISATIONS) -> dict[str, str]`: lower-case name → spelling.
  - `read_overrides(path=paths.OVERRIDES) -> list[dict]`: keys `github_username`, `organisation`, `from_year` and `to_year`, with years as `int | None`, in file order.
  - `load_organisation_mapping(mapping_file=paths.ORGANISATIONS, overrides_file=paths.OVERRIDES, year=None) -> dict[str, str]`.
    Its behaviour and print output are identical to today's `organisation_stats.load_organisation_mapping`, except for the errors.
  - `organisation_stats` and `plone_contributors` re-export these names, so existing imports and tests keep working until Task 7.

- [ ] **Step 1: Write the failing tests** in `tests/test_mappings.py`:

```python
LOADERS = [mappings.load_excluded_repositories, mappings.load_bot_accounts, mappings.load_commit_authors,
           mappings.load_account_aliases, mappings.read_organisations, mappings.organisation_names,
           mappings.read_overrides]

@pytest.mark.parametrize('loader', LOADERS)
def test_loader_raises_on_missing_file(loader, tmp_path):
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        loader(tmp_path / 'missing.csv')

def test_mapping_raises_on_missing_overrides_for_a_year(tmp_path):
    (tmp_path / 'o.csv').write_text('Organisation,Team\nA,x\n', encoding='utf-8')
    with pytest.raises(FileNotFoundError):
        mappings.load_organisation_mapping(tmp_path / 'o.csv', tmp_path / 'missing.csv', year=2024)

def test_paths_are_relative():
    for name, value in vars(paths).items():
        if isinstance(value, Path):
            assert not value.is_absolute(), name
```

  Replace `test_missing_exclusion_file_excludes_nothing` with `test_missing_exclusion_file_raises`.
- [ ] **Step 2:** Run `python -m pytest tests/test_mappings.py tests/test_repository_selection.py -v`.
  Expected: FAIL with `ModuleNotFoundError: mappings`.
- [ ] **Step 3:** Implement `paths.py` and `mappings.py`.
  Point every caller at them.
  In `generate_volto_team_report.py`, replace only the file reading: `load_mapping` becomes `mappings.read_organisations`, and `load_overrides` becomes `mappings.read_overrides`.
  Keep `resolve_org` unchanged (review focus 3).
  Replace `os.path.exists` checks with plain `open` calls, so the error names the path.
- [ ] **Step 4:** Run `make test`.
  Expected: all pass.
- [ ] **Step 5:** Run `verify_outputs.sh origin/main "$TARGETS" "$TARGETS"`.
  Expected: exit 0.
- [ ] **Step 6:** Commit: "Read mapping files in one place and fail when one is missing".

### Task 3: Year defaults in one place, and loud errors for missing yearly input

**Files:**
- Create: `years.py` at the root; it moves in Task 7.
- Modify:
  - `multi_year_summary.py:239-243`
  - `generate_community_recognition_report.py:22`, the loaders at `:29-160`, and every `try/except FileNotFoundError` around the per-kind files at `:158-290`
  - `Makefile`, the targets `five-year-summary`, `ten-year-summary`, `three-year-summary` and `community-recognition`
- Test: `tests/test_years.py`; extend `tests/test_recognition_method.py`.

**Interfaces:**
- Produces in `years.py`:
  - `SUMMARY_END_YEAR = 2024`
  - `RECOGNITION_YEAR = 2025`
  - `window(length: int, end: int = SUMMARY_END_YEAR) -> list[int]`
  - `last_completed_year(today: date | None = None) -> int`.
    It isn't used as a default before stage 5.
- `Makefile` variables `SUMMARY_END ?= 2024` and `RECOGNITION_YEAR ?= 2025`.
  The summary targets pass `--years $(shell seq $$(($(SUMMARY_END)-N+1)) $(SUMMARY_END))`.
  `community-recognition` passes `--year $(RECOGNITION_YEAR)`.
  This adds a `--year` argument to `generate_community_recognition_report.py`, with `years.RECOGNITION_YEAR` as its default.

- [ ] **Step 1: Write the failing tests:**

```python
def test_default_windows_unchanged():
    assert years.window(3) == [2022, 2023, 2024]
    assert years.window(5) == [2020, 2021, 2022, 2023, 2024]
    assert years.window(10) == list(range(2015, 2025))
    assert years.RECOGNITION_YEAR == 2025

def test_last_completed_year():
    assert years.last_completed_year(date(2026, 10, 18)) == 2025

def test_recognition_raises_without_community_year(tmp_path):
    # community folder exists, but has no files for the year
    ...
    with pytest.raises(FileNotFoundError, match='2025'):
        recognition.calculate_community_recognition_points(year=2025, data_dir=str(tmp_path / 'data'), ...)

def test_recognition_raises_on_missing_organisation_year(tmp_path):
    with pytest.raises(FileNotFoundError, match='2023-plone-organisation-contributors.csv'):
        recognition.load_pr_data([2023], data_dir=str(tmp_path))

def test_recognition_warns_on_one_missing_kind(tmp_path, capsys):
    # year has a plone-conference file but no podcasts file: still runs, prints a warning
```

- [ ] **Step 2:** Run `python -m pytest tests/test_years.py tests/test_recognition_method.py -v`.
  Expected: FAIL.
- [ ] **Step 3:** Implement the following:
  - Missing community folder, or no `{year}-*.csv` in it: raise `FileNotFoundError(f'no curated community data for {year} in {folder}')`.
  - Missing yearly organisation file, `plone-plips-detailed.csv`, or the recognition levels file: raise.
  - One missing kind of data in a year that has other files: keep the warning.
- [ ] **Step 4:** Run `make test`.
  Expected: pass.
  Then run `verify_outputs.sh origin/main "$TARGETS" "$TARGETS"`.
  Expected: exit 0.
- [ ] **Step 5:** Commit: "Keep the year defaults in one place and fail on missing yearly input".

### Task 4: Untrack junk, update the docs, open PR 1

**Files:**
- Modify:
  - `.gitignore`: add `.DS_Store`, `pypi_cache/` and `__pycache__/`; check whether the last one is already there.
  - `docs/reference/make-targets.md`: the new variables.
  - `docs/explanation/known-limitations.md`: mention that missing input now raises an error.
  - `docs/how-to/collect-data-again.md`, if it names the defaults.
- Delete from git: `.DS_Store`, with `git rm --cached .DS_Store && rm .DS_Store`.
- Create: `archive/specs-and-plans/2026-10-18-repository-layout-design.md` and `...-plan.md`, copied unchanged from the scratchpad.
  Their rows go into the `specs-and-plans/` entry, which already exists.

- [ ] **Step 1:** Make the changes.
  Run `make test check docs`.
  Expected: all succeed.
- [ ] **Step 2:** Commit, push, and open PR 1.
  The title is "Fail on missing input files and keep paths and years in one place".
  The body states that no output changes, with the verification command and its result.

---

## Stage 2 — PR 2: archive

### Task 5: Move dead and experimental material into archive bundles

**Files:**
- Create the bundles with `git mv` (verify the list against the current tree first):
  - `archive/legacy-collectors/`: `plone_contributor_statistics.py`, `plone_companies.py`
  - `archive/plip-levels/`: `analyze_plip_contributor_levels.py`, `generate_plip_3tier_levels.py`, `plip_stats.py`
  - `archive/package-statistics/`: `npm_package_stats.py`, `volto_addon_discovery.py`, `pypi_package_statistics.py`, `npm_mapping.txt`, and every `npm-packages-*.csv` and `npm-packages-*.md`
  - `archive/cmfplone-releases/`: `fetch_cmfplone_releases.py`, `filter_releases.py`, `cmfplone-releases.csv`
  - `archive/flourish/`: `create_organization_flourish_csv.py`, `create_individual_contributors_flourish_csv.py`, the four root Flourish CSVs, and `data/plone-individual-contributors-flourish.csv` and `data/plone-organizations-bar-chart-race-flourish.csv`, both renamed with the prefix `data-` inside the bundle to avoid name clashes
  - `archive/orphan-outputs/`: `reports/plips.md`, `graphs/commits_prs_trend.png`
- Modify:
  - `archive/README.md`: one row per bundle.
    The row has the bundle path, `2026-10-…`, the original paths and why the bundle was archived.
    A revival issue link is added in Task 6.
    Remove the last line about `make analyze-plip-levels`.
  - `Makefile`: remove `run-contributors`, `run-organisations`, `analyze-plip-levels`, `npm-packages`, `pypi-packages`, `generate-plip-report`, both `flourish-*` targets and `run-all`, and their help lines and `.PHONY` entries.
    `clean` deletes only ignored files: `.pytest_cache`, `__pycache__`, `*.pyc`, `data/*_checkpoint.csv` and `docs/_build`.
    It never deletes committed files.
  - `tests/test_docs_and_archive.py`: extend `ARCHIVED` with the new bundle names, and empty `KNOWN_MISSING`.
  - Docs:
    - `reference/data-sources.md`, `reference/data-files.md`, `reference/make-targets.md` and `reference/mapping-files.md`, which drops `npm_mapping.txt`
    - `explanation/known-limitations.md`, which drops the resolved entries
    - `explanation/community-recognition.md:54`
- Test: `tests/test_docs_and_archive.py`, plus a new test there:

```python
def test_clean_keeps_committed_files():
    recipe = makefile_target('clean')
    for committed in ['*.csv', 'summary-', 'STATISTICS-', 'graphs', 'plone-plips']:
        assert committed not in recipe
```

- [ ] **Step 1:** Write the new test and extend `ARCHIVED`.
  Run `python -m pytest tests/test_docs_and_archive.py -v`.
  Expected: FAIL.
- [ ] **Step 2:** Do the moves and the edits.
  Run `make test check docs`.
  Expected: all succeed.
- [ ] **Step 3:** Run `verify_outputs.sh origin/main "$TARGETS" "$TARGETS"`.
  Expected: exit 0, since the archived scripts produce nothing in `$TARGETS`.
- [ ] **Step 4:** Commit: "Archive dead and experimental scripts, data and reports".

### Task 6: Revival issues, then open PR 2

- [ ] **Step 1: Ask the maintainer to confirm the issue list before creating anything.**
  The list, from spec §4.4:
  1. "Packages published per organisation (npm, PyPI)": revive `archive/package-statistics/`.
  2. "Charts in the repository instead of Flourish": revive `archive/flourish/` as charts in the docs or the reports.
  3. "PLIP report generator": `reports/plips.md` had no generator.
     The alternative is a comment on #14.
- [ ] **Step 2:** Create the approved issues with `gh issue create`.
  Each issue says what the bundle contained, why it was archived, and what reviving it would take, and ends with `Assisted-by: Claude Opus 5.5`.
  Add the links to the rows in `archive/README.md`, and commit.
- [ ] **Step 3:** Push and open PR 2.

---

## Stage 3 — PR 3: scripts

### Task 7: `scripts/lib/`

**Files:**
- Move with `git mv` into `scripts/lib/`: `github_api.py`, `git_history.py`, `paths.py`, `mappings.py` and `years.py`.
- Modify: every import of these modules (`from scripts.lib import github_api` and so on), in scripts and tests.

**Interfaces:**
- Produces the import paths `scripts.lib.paths`, `scripts.lib.mappings`, `scripts.lib.years`, `scripts.lib.github_api` and `scripts.lib.git_history`.
- No `__init__.py` files.
  Python 3 namespace packages are enough.
  Add `__init__.py` files only if a tool fails without them, and say so in the PR.

- [ ] **Step 1:** Move the files and fix the imports.
  Monkeypatch targets in tests, such as `monkeypatch.setattr(plone_contributors, 'github_get', …)`, keep patching the module that *uses* the name.
- [ ] **Step 2:** Run `make test`.
  Expected: pass.
  Commit: "Move the shared code into scripts/lib".

### Task 8: Stage folders, `python -m`, CI

**Files:**
- Move with `git mv`:
  - `scripts/collect/`: `plone_contributors.py`, `plone_pr_interactions.py`, `volto_stats.py`, `plone_plips.py`
  - `scripts/derive/`: `organisation_stats.py`, `multi_year_summary.py`, `yearly_activity_analysis.py`, `plip_organisation_stats.py`
  - `scripts/report/`: `generate_contributor_report.py`, `generate_community_recognition_report.py`, `generate_volto_team_report.py`, `generate_yearly_graphs.py`
  - `scripts/tools/`: `get_github_name.py`, `analyze_independent_contributors.py`
- Modify:
  - `Makefile`: every `python X.py` becomes `python -m scripts.<stage>.X`.
    `lint`, `format` and `check` use `$(shell find scripts tests -name '*.py')`.
  - `.github/workflows/tests.yml`: flake8 checks `scripts/ tests/`.
  - `tests/conftest.py`: update the comment; the root stays on `sys.path`.
  - Imports in all tests.
  - `plone_plips.py:28`: read the token through `load_dotenv()` like the other collectors, instead of `open('.env')`.
  - `tests/test_docs_and_archive.py`: `_code_files` globs `scripts/**/*.py`.
- Test: `tests/test_layout.py`, new:

```python
def test_scripts_run_as_modules():
    for script in Path('scripts').glob('*/*.py'):
        if script.parent.name == 'lib':
            continue
        module = '.'.join(script.with_suffix('').parts)
        result = subprocess.run([sys.executable, '-m', module, '--help'], capture_output=True, timeout=30)
        assert result.returncode == 0, (module, result.stderr.decode()[-500:])

def test_no_python_files_in_root():
    assert not list(Path('.').glob('*.py'))
```

  (`--help` must not touch the network or files.
  If a script has no argparse, give it one with a short description.)

- [ ] **Step 1:** Write `tests/test_layout.py`.
  Run it.
  Expected: FAIL.
- [ ] **Step 2:** Move the files and make the edits.
  Run `make test check`.
  Expected: pass.
- [ ] **Step 3:** Run `verify_outputs.sh origin/main "$TARGETS" "$TARGETS"`.
  The target names are still the same.
  Expected: exit 0.
- [ ] **Step 4:** Commit: "Move the scripts into scripts/, grouped by stage".

### Task 9: A `YEAR` variable instead of per-year targets, and one target for a whole year

**Files:**
- Modify: `Makefile`, `docs/reference/make-targets.md`, and how-tos that name per-year targets (search for `run-stats-20` and similar).
- Create: `docs/how-to/prepare-a-new-year.md`, linked from `docs/how-to/index.md` and from `README.md`.
  It covers `make year YEAR=…`, what to check by hand (unmapped contributors via `analyze-independent`, curated community files for the year) and what to commit.
  If it would mostly repeat `collect-data-again.md`, extend that page instead.
- Test: extend `tests/test_layout.py`.

**Interfaces:**
- `YEAR ?= $(shell python -c 'from scripts.lib.years import last_completed_year as y; print(y())')`
- Targets:
  - `run-stats`, `run-organisation-stats-year`, `pr-interactions` and `run-volto-stats` take `YEAR`.
    Choose the names, but keep `run-organisation-stats`, which covers all years.
  - `run-stats-all-years`, `pr-interactions-all-years` and `run-organisation-stats` stay.
  - New: `year`, which runs, in order:
    1. `run-stats`
    2. `pr-interactions`
    3. `run-volto-stats`
    4. `run-plips`
    5. `run-organisation-stats-year`
    6. `run-plip-organisations`
    7. the summaries
    8. `yearly-activity`
    9. `yearly-graphs`
    10. `generate-report`
    11. `generate-volto-report`
    12. `community-recognition`

    It is documented as "prepare a new year".
- Every `run-stats-20NN`, `run-organisation-stats-20NN`, `pr-interactions-20NN` and `run-volto-stats-20NN` target is removed.

- [ ] **Step 1:** Add `test_no_per_year_targets`, which asserts that no Makefile target matches `-(19|20)\d\d:`.
  Run it.
  Expected: FAIL.
- [ ] **Step 2:** Rewrite the targets.
  Run `make -n year YEAR=2024` and check the printed order.
  Run `make test docs`.
  Expected: pass.
  The docs test for Make targets catches stale target names in the docs.
- [ ] **Step 3:** Commit: "Use a YEAR variable instead of one target per year".

### Task 10: Move the PR interaction report out of its collector, if the CSV is enough

**Files:**
- Read: `scripts/collect/plone_pr_interactions.py`, the report writing near `:340-470` and the CSV columns near `:313-330`.
- Maybe create: `scripts/report/generate_pr_interactions_report.py`, plus a `pr-interactions-report` target that takes `YEAR`.

- [ ] **Step 1:** Decide.
  For each number and list in `reports/github-pr-interactions-report-2024.md`, check whether it can be computed from `data/2024-plone-pr-interactions.csv`.
  If not, stop here.
  Add a paragraph to `scripts/README.md` (Task 11) and to `docs/reference/data-files.md` saying that this collector also writes a report, and why.
  Then skip to Task 11.
- [ ] **Step 2 (only if the CSV is enough):** Write `tests/test_pr_interactions_report.py`.
  It builds the report from a small CSV fixture and asserts the section headings and counts.
  Run it.
  Expected: FAIL.
- [ ] **Step 3:** Move the report code into the new script.
  The collector stops writing reports.
  Run `python -m scripts.report.generate_pr_interactions_report --year Y` for every year that has a CSV.
  `git diff reports/` must show only `Generated` lines.
- [ ] **Step 4:** Run `make test`, then commit.

### Task 11: Scripts docs, open PR 3

**Files:**
- Create: `scripts/README.md`.
  It describes the stages, explains that scripts run as `python -m scripts.<stage>.<name>` from the root (normally through `make`), and lists what `lib/` holds.
- Modify:
  - Every script path in `docs/` and in `AGENTS.md`'s Layout section and its "Looking up names" section, which becomes `python -m scripts.tools.get_github_name <login>`.
  - `README.md`, where it names scripts.
- [ ] **Step 1:** Make the edits.
  Run `make test check docs`.
  Expected: pass.
  Run `verify_outputs.sh origin/main "<base targets>" "<new targets>"` with the renamed targets.
  Expected: exit 0.
- [ ] **Step 2:** Push and open PR 3.
  Comment on PR #34 that the repository layout changed, linking PR 3.

---

## Stage 4 — PR 4: data

### Task 12: Move data folders and update `paths.py`

**Files:**
- Move with `git mv`, keeping file names:
  - **Mapping files** (`organisations.csv`, `organisation_mapping_overrides.csv`, `organisation_mapping_sources.csv`, `organisation_mapping_proposals.csv`, `commit_authors.csv`, `account_aliases.csv`, `bot_accounts.csv`, `excluded_repositories.csv` and `mapping-github-username-to-fullname.csv`) go to `curated/mappings/`.
  - **`data/community-contributions/`** goes to `curated/community-contributions/`, except `*-community-recognition-report.csv`, which goes to `derived/community-recognition/`.
  - **Collected data:**
    - `data/*-plone-contributors.csv` goes to `collected/contributors/`.
    - `data/*-plone-pr-interactions.csv` goes to `collected/pr-interactions/`.
    - `data/*-volto-stats.csv` goes to `collected/volto/`.
    - `plone-plips.csv` and `plone-plips-detailed.csv` go to `collected/plips/`.
  - **Derived data:**
    - `data/*-plone-organisation-contributors.csv` goes to `derived/organisation-contributors/`.
    - `summary-past-*.csv` goes to `derived/summaries/`.
    - `yearly-activity-statistics.csv` and `plone-plip-organisations.csv` go to `derived/`.
  - **Reports:**
    - `STATISTICS-PAST-*.txt` goes to `reports/summaries/`.
    - `reports/github-pr-interactions-report-*.md` goes to `reports/pr-interactions/`.
    - `graphs/*.png` goes to `reports/graphs/`.
  - Afterwards, `data/` and `graphs/` are empty and disappear.
- Modify:
  - `scripts/lib/paths.py`, constants only.
  - `.gitignore`: `collected/**/*_checkpoint.csv` replaces `data/*_checkpoint.csv`.
  - `Makefile`: the loop in `run-organisation-stats` globs `collected/contributors/*-plone-contributors.csv`, and `clean` uses the new checkpoint path.
  - Tests that build paths themselves: the `DATA` and `ROOT / '<file>'` constants in `test_conference_trainings_format.py`, `test_board_of_directors_format.py`, `test_release_managers_format.py`, `test_curated_organisation_names.py`, `test_commit_authors.py`, `test_unmapped_and_mapping.py`, `test_repository_selection.py`, `test_full_history_collection.py` and `test_recognition_method.py`.
    All use `paths.*` from now on.
  - `tests/conftest.py`: new fixture.

**Interfaces:**
- Produces the `tmp_repo` fixture in `tests/conftest.py`.
  It does `monkeypatch.chdir(tmp_path)`, creates the parent folder of every `Path` constant in `scripts.lib.paths`, and returns `tmp_path`.
  Tests that used `monkeypatch.chdir(tmp_path)` with fixture files switch to it.

- [ ] **Step 1:** Add `test_tmp_repo_has_layout(tmp_repo)` to `tests/test_layout.py`.
  It asserts that `paths.ORGANISATIONS.parent` and `paths.CONTRIBUTORS_DIR` exist under `tmp_repo`.
  Run it.
  Expected: FAIL.
- [ ] **Step 2:** Make the moves and the edits.
  Run `make test`.
  Expected: pass.
- [ ] **Step 3:** Run `verify_outputs.sh origin/main "<stage-1 targets>" "<new targets>"`.
  Expected: exit 0, with files paired by name.
- [ ] **Step 4:** Commit: "Move data into curated, collected, derived and reports".

### Task 13: Folder READMEs, the map, the layout guard, and docs; open PR 4

**Files:**
- Create: `curated/README.md`, `collected/README.md`, `derived/README.md` and `reports/README.md`.
  Each is 3–8 lines: what the folder holds, edit by hand or never, which `make` targets write it, and a link to the matching reference page.
  `curated/README.md` repeats the public-record rule in one line, with a link to the docs.
- Modify:
  - `README.md`: a new "Where things live" section with the top-level tree from spec §4.1, one line per folder.
  - `AGENTS.md`: the Layout section.
  - `docs/reference/data-files.md` and `docs/reference/mapping-files.md`, where "All of them are in the repository root" changes.
  - `docs/reference/recognition-files.md`, `docs/reference/data-sources.md`, and all how-tos and explanations that name moved files.
    `test_docs_reference_existing_files` lists every one.
  - The glossary, if it names paths.
- Test: add to `tests/test_layout.py`:

```python
ALLOWED_ROOT = {'README.md', 'AGENTS.md', 'CLAUDE.md', 'Makefile', 'requirements.txt', 'requirements-docs.txt',
                'pytest.ini', '.env.example', '.gitignore', '.github', 'scripts', 'curated', 'collected',
                'derived', 'reports', 'docs', 'tests', 'archive'}

def test_root_contains_only_allowed_entries():
    tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout.split()
    assert {p.split('/')[0] for p in tracked} <= ALLOWED_ROOT

@pytest.mark.parametrize('folder', ['scripts', 'curated', 'collected', 'derived', 'reports'])
def test_folder_has_readme(folder):
    assert (Path(folder) / 'README.md').exists()
```

- [ ] **Step 1:** Write the tests.
  Run them.
  Expected: `test_folder_has_readme` fails for the four data folders.
- [ ] **Step 2:** Write the READMEs and update the docs.
  Run `make test check docs`.
  Expected: pass.
- [ ] **Step 3:** Push and open PR 4.

---

## Stage 5 — PR 5: regenerate stale outputs (only with the maintainer's go-ahead)

### Task 14: Switch defaults to the last completed year and regenerate

- [ ] **Step 1: Ask the maintainer whether to do this stage.**
  It changes published numbers: the summary windows move from ending in 2024 to ending in 2025, and `reports/volto.md` is regenerated, last generated on 2026-06-24.
- [ ] **Step 2:** In `scripts/lib/years.py`, set `SUMMARY_END_YEAR` and `RECOGNITION_YEAR` from `last_completed_year()`.
  The `Makefile` defaults follow `YEAR`.
  Update `test_default_windows_unchanged` to `test_default_windows_follow_last_completed_year`, with a fixed `today`.
- [ ] **Step 3:** Run every target in `$TARGETS` with the new names.
  `git rm` the old `summary-past-*-2024.csv` files that the new windows replace.
  This is a regeneration, not an archive: git history keeps the old files.
- [ ] **Step 4:** Run `make test docs`, commit, and open PR 5.
  The body lists which outputs changed and why.
