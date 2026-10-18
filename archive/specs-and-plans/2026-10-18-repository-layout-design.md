# Design: repository layout restructure

Date: 2026-10-18
Repository: `plone/plone-contributor-statistics`

## 1. Intent

Code, hand-maintained mapping data, collected data, derived data and reports are mixed in the repository root, in `data/` and in `reports/`.
The root holds 28 scripts, about 60 data and report files, and several dead experiments next to the live pipeline.
Nobody can tell from the tree which files are edited by hand, which files a script regenerates, and which files are left over.

After this work, the tree itself explains the pipeline.
The structure is also documented.
Dead and experimental material is archived, not deleted, and gets an issue wherever reviving it could make sense.

### Reader

A maintainer: a person who works on the repository, either to improve it or to prepare the numbers for a new year.
In their first minutes they must see:

- where the code is, and which script belongs to which stage;
- which files they edit by hand, and which files they must never edit because a script regenerates them;
- what is history and can be ignored.

## 2. Goals, non-goals, anti-goals

Goals

- A top-level layout that mirrors the pipeline: curated input and collected data go into scripts, which produce derived data and reports.
- Every live script is in `scripts/`, grouped by pipeline stage, with code shared between scripts extracted into a shared module (DRY where it really repeats, see section 4.3).
- Every dead, experimental or orphaned script, data file and report goes to `archive/`.
  Each archived item gets an entry in `archive/README.md`, plus a GitHub issue if reviving it could make sense.
- One canonical place for all file paths in code, so the next move is a one-line change.
- Loading a required input file that is missing raises an error instead of returning an empty result.
- The README has a short "where things live" map, and every new top-level data or code folder has a short `README.md`.
- `docs/`, `AGENTS.md` and the tests describe and enforce the new layout.
- A new year needs no edits to code or year lists in the `Makefile`.

Non-goals

- An installable Python package: no `pyproject.toml`, no `src/` layout, no console entry points.
  Scripts stay plain scripts, run through `make`.
- Changes to the method, the counting rules or the attribution.
- New statistics, new data sources or new charts.
  Replacing Flourish with charts in the repository is a follow-up issue, not part of this work.
- Fixing known method limitations listed in `docs/explanation/known-limitations.md`, except where this design says so.
- Adding a real dependency manager or lock file.

Anti-goals: these would make the work a failure even if everything technically runs.

- **A restructure that changes numbers.**
  Moving files and refactoring must not change any output.
  Regenerating outputs that were already stale is a separate, final step, see section 5, stage 5.
- **A missed path that produces wrong statistics without any error.**
  Today several loaders return `{}` when their file is missing.
- **Deleting content.**
  Everything leaves the live tree only by moving to `archive/`.
  The only exception is junk that was never content (`.DS_Store`).
- **Editing archived files** or moving files that are already in `archive/`.
- **A layout that needs the docs to be understood.**
  The docs explain it, but the folder names alone must already be self-explanatory.
- **One giant pull request** that nobody can review.

## 3. Constraints

- **Timing.** Start after the branch the maintainer is currently waiting for has been merged.
  Base the work on the then-current `origin/main`, not the local `main`.
  At the time of writing the local `main` is behind `origin/main`, and all eight old local feature branches are already merged.
- **Other open branches are ignored**, as the maintainer decided.
  These are PR #34 (`community-recognition-weighting`), `split-code-and-community-contributions` and `claude/extract-active-github-users-ANUfl`.
  Their authors rebase onto the new layout if they continue.
  Mention the restructure on PR #34 once stage 3 or stage 4 is merged.
- **Re-verify the inventory.** The inventory in section 6 was taken from the local `main` at `916bfa5`.
  `origin/main` has since gained `plip_organisation_stats.py` and the board of directors files for 2004–2019, and it has lost `fetch_board_members.py`.
  Before planning, re-run the inventory on the new base and correct section 6.
- **Repository rules in `AGENTS.md` apply.**
  - Work in a git worktree, on its own branch.
  - Update `docs/` in the same pull request as anything it describes.
  - Code changes get offline pytest tests, and data changes get format checks.
  - Draft specs and plans outside `docs/`.
    As the last step before each pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename.
  - End commits, pull requests, issues and comments with `Assisted-by: <model name>`.
- **Keep the docs tests green.**
  - `tests/test_docs_and_archive.py` requires every backticked file path in `docs/` to exist relative to the root.
  - It also requires every Make target named in the docs to exist.
  - It requires `archive/README.md` to list every top-level entry in `archive/`.
- **CI** runs `make check`, `make test` and `flake8 ... *.py tests/`.
  The root `*.py` globs in CI, the `Makefile` and `tests/test_docs_and_archive.py` must follow the scripts.
- **`.env` handling.**
  Some scripts find `.env` with `load_dotenv()`.
  Others open `.env` relative to the current directory: `plone_plips.py`, and some archived scripts.
  The token must keep working when scripts move.
  Never pass the token on the command line.
- The Make interface may change, but `docs/reference/make-targets.md` must describe it.
  Nothing outside the repository depends on target names or file paths.
  The Flourish charts point at uploaded data, not at raw GitHub URLs.

## 4. Decided parts

### 4.1 Top-level layout

Decided with the maintainer: the separation into curated, collected, derived and reports, and keeping data and reports committed.
The exact names are my call.

```
README.md  AGENTS.md  CLAUDE.md  Makefile  requirements*.txt  pytest.ini  .env.example  .gitignore
scripts/       all live code, by pipeline stage
curated/       hand-maintained input: edit by hand, every entry needs a public record
collected/     fetched by the collectors from GitHub and git; never edit by hand
derived/       computed from curated + collected; committed for transparency; never edit by hand
reports/       human-facing output (markdown reports, text summaries, graphs); never edit by hand
docs/          Sphinx documentation
tests/         offline pytest tests
archive/       history; not maintained, never edited
```

Inside each data folder (my call):

```
curated/
  mappings/                 organisations.csv, organisation_mapping_{sources,overrides,proposals}.csv,
                            commit_authors.csv, account_aliases.csv, bot_accounts.csv,
                            excluded_repositories.csv, mapping-github-username-to-fullname.csv
  community-contributions/  current data/community-contributions/ minus derived files
collected/
  contributors/             YYYY-plone-contributors.csv
  pr-interactions/          YYYY-plone-pr-interactions.csv
  volto/                    YYYY-volto-stats.csv
  plips/                    plone-plips.csv, plone-plips-detailed.csv
derived/
  organisation-contributors/  YYYY-plone-organisation-contributors.csv
  summaries/                  summary-past-*-years-*.csv
  yearly-activity-statistics.csv
  plone-plip-organisations.csv
  community-recognition/      YYYY-community-recognition-report.csv
reports/
  github-contributor-report.md  community-recognition.md  volto.md
  pr-interactions/            github-pr-interactions-report-YYYY.md
  summaries/                  STATISTICS-PAST-*-YEARS.txt
  graphs/                     *.png
```

- File names stay as they are, so a downloaded file still says what it is.
- `.cache/` stays where it is and stays ignored.
- Checkpoint files move with their data, and the ignore rule follows them.
- Each of `scripts/`, `curated/`, `collected/`, `derived/` and `reports/` gets a short `README.md` (my call).
  It says what the folder holds, whether to edit by hand, and which `make` targets write it.
  GitHub shows this file when someone opens the folder.

### 4.2 Scripts

Decided with the maintainer: plain scripts, no package, DRY where it makes sense.
The grouping is my call.

```
scripts/
  lib/        shared code: github_api.py, git_history.py, paths.py, loaders for the mapping files
  collect/    plone_contributors.py, plone_pr_interactions.py, volto_stats.py, plone_plips.py
  derive/     organisation_stats.py, multi_year_summary.py, yearly_activity_analysis.py, plip_organisation_stats.py
  report/     generate_contributor_report.py, generate_community_recognition_report.py,
              generate_volto_team_report.py, generate_yearly_graphs.py
  tools/      get_github_name.py, analyze_independent_contributors.py
```

- Scripts run from the repository root as modules, e.g. `python -m scripts.collect.plone_contributors`.
  `make` does this, so maintainers keep using `make`.
  `scripts/` and its subfolders are plain folders, with no packaging metadata.
  Python 3 namespace packages make `python -m` and the imports work.
  An empty `__init__.py` per folder is the builder's call if a tool needs it.
- Internal imports become `from scripts.lib import github_api`, and so on.
  `tests/conftest.py` keeps adding the root to `sys.path`.
- Script file names stay as they are, except where a name is wrong for its new place.
  Any rename is the builder's call and is listed in the pull request.

### 4.3 Shared code (DRY)

Extract only what really repeats today:

- **`scripts/lib/paths.py`**: every file and folder path used by more than one script, as `pathlib` constants relative to the repository root.
  It also holds functions such as `contributors_file(year)`.
  The paths are relative to the repository root, which is the current directory.
  `python -m scripts...` requires that anyway, and many tests rely on it: they `chdir` into `tmp_path` and write their fixtures there.
  All scripts and tests use these constants instead of string literals.
- **A mapping loader module** in `scripts/lib/`: one loader each for `organisations.csv`, the overrides, `bot_accounts.csv`, `excluded_repositories.csv`, `commit_authors.csv` and `account_aliases.csv`.
  Today `organisations.csv` is parsed separately in at least five scripts.
  The other loaders live in `plone_contributors.py` and are imported from there by unrelated scripts.
  The loaders keep the current behaviour exactly, with one exception: they raise an error when a required file is missing.
- **Year handling**: the "last completed year" default, and the 3-, 5- and 10-year windows, in one place, used by the `Makefile` and the scripts.
  Today the year ranges are hard-coded: the summaries end at 2024, and the recognition report reads files for 2025.
  **Stages 1–4 add the mechanism, but the defaults stay equal to the current values**: summaries end at 2024, and recognition runs for 2025.
  This way `make` reproduces the committed outputs.
  Switching the defaults to "last completed year" happens in stage 5, together with the regeneration (my call).

### 4.3a Missing inputs (my call)

- The mapping files are always required: a missing file raises an error.
- In the recognition report, a missing `community-contributions` folder, or a year with no curated files at all, raises an error.
  A single missing kind of data in a year that has others stays a warning, because some kinds didn't exist in some years.
  A list of expected kinds per year would be a method decision and is out of scope.
- A missing yearly organisation file for a year inside the requested range raises an error instead of being skipped.

### 4.3b PR interaction report (my call)

`reports/github-pr-interactions-report-YYYY.md` is written by the collector `plone_pr_interactions.py`, from data held in memory.
That breaks the stage separation, and it can't be checked offline.
If `YYYY-plone-pr-interactions.csv` holds everything the report shows, move the report writing into a `scripts/report/` script that reads the CSV.
Check this in stage 3: regenerated reports must match the committed ones apart from timestamps.
If the CSV isn't enough, leave the report in the collector, and document the exception in `scripts/README.md` and the docs.
Don't widen the CSV, because that would be a data change.

Duplicated logic beyond these three items is the builder's call.
Extract it only if it is the same code in several scripts, not just similar.

### 4.4 Archive

Decided with the maintainer: archive, don't delete; open an issue where revival could make sense.
The bundle layout is my call.

- Archived items go into **one folder per archived topic** below `archive/`, with code, data and output together, so a revival starts in one place.
  This breaks the old "original path below `archive/`" convention on purpose: 29 npm files and a dozen scripts would bury the archive root.
  The README table records each item's original path.
- Existing archive content stays exactly where it is.
- `archive/README.md` gets one row per bundle: original paths, date archived, why it was archived, and a link to the revival issue if there is one.
- Proposed bundles, to be checked against the re-run inventory:

| Bundle | Contents | Why | Revival issue (my proposal) |
|---|---|---|---|
| `legacy-collectors/` | `plone_contributor_statistics.py`, `plone_companies.py` | Replaced by the current collectors; docs say "not part of the current method" | No |
| `plip-levels/` | `analyze_plip_contributor_levels.py`, `generate_plip_3tier_levels.py`, `plip_stats.py` | Superseded PLIP level experiments; `plip_stats.py --year` crashes (#44) | No new issue; reference #18 and #44 |
| `package-statistics/` | `npm_package_stats.py`, `volto_addon_discovery.py`, `pypi_package_statistics.py`, `npm_mapping.txt`, all `npm-packages-*` files | One-off snapshot from 2025-08-20; the PyPI target was broken | Yes: "Packages published per organisation (npm, PyPI)" |
| `cmfplone-releases/` | `fetch_cmfplone_releases.py`, `filter_releases.py`, `cmfplone-releases.csv` | Not used by any statistic | No, unless the maintainer sees a use |
| `flourish/` | `create_organization_flourish_csv.py`, `create_individual_contributors_flourish_csv.py`, all six Flourish CSVs (root and `data/`) | External service; the maintainer prefers charts that live in the repository | Yes: "Charts in the repository instead of Flourish" |
| `orphan-outputs/` | `reports/plips.md` (no generator), `plone-organizations-bar-chart-race.csv`, `graphs/commits_prs_trend.png` (no longer generated) | Can't be reproduced | `reports/plips.md`: yes, "PLIP report generator", or fold it into #14 |

- `.DS_Store` is removed from git and added to `.gitignore`.
  It is junk, not content.
- Make targets that call archived or missing scripts are removed:
  - `run-contributors`, `run-organisations`, `analyze-plip-levels`, `npm-packages`, `pypi-packages` and `generate-plip-report`;
  - the two `flourish-*` targets;
  - `run-plip-organisations`, re-pointed if `plip_organisation_stats.py` now exists on `origin/main`;
  - the broken `run-all`.

  `KNOWN_MISSING` in `tests/test_docs_and_archive.py` should end up empty.
- Issues are created only after the maintainer has approved the list.
  Each one links the bundle and says what reviving it would take.
  Each one ends with `Assisted-by: <model name>`.

### 4.5 Makefile

- Replace the per-year copies (`run-stats-2000` … `run-stats-2025`, the same for organisation stats, PR interactions and Volto) with a `YEAR` variable.
  For example, `make run-stats YEAR=2026`, which defaults to the last completed year.
  Keep the `*-all-years` targets.
  Target names are the builder's call, documented in `make-targets.md`.
- One umbrella target that runs a full year in pipeline order: collect, derive, report.
  The name is the builder's call, e.g. `make year YEAR=2026`.
  This is the main entry point for the "prepare a new year" reader.
- `make clean` deletes only ignored files: caches, checkpoints, `__pycache__`, `docs/_build`.
  It never deletes committed files.
- `check`, `lint`, `format` and CI glob `scripts/**/*.py` and `tests/`, not the root `*.py`.

### 4.6 Documentation

- Every pull request updates the docs it affects, as `AGENTS.md` requires:
  `docs/reference/{data-files,mapping-files,data-sources,recognition-files,make-targets}.md`, how-tos, explanations, glossary, `AGENTS.md` (the Layout section) and `README.md`.
- The README gets a "Where things live" section with the top-level map, one line per folder, and a link to the docs.
- A new how-to, "Prepare the numbers for a new year": the umbrella target, what to check by hand, what to commit.
  This is my call; drop it if it duplicates `collect-data-again.md`, and extend that page instead.
- `known-limitations.md` loses the entries that the restructure resolves, such as the broken targets and the missing generators.

### 4.7 Guards (tests)

- An offline test that each loader raises an error on a missing file.
- A layout test: the root contains only an allowed list of files and folders, and each of `scripts/`, `curated/`, `collected/`, `derived/` and `reports/` has a `README.md`.
  This keeps clutter from coming back (my call).
- Existing format checks and tests are updated to the new paths, via `paths.py` where possible.
- Tests that `chdir` into `tmp_path` and write fixtures by bare file name must create the new subfolders.
  An alternative is a `paths.py` that can be pointed at a temporary root.
  The mechanism is the builder's call.

## 5. Stages: one pull request each, in this order

Each stage leaves `main` working, with tests green and docs accurate.

1. **Safety net.** Introduce `paths.py` and the shared loaders while the scripts are still at the root.
   Make missing files raise an error, add the tests, and untrack `.DS_Store`.
   No file moves.
2. **Archive.** Move the bundles from section 4.4 into `archive/`, remove the dead Make targets, and update `archive/README.md` and the docs.
   Create the approved revival issues.
3. **Move scripts.** Move them into `scripts/`, then update imports, the `Makefile`, CI, `conftest.py` and the docs.
   Also do the `YEAR` variable in the `Makefile` here, or in its own pull request, as the builder decides.
4. **Move data.** Move the data into `curated/`, `collected/`, `derived/` and `reports/`.
   Change only `paths.py` constants, folder READMEs, the ignore rules, docs, `AGENTS.md`, the README map, and the layout test.
5. **Regenerate stale outputs.** This is a separate pull request, and it changes numbers on purpose.
   For example, `reports/volto.md` was last generated on 2026-06-24, and the summary windows end at 2024 although 2025 is complete.
   Switch the year defaults to "last completed year" here.
   New summary windows replace the old `summary-past-*` files, because regenerated outputs are not archived and git history keeps them (my call).
   The maintainer decides whether to do this stage.

**Verification for stages 1–4 (no numbers change).**
Before a stage, run every derive and report step offline from the committed inputs into a scratch copy.
Run them again after the stage, and compare.
The outputs must be byte-identical, apart from timestamps such as `Generated on:` lines.
Collectors need the GitHub API and are not re-run.
Their code paths are covered by the existing offline tests.

## 6. Inventory used for this design

The full inventory is in the two subagent reports from 2026-10-18.
Re-verify both on the new base.
Key facts:

- **Live scripts** (wired into `make`, imported or tested): `plone_contributors`, `git_history`, `github_api`, `plone_pr_interactions`, `organisation_stats`, `multi_year_summary`, `generate_contributor_report`, `generate_community_recognition_report`, `volto_stats`, `generate_volto_team_report`, `plone_plips`, `yearly_activity_analysis`, `generate_yearly_graphs` and `analyze_independent_contributors`.
  `get_github_name` is a manual tool.
  `plip_organisation_stats` is new on `origin/main`.
- **Silent loaders**: `plone_contributors.py` lines 62–97 and `organisation_stats.py` lines 31 and 43 return `{}` when a file is missing.
- **Links between derived files at the root** (on `origin/main` at `dcafeae`):
  - `generate_community_recognition_report` reads `plone-plips-detailed.csv` and the yearly organisation files directly;
  - no script reads the `summary-past-*` files or `plone-plip-organisations.csv` any more, but Make targets still write them, so they stay live outputs;
  - `generate_yearly_graphs` reads `yearly-activity-statistics.csv`;
  - the PLIP level scripts, which are being archived, read `plone-plips.csv`.
- **The Flourish files exist twice.** The root copies are stale, and the `data/` copies are current.
- **`data/community-contributions/2025-community-recognition-report.csv`** is derived but lives with the curated data.
- **`community-recognition-points.csv` is curated, but no script reads it**, also on `origin/main`.
  Only a docstring names it.
  It stays in `curated/community-contributions/`.
- **`make clean` deletes committed files.**
  Some of them can't be regenerated.

## 7. Left to the builder

- Splitting stages into smaller pull requests, and the order of steps within a stage.
- Exact Make target names, and whether to keep aliases for old names (not required).
- Whether the scripts need `__init__.py` files.
- Further DRY extraction beyond section 4.3, within the "identical code only" rule.
- How tests point `paths.py` at a temporary root.
- Renames of scripts whose names are misleading in their new place.
- The wording of folder READMEs and of the archive rows.
