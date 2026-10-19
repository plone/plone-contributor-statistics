# Data Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mapping files and the curated community files with keyed registers (people, identities, affiliations, organisations) described by a Frictionless Table Schema, read through one model library, migrated by a script that changes no code attribution.

**Architecture:** `curated/schemas/*.json` and `curated/datapackage.json` define every curated file; `scripts/lib/model/` is the only reader of `curated/` and resolves people and organisations; a migration script builds the new files from the old ones; every consumer (collectors, derive, report, tools) is switched to the model; `tests/test_reproducible_outputs.py` gates the result.

**Tech Stack:** Python 3.12, `csv`, `dataclasses`, `frictionless>=5.18` (Table Schema, Data Package, custom checks), pytest, Make, Sphinx/MyST for the docs.

**Spec:** https://github.com/plone/plone-contributor-statistics/issues/139#issuecomment-6276443815 (copied unchanged into `archive/specs-and-plans/2026-10-19-data-structure-spec.md` in Task 16; this plan goes next to it).

## Global Constraints

- Work in a git worktree on branch `data-structure` (repo rule; `superpowers:using-git-worktrees`).
- Every commit message ends with `Assisted-by: Claude Fable 5.1` and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Code changes get offline pytest tests; the GitHub API is replaced by fakes. Data changes get format checks.
- Never commit `.env` or a token; collectors take `GITHUB_TOKEN` from the environment.
- Column names in the new files are `snake_case`; ids match `^[a-z0-9][a-z0-9-]*$`; years are `YYYY`; `source` cells contain an `https?://` link (except identities of kind `email`).
- No default in affiliations: a year no row covers is `Unmapped`; `Unmapped` is never written into a curated file.
- A set cell holds `;`-separated keys, no empty elements, no duplicates; only the columns `trainers`, `speakers`, `organisers`, `organisations` (and `aliases`) are sets.
- Code attribution (`derived/organisation-contributors/*.csv`) changes in this PR only in the `contributors` cells where a no-login person becomes `person:<id>`.
- Prose in docs: no numbers or rankings. Documentation changes land in the same PR as the files they describe.
- The migration script is re-runnable offline from the old files at `499a4af`; the profile names it needs are a committed input.

## Review Focus

1. A set cell with an empty element (`pbauer;;tschorr`, `pbauer;`) must fail with file, row and column — Task 4 (`test_set_keys_rejects_empty_element`).
2. A login spelled with another case than `people.github` (`PBauer` in collected data) must still resolve to the person — Task 5 (`test_person_for_login_ignores_case`).
3. Two affiliations of one person that overlap by one year (`2010–2016` and `2016–`) must fail naming both rows — Task 4 (`test_affiliation_overlap_names_both_rows`).
4. A new organisation whose `name` folds to an existing name or alias (`Kitconcept GmbH`, `Ecreall`) must fail — Task 4 (`test_name_fold_rejects_near_duplicate`).
5. A `person:<id>` username in `collected/` whose id is not in `people.csv` must fail the test suite, not crash a derive script — Task 8 (`test_collected_person_ids_exist`).

---

### Task 1: Worktree, dependency, schema files

**Files:**
- Modify: `requirements.txt`
- Create: `curated/schemas/people.json`, `identities.json`, `affiliations.json`, `organisations.json`, `affiliation-proposals.json`, `bot-accounts.json`, `excluded-repositories.json`, `board-of-directors.json`, `team-leaders.json`, `release-managers.json`, `podcasts.json`, `plone-conference-trainings.json`, `world-plone-day-talks.json`, `sprints.json`, `plone-conference.json`, `world-plone-day-event.json`, `community-recognition-levels.json`, `community-recognition-points.json`, `plips-before-github.json`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces: one Table Schema JSON per kind, file name = kind. Field names as the spec's tables, `snake_case`. Set columns are `string` fields with `"x-set": "people"` or `"x-set": "organisations"` (custom property naming the referenced resource). Registers: `people` primaryKey `id`; `organisations` primaryKey `id`, `name` unique; `identities` foreignKey `person`→`people.id`; `affiliations` foreignKeys `person`→`people.id`, `organisation`→`organisations.id`; community kinds: scalar `person`→`people.id`, `organisation`→`organisations.id`.
- Field details the implementer needs: years `integer` with `minimum: 2000`; `episodes` `integer`; `checked` `date`; `date` (WPD event) `date`; `start`/`end` (sprints) `string` with pattern `^\d{4}(-\d{2}(-\d{2})?)?$` (sources give partial dates); `source` `string` with pattern `.*https?://.*` and `required: true` everywhere except `identities`; enums: `kind` (people? none; identities `name|email|login`; organisations `organisation|independent|foundation`), `role` `voting|non-voting`, `level` `strategic|community|` (empty allowed → not required, enum without empty), `format` `in person|hybrid|online`, `type` `Talk|Teaser|Announcement|Welcome|Recap|Duplicate|Opening|Full stream|Newsroom`. `community-recognition-levels.json`, `community-recognition-points.json` and `plips-before-github.json` describe today's columns unchanged.

- [ ] **Step 1: Create the worktree and branch**

Run: `git worktree add ../plone-contributor-statistics-data-structure -b data-structure origin/main` (via `superpowers:using-git-worktrees`); all later commands run there.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_schemas.py
import json
from pathlib import Path
from frictionless import Schema

SCHEMAS = Path('curated/schemas')
KINDS = {'people', 'identities', 'affiliations', 'organisations', 'affiliation-proposals', 'bot-accounts',
         'excluded-repositories', 'board-of-directors', 'team-leaders', 'release-managers', 'podcasts',
         'plone-conference-trainings', 'world-plone-day-talks', 'sprints', 'plone-conference',
         'world-plone-day-event', 'community-recognition-levels', 'community-recognition-points',
         'plips-before-github'}

def test_every_kind_has_a_valid_schema():
    assert {p.stem for p in SCHEMAS.glob('*.json')} == KINDS
    for path in SCHEMAS.glob('*.json'):
        assert Schema.from_descriptor(json.loads(path.read_text())).to_descriptor()

def test_people_and_organisations_have_opaque_ids():
    for kind in ('people', 'organisations'):
        schema = json.loads((SCHEMAS / f'{kind}.json').read_text())
        field = next(f for f in schema['fields'] if f['name'] == 'id')
        assert schema['primaryKey'] == ['id']
        assert field['constraints']['pattern'] == '^[a-z0-9][a-z0-9-]*$'

def test_set_columns_name_their_register():
    expected = {'plone-conference-trainings': {'trainers': 'people'},
                'world-plone-day-talks': {'speakers': 'people', 'organisations': 'organisations'},
                'sprints': {'organisers': 'people', 'organisations': 'organisations'},
                'plone-conference': {'organisers': 'people'},
                'world-plone-day-event': {'organisers': 'people', 'organisations': 'organisations'}}
    for kind, sets in expected.items():
        fields = json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']
        assert {f['name']: f['x-set'] for f in fields if 'x-set' in f} == sets

def test_source_requires_a_link_except_for_identities():
    for path in SCHEMAS.glob('*.json'):
        fields = {f['name']: f for f in json.loads(path.read_text())['fields']}
        if 'source' in fields and path.stem != 'identities':
            assert fields['source']['constraints']['pattern'] == '.*https?://.*'
            assert fields['source']['constraints']['required'] is True
```

- [ ] **Step 3: Run it to verify it fails**

Run: `pip install 'frictionless>=5.18' && python -m pytest tests/test_schemas.py -v`
Expected: FAIL, `curated/schemas` has no files.

- [ ] **Step 4: Add `frictionless>=5.18` to `requirements.txt` and write the nineteen schema files**

Each file: `{"fields": [...], "primaryKey": [...], "foreignKeys": [...]}` with a one-sentence `description` per field (the docs generator in Task 14 prints them). Keep `missingValues: [""]` (default).

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt curated/schemas tests/test_schemas.py
git commit -m "Describe every curated file with a Table Schema (#139)"
```

---

### Task 2: Data package generator

**Files:**
- Create: `scripts/tools/datapackage.py`
- Create: `curated/datapackage.json` (generated)
- Modify: `scripts/lib/paths.py` (add `SCHEMAS_DIR = Path('curated/schemas')`, `DATAPACKAGE = Path('curated/datapackage.json')`, `PEOPLE`, `IDENTITIES`, `AFFILIATIONS`, `AFFILIATION_PROPOSALS`; keep the old constants until Task 13)
- Test: `tests/test_datapackage.py`

**Interfaces:**
- Produces: `build_package(root: Path = Path('.')) -> dict` — the descriptor: one resource per CSV under `curated/`, `name` = file stem with `/` and `_` turned into `-` (e.g. `community-contributions-2023-sprints` → shorten to `2023-sprints`; registers `people`, `organisations`, …), `path` relative to `curated/`, `schema` = `schemas/<kind>.json`, where kind = the file stem for registers and the stem without the leading `YYYY-` for community files. `kind_of(path: Path) -> str`. `main()` writes `curated/datapackage.json` with `indent=1`, sorted keys, trailing newline.
- Resource names referenced by foreign keys must be exactly `people` and `organisations`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_datapackage.py
import json
from pathlib import Path
from scripts.tools import datapackage

def test_kind_of():
    assert datapackage.kind_of(Path('curated/community-contributions/2023-sprints.csv')) == 'sprints'
    assert datapackage.kind_of(Path('curated/mappings/affiliation_proposals.csv')) == 'affiliation-proposals'
    assert datapackage.kind_of(Path('curated/plips/plone-plips-before-github.csv')) == 'plips-before-github'

def test_build_package_lists_every_curated_csv(tmp_repo):
    (tmp_repo / 'curated/mappings/people.csv').write_text('id,name,github,source\n')
    (tmp_repo / 'curated/community-contributions/2023-sprints.csv').write_text('sprint\n')
    descriptor = datapackage.build_package(tmp_repo)
    names = {r['name']: r for r in descriptor['resources']}
    assert names['people']['schema'] == 'schemas/people.json'
    assert names['2023-sprints']['path'] == 'community-contributions/2023-sprints.csv'

def test_committed_datapackage_is_current():
    committed = json.loads(Path('curated/datapackage.json').read_text())
    assert committed == datapackage.build_package()
```

`tmp_repo` is the fixture in `tests/conftest.py`; `build_package` must accept a root and resolve `curated/` below it.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_datapackage.py -v` — Expected: FAIL, no module `scripts.tools.datapackage`.

- [ ] **Step 3: Implement `scripts/tools/datapackage.py` and the new `paths` constants; run `python -m scripts.tools.datapackage`**

Resource descriptor: `{"name", "path", "schema", "format": "csv", "encoding": "utf-8", "dialect": {"csv": {"delimiter": ","}}}`. The generator walks `curated/**/*.csv` sorted.

- [ ] **Step 4: Run the test to verify it passes** — `python -m pytest tests/test_datapackage.py -v` — PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tools/datapackage.py scripts/lib/paths.py curated/datapackage.json tests/test_datapackage.py
git commit -m "Generate curated/datapackage.json from the schemas and the files (#139)"
```

---

### Task 3: Profile names input for the migration (the one online step)

**Files:**
- Create: `scripts/tools/migrate_data_structure.py` (only the `fetch-names` subcommand for now)
- Create: `scripts/tools/migrate_data/profile_names.csv` (committed output: `login,name,fetched`)
- Test: `tests/test_migrate_fetch_names.py`

**Interfaces:**
- Consumes: `scripts.tools.unmatched_names.fetch_profile_names(logins, token) -> dict[login, name]` (exists, GraphQL) and `scripts.lib.github_api`.
- Produces: `logins_without_a_name(root) -> set[str]`: logins in `organisations.csv` Team cells, overrides, sources, `commit_authors.csv`, `account_aliases.csv` (main accounts) that appear in no community person column and have no fullname row. `write_profile_names(names: dict, path)` sorted by login, `fetched` = today's date.

- [ ] **Step 1: Write the failing test** (`fetch_profile_names` replaced by a fake returning `{'tisto': 'Timo Stollenwerk', 'nobody': ''}`): `test_logins_without_a_name_skips_named_logins` on a `tmp_repo` with a fullname row for `pbauer` and a Team cell `pbauer;tisto` → `{'tisto'}`; `test_write_profile_names_uses_login_when_profile_has_no_name` → row `nobody,nobody,<date>`.
- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement the two functions and `main()` with `fetch-names --out PATH`; token from `GITHUB_TOKEN` only.**
- [ ] **Step 4: Run the tests; PASS. Then run the real fetch once:** `GITHUB_TOKEN=… python -m scripts.tools.migrate_data_structure fetch-names --out scripts/tools/migrate_data/profile_names.csv` and look at the result (about 150 rows).
- [ ] **Step 5: Commit** — `"Fetch the profile names the migration needs, once (#139)"`.

---

### Task 4: Custom checks and the check tool

**Files:**
- Create: `scripts/lib/model/__init__.py` (empty for now), `scripts/lib/model/names.py`, `scripts/lib/model/checks.py`
- Create: `scripts/tools/check.py`
- Modify: `Makefile` (`check:` runs `python -m scripts.tools.check` after `pip check`; `help` text)
- Test: `tests/test_checks.py`

**Interfaces:**
- Produces, in `names.py`: `fold(text: str) -> str` (NFKD, drop combining marks, casefold, collapse whitespace, strip punctuation) and `slugify(text: str) -> str` (NFKD → ASCII, lower, `[^a-z0-9]+` → `-`, strip `-`). The only two text normalisations in the code base.
- Produces, in `checks.py`: Frictionless `Check` subclasses
  - `SetKeys(field: str, keys: set[str])` — type `set-keys`; per row: split on `;`, strip; error for an empty element, a duplicate, or an element not in `keys`.
  - `AffiliationOverlap()` — type `affiliation-overlap`; `validate_end` yields one error per overlapping pair, naming both row numbers.
  - `NameFold(existing: dict[str, str])` — type `name-fold`; error when a row's `name` or an alias folds to another row's name or alias.
  - `Sorted(fields: list[str], casefold: bool)` — type `not-sorted`.
  - `UniqueCasefold(field: str)` — type `unique-casefold` (for `people.github`).
  - `LinkUnlessEmail()` — type `source-link`, identities only.
  - `checks_for(resource_name: str, package) -> list[Check]` — the mapping: registers get their checks; community resources get `SetKeys` per `x-set` field, with keys read from the referenced resource's primary key column.
- Produces, in `check.py`: `validate(root: Path = Path('.')) -> list[tuple[str, int | None, str | None, str]]` (file, row, field, message), using `frictionless.Package(paths.DATAPACKAGE).validate(checks=...)` per resource; `main()` prints one line per error `file:row:field: message`, exit 1 on errors, and for a `foreign-key` or `set-keys` error appends `nearest: a, b, c` (three closest ids by `difflib.get_close_matches`).

- [ ] **Step 1: Write the failing tests** (a `tmp_package` fixture in the test file copies `curated/schemas` into `tmp_repo`, writes the given CSV files and runs `datapackage.main()` there):

```python
def test_fold_and_slugify():                               # fold('Ecréall ') == fold('ecreall'); slugify('Víctor Fernández de Alba') == 'victor-fernandez-de-alba'
def test_set_keys_rejects_empty_element(tmp_package):      # trainers = "pbauer;;tschorr" → one set-keys error, rowNumber 2, fieldName 'trainers'
def test_set_keys_rejects_unknown_key(tmp_package):        # trainers = "pbauer;nobody" → message contains 'nobody'
def test_affiliation_overlap_names_both_rows(tmp_package): # rows 2010-2016 and 2016- for one person → message contains '2' and '3'
def test_name_fold_rejects_near_duplicate(tmp_package):    # organisations 'Ecréall' and 'Ecreall' → name-fold error
def test_check_main_prints_file_row_field(tmp_package, capsys): # output line starts with 'curated/community-contributions/2023-plone-conference-trainings.csv:2:trainers:'
def test_check_hints_nearest_ids(tmp_package, capsys):     # 'nobody' → 'nearest:' line mentions an existing id
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement `checks.py` and `check.py`; wire `make check`.**
- [ ] **Step 4: Run the tests; PASS.**
- [ ] **Step 5: Commit** — `"Add the custom checks and python -m scripts.tools.check (#139)"`.

---

### Task 5: The model library: registers

**Files:**
- Create: `scripts/lib/model/schema.py`, `scripts/lib/model/registers.py`; extend `scripts/lib/model/__init__.py`
- Test: `tests/test_model_registers.py`

**Interfaces:**
- `schema.py`: `read_rows(path: Path) -> list[dict]` — typed rows via `frictionless.Resource(path=..., schema=<schema for kind_of(path)>).read_rows()`, each row a plain dict (ints, dates, `None` for empty); raises `FileNotFoundError` when missing. `split_set(value: str | None) -> tuple[str, ...]`.
- `registers.py` dataclasses (frozen): `Person(id, name, github, source)`, `Identity(person, kind, value, source)`, `Affiliation(person, organisation, from_year, to_year, source, checked, notes)`, `Organisation(id, name, kind, aliases: tuple, notes)`.
- `class Registry` built by `load_registry(mappings_dir=paths.MAPPINGS_DIR) -> Registry`:
  - `people: dict[str, Person]`, `organisations: dict[str, Organisation]`
  - `person_for(*, login=None, email=None, name=None) -> Person | None`: login matches `github` or an identity of kind `login`, ignoring case; email lower-cased against identities of kind `email`; name folded (same `fold` as `checks.py`) against `people.name` and identities of kind `name`, `None` when ambiguous.
  - `person_for_username(username: str) -> Person | None`: `person:<id>` → `people[id]`, else `person_for(login=username)`.
  - `organisation_of(person_id: str, year: int) -> str`: the `organisations[id].name` of the affiliation covering `year`, else `UNMAPPED`.
  - `organisation_for_username(username: str, year: int) -> str`.
  - `login_organisations(year: int) -> dict[str, str]`: `{github login: organisation name}` for every person with a login, plus alias logins, for the year — the drop-in for `load_organisation_mapping(year)` (only logins with an affiliation that year appear).
  - `organisation_name(org_id: str) -> str`, `organisation_id(name_or_alias: str) -> str | None` (fold match).
  - `is_counted_organisation(name: str) -> bool`: kind `organisation` (replaces the `(independent)` suffix parsing and `NOT_ORGANISATIONS`).
  - `display_name(username: str) -> str`: `people.name` for `person:<id>` and for logins in the register, else the username.
- `__init__.py` re-exports: `UNMAPPED = 'Unmapped'`, `Registry`, `load_registry`, the dataclasses, `load_bot_accounts`, `load_excluded_repositories` (moved from `mappings.py`).

- [ ] **Step 1: Write the failing tests** on a `tmp_repo` with small register files:

```python
def test_person_for_login_ignores_case(registry):          # github 'pbauer' → person_for(login='PBauer').id == 'philip-bauer'
def test_person_for_second_account(registry):              # identity login 'bobdobbs666' → 'alan-runyan'
def test_person_for_name_is_none_when_ambiguous(registry)  # two people with identity name 'Kim' → None
def test_organisation_of_without_affiliation_is_unmapped(registry)  # 2003 → 'Unmapped'
def test_organisation_of_open_range(registry)              # from 2019, to None → 2026 → 'Syslab'
def test_login_organisations_omits_logins_without_affiliation(registry)
def test_organisation_for_username_person_prefix(registry) # 'person:alan-runyan', 2004 → 'Enfold'
def test_is_counted_organisation(registry)                 # independent → False, foundation → False, organisation → True
def test_read_rows_types(tmp_repo)                         # affiliations from_year is int, to_year None, checked is date
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement `schema.py`, `registers.py`, `__init__.py`.**
- [ ] **Step 4: Run the tests; PASS.**
- [ ] **Step 5: Commit** — `"Add the model library: people, identities, affiliations, organisations (#139)"`.

---

### Task 6: The model library: community roles and events

**Files:**
- Create: `scripts/lib/model/community.py`
- Test: `tests/test_model_community.py`

**Interfaces:**
- Dataclasses (frozen): `Role(kind, year, person: str (id), label, detail, file, line, source, notes)`; `Event(kind, year, name, organisations: tuple[str, ...] (ids), organisers: tuple[str, ...], sources: tuple, level, file, line)`; `Item(kind, year, key, people: tuple, organisations: tuple, file, line, source, notes, fields: dict)` for talks, trainings, podcasts rows as such (the recognition script needs the row, the page needs the role).
- `ROLE_KINDS`, `TALK_TYPES = ('Talk',)`, `IN_PERSON = ('in person', 'hybrid')`, `MIN_EPISODES = 5`, `EVENT_KINDS` — the single definitions.
- `roles(year, community_dir=paths.COMMUNITY) -> list[Role]`: one per person and role; per-person kinds from `person`; set kinds from `trainers`/`speakers`/`organisers`; talks only with `type in TALK_TYPES`; labels as today's `ROLE_KINDS` (`Board`, `Team lead`, `Release manager`, `Trainer`, `Talk`, `Sprint organiser`, `Podcast`, `Conference organiser`).
- `events(year) -> list[Event]`: conference (one event, organisations from all rows), sprints (one per row, `level`), WPD events (`format in IN_PERSON`).
- `items(year, kind) -> list[Item]`: the rows of a kind with their sets split, for the recognition script.
- A missing file yields `[]`; a missing column raises `KeyError` with the file name.

- [ ] **Step 1: Write the failing tests** on `tmp_repo` with one file per kind in the new format: `test_roles_split_set_columns` (training with `trainers=pbauer;tschorr` → two `Trainer` roles), `test_roles_skip_non_talks`, `test_events_sprint_level_and_organisations`, `test_events_wpd_online_is_no_event`, `test_items_podcasts_episodes_int`, `test_missing_file_is_empty`.
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement `scripts/lib/model/community.py`.**
- [ ] **Step 4: Run the tests; PASS.**
- [ ] **Step 5: Commit** — `"Add the model library: community roles, events and items (#139)"`.

---

### Task 7: The migration script

**Files:**
- Modify: `scripts/tools/migrate_data_structure.py` (add `run` subcommand)
- Test: `tests/test_migrate_data_structure.py`

**Interfaces:**
- Consumes: the old loaders in `scripts/lib/mappings.py`, `scripts/lib/people.py`, `scripts/lib/community.py` (still present), `profile_names.csv`, the alias table `org_mapping` in `generate_community_recognition_report.normalize_organization_name` (import the dict by extracting it into a module constant `ORGANISATION_ALIASES` first — a one-line refactor in that file).
- Produces: `migrate(root: Path, until: int, profile_names: Path) -> Report` where `Report` holds counts and lists (`people`, `identities`, `affiliations`, `proposals`, `dropped_aliases`, `renamed_usernames`, `cut_sources`); writes the new files, rewrites the community files and `collected/*/`, deletes the old mapping files; `main()` with `run --until 2026 --profile-names PATH [--report PATH]` prints the report as Markdown (pasted into the PR).
- Rules the implementer cannot infer:
  - **People.** Clusters: start from `people.build_person_index` on all records plus handles, profile links, `commit_authors` (name+login) and fullnames; each login is one person; each name without a login is one person. `id = names.slugify(name)`, on collision append `-2`, `-3`. `name`: the fullname spelling for a login, else `profile_names.csv`, else the most frequent spelling in the community data, else the login. `source`: the fullname row's source, else `https://github.com/<login>`, else the source link of the first community row naming the person.
  - **Identities.** Every other spelling → `name` with the source of the row that spells it so; `commit_authors` emails → `email` with their source; `account_aliases` → `login`; `changelog_names` rows → `name` (file is empty today).
  - **Organisations.** `id = slugify(name)`; `kind`: `independent` if the name ends with `(independent)`, `foundation` for `Plone Foundation`, else `organisation`; `aliases`: keys of `ORGANISATION_ALIASES` whose value folds to the name; alias rows whose target is no organisation are listed under `dropped_aliases`. Add `Plone Foundation` if missing.
  - **Affiliations.** For each person with a login and each year `2002..until`: `load_organisation_mapping(year).get(login)`; drop `Unmapped`; compress runs of equal organisation into ranges; a run from the `Team` entry: `source`/`checked` from `organisation_mapping_sources.csv`, `to` empty when the run reaches `until`, `notes = 'range from the current entry; years before <checked year> not verified (#139)'` when `from` is earlier than the `checked` year; a run from an override: that override's `source`, `checked` empty, `to` as the override says (empty when open).
  - **Community files.** Per kind, write the new header; `person` or set columns hold ids; per-person kinds with several names in one cell become one row each (copy the other columns); `source` = the old `Source` up to the first `; organisation of`, `; organisation from`, or `; <Name>:` (talks), else the whole cell; for talks without a `Source` the video URL; the cut remainder goes to `cut_sources` in the report; `notes` = old `Notes`; talks: `location` = `Event / Location`, drop `YouTube ID`; speaker cells matching `<Org> team` → `organisations` set (org by fold match), speakers empty. Organisation cells of person kinds: compare with `organisation_of(person, year)` after the affiliations are written — copied (`Source` says so) or equal → dropped; `Unmapped` → dropped; otherwise a row in `affiliation_proposals.csv` (`person, organisation, from=to=year, evidence = '<file>:<line>; <source link>'`). Organisation cells of event kinds → ids by fold match; an unknown spelling stops the run with the spelling and the file.
  - **Collected files.** In `collected/contributors/*.csv` and `collected/changelogs/*.csv`, a `username` equal to the `name` of a commit author without login becomes `person:<id>`.
  - **Old files** `organisations.csv` (old shape), `organisation_mapping_*.csv`, `commit_authors.csv`, `account_aliases.csv`, `mapping-github-username-to-fullname.csv`, `changelog_names.csv` are deleted at the end.

- [ ] **Step 1: Write the failing tests** on a `tmp_repo` filled with a miniature old structure (two organisations, one override, one `Unmapped` blocker, one fullname row with two spellings, one commit author without login, a 2016 trainings row with two trainers and a copied organisation, a 2023 sprint with three organisers and two organisations, a 2006 board row stating an organisation the mapping contradicts, a `profile_names.csv`):

```python
def test_people_get_slug_ids_and_names(migrated)         # 'philip-bauer' github 'pbauer'; no-login author 'alan-runyan' github ''
def test_second_spelling_becomes_identity(migrated)
def test_affiliations_have_no_default_and_no_unmapped(migrated)   # blocker gone; Team range notes mention 'not verified'
def test_override_becomes_dated_range(migrated)
def test_trainings_row_keeps_one_row_with_a_set(migrated) # trainers == 'philip-bauer;thomas-schorr', no organisation column
def test_board_row_is_split_and_conflict_goes_to_proposals(migrated)  # proposals has one row 2006-2006 with evidence containing the file name
def test_sprint_sets_are_ids(migrated)                    # organisers three ids, organisations two ids
def test_source_cell_is_cut_at_mapping_note(migrated)
def test_no_login_username_is_renamed_in_collected(migrated)  # 'person:alan-runyan'
def test_old_files_are_removed(migrated)
def test_output_validates(migrated)                        # scripts.tools.check.validate(root) == []
```

and, in a new `tests/test_curated_data.py`, the test that makes `make test` run the checks on the real data from now on:

```python
def test_curated_data_passes_the_checks():
    assert check.validate() == []
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement `migrate` and `run`; extract `ORGANISATION_ALIASES` in the recognition script.**
- [ ] **Step 4: Run the tests; PASS.**
- [ ] **Step 5: Run the migration on the real data:** `python -m scripts.tools.migrate_data_structure run --until 2026 --profile-names scripts/tools/migrate_data/profile_names.csv --report /tmp/migration-report.md && python -m scripts.tools.datapackage && python -m scripts.tools.check` — Expected: check prints nothing, exit 0. Read the report: the proposals count is in the order of the spec's estimates (about 65 + a dozen + 160); `dropped_aliases` lists only targets that are no organisation.
- [ ] **Step 6: Commit the script, its tests and the migrated data** — `"Migrate the mapping files and the curated data to the registers (#139)"`. (The consumers break from here until Task 12; that is expected inside the branch.)

---

### Task 8: Switch the derive scripts to the model

**Files:**
- Modify: `scripts/derive/organisation_stats.py` (lines 23, 29, 105–175, 231, 265), `scripts/derive/plip_organisation_stats.py` (lines 35–44), `scripts/derive/multi_year_summary.py` and `scripts/derive/yearly_activity_analysis.py` only if they import the old loaders (check with grep)
- Test: `tests/test_unmapped_in_reports.py`, `tests/test_changelog_entries_in_statistics.py`, `tests/test_plone_plips.py` (adapt fixtures to the new files), new `tests/test_collected_person_ids.py`

**Interfaces:**
- Consumes: `load_registry()`, `Registry.organisation_for_username(username, year)`, `Registry.login_organisations(year)`, `model.UNMAPPED`, `model.load_bot_accounts`.
- Produces: `organisation_stats.UNMAPPED` is now `from scripts.lib.model import UNMAPPED`; `plip_organisation_stats.organisation_lookup(registry=None) -> callable(login, year)`.

- [ ] **Step 1: Write the failing tests**: adapt the three test files' fixtures from `organisations.csv`/overrides to `people.csv` + `affiliations.csv` + `organisations.csv` (new shape); add

```python
def test_collected_person_ids_exist():      # every 'person:' username in collected/ is an id in curated/mappings/people.csv
```

- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Switch the two scripts; delete the `print` lines that reported the mapping size or keep them with the new counts.**
- [ ] **Step 4: Run the tests; PASS. Then:** `make run-organisation-stats run-plip-organisations && git diff --stat derived/organisation-contributors derived/plone-plip-organisations.csv` and `git diff derived/organisation-contributors | grep '^[-+][^-+]' | grep -v 'person:'` — Expected: the second command prints nothing (code attribution unchanged except the four renames).
- [ ] **Step 5: Commit** — `"Read the organisation of a login from the affiliations (#139)"`.

---

### Task 9: Switch the recognition script to the model

**Files:**
- Modify: `scripts/report/generate_community_recognition_report.py` (delete `normalize_organization_name`, `load_organisation_names`, `ORGANISATION_ALIASES`, the constants duplicated from the model; rewrite `calculate_community_recognition_points` sections 1–9 on `model.community.items/events` and `Registry.organisation_of`; `load_pr_data`/`load_plip_data` keep reading derived files by name)
- Test: `tests/test_recognition_method.py` (fixtures to the new format)

**Interfaces:**
- Consumes: `items(year, kind)`, `events(year)`, `Registry.organisation_of(person_id, year)`, `Registry.organisation_name`, `MIN_EPISODES`, `TALK_TYPES`, `IN_PERSON`.
- Produces: `calculate_community_recognition_points(year, data_dir, community_dir, plips_file, registry=None, contributions=None)` — the `organisations`/`overrides` parameters go; `Contribution.text` for a person uses `Registry.people[id].name`.
- Rules: an organiser role (sprint, conference) is not a point source; sprint, conference and WPD event points go to `organisations` of the event as before; training points split among the trainers' organisations of the year (one share per trainer, Unmapped shares dropped as before); talk points per distinct speaker organisation, plus the `organisations` set for team talks; podcast and team-lead splitting as before.

- [ ] **Step 1: Adapt `tests/test_recognition_method.py`** to write register files and new-format community files; keep every existing assertion about points.
- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Rewrite the sections.**
- [ ] **Step 4: Run the tests; PASS. Then `make community-recognition && git diff --stat derived/community-recognition reports/community-recognition.md`** — read the diff: every changed line is a deferred stated organisation (now the mapping's or Unmapped) or an organiser role; note anything else as a defect to fix.
- [ ] **Step 5: Commit** — `"Calculate the recognition points from the model (#139)"`.

---

### Task 10: Switch the community page to the model

**Files:**
- Modify: `scripts/derive/community_page.py` (drop `people`, `community`, `organisation_names`, `NOT_ORGANISATIONS`, `code_key`, `is_organisation`; `people_of_year` keys by person id for registered people and by login otherwise; `organisation_history` counts a role for `organisation_of(role.person, year)`; `history_of_year` renders `name` via `Registry.display_name`; `people_names` becomes `{fold(name): id or login}` from the register), `scripts/report/community_page.py` and `scripts/report/site/static/site.js` (search by name → id; the JavaScript normalisation stays only as a lookup into `names`), templates that print `organisation`
- Test: `tests/test_community_page_data.py`, `tests/test_community_page_render.py`

**Interfaces:**
- Consumes: `roles(year)`, `events(year)`, `Registry.person_for_username`, `Registry.organisation_of`, `Registry.is_counted_organisation`, `Registry.display_name`.
- Produces: `derived/community-page.json`: `people[year][].id` is the person id or the login; `people_names` maps folded display names and identity names to that key; board and team-lead entries carry `name` (display) and `organisation` (name).

- [ ] **Step 1: Adapt the two test files; add `test_people_active_counts_a_person_once_across_code_and_roles` (login in collected + role by id → one entry) and `test_organiser_role_counts_for_the_persons_organisation`.**
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Rewrite.**
- [ ] **Step 4: Run the tests; PASS. `make community-page site`; open `_site/index.html`, search a person by name and by login.**
- [ ] **Step 5: Commit** — `"Derive the community page from the model (#139)"`.

---

### Task 11: Switch the collectors and the changelog mapper

**Files:**
- Modify: `scripts/collect/plone_contributors.py` (lines 45, 134–136, 245–246, 341: emails and aliases from the registry; a no-login person is written as `person:<id>`), `scripts/collect/plone_pr_interactions.py` (line 27), `scripts/collect/plone_changelogs.py` (`name_mapper`), `scripts/lib/changelogs.py` (`NameMapper` takes a `Registry` and the collected logins; layers become: identities (`changelog_names`/`fullname`/`commit_authors` → `identity`), email, SVN local part of an email identity, alias → `identity`, bot, `login`; `matched_by` values: `identity`, `login`, `bot`, `unmatched`)
- Test: `tests/test_changelogs_counting.py`, `tests/test_changelogs_collect.py`, `tests/test_full_history_collection.py`, `tests/test_merge_commits.py` (fixtures), new `tests/test_name_mapper_registry.py`

**Interfaces:**
- Consumes: `Registry.person_for(email=…)`, `person_for(name=…)`, `person_for(login=…)`, identities of kind `email` for the SVN local-part rule.
- Produces: `changelogs.NameMapper(registry, logins, bots)`; `map(name) -> (username, layer)` where `username` is the login or `person:<id>`.

- [ ] **Step 1: Write/adapt the tests**: `test_svn_local_part_resolves_through_email_identity`, `test_name_equal_to_collected_login_resolves`, `test_no_login_person_is_written_with_prefix`, plus the fixture changes.
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the tests; PASS. `docs/reference/data-files.md` gets the new `matched_by` values in Task 14.**
- [ ] **Step 5: Commit** — `"Collect with the registry: emails, aliases and changelog names (#139)"`.

---

### Task 12: Switch the tools, remove the old loaders and tests

**Files:**
- Modify: `scripts/tools/unmatched_names.py` (propose `people.csv`/`identities.csv` rows), `scripts/tools/unmatched_changelog_names.py`, `scripts/tools/analyze_independent_contributors.py`, `scripts/tools/get_github_name.py` (use `scripts.lib.github_api`)
- Move: `scripts/lib/mappings.py`, `scripts/lib/people.py`, `scripts/lib/community.py` → `scripts/tools/migrate_data/legacy_mappings.py`, `legacy_people.py`, `legacy_community.py` (the migration script keeps working from these copies until the whole `migrate_data/` folder is archived after the merge; `load_bot_accounts` and `load_excluded_repositories` already live in the model since Task 5); update the imports in `migrate_data_structure.py`
- Delete: tests `test_mappings.py`, `test_people_identity.py`, `test_person_names_format.py`, `test_commit_authors.py`, `test_changelog_names_format.py`, `test_unmapped_and_mapping.py`, `test_curated_organisation_names.py`, `test_curated_community_format.py`, `test_community_records.py`, `test_conference_trainings_format.py`, `test_release_managers_format.py`, `test_team_leaders_format.py`, `test_world_plone_day_talk_types.py`
- Modify: `tests/test_board_of_directors_format.py` and `tests/test_sprints_format.py` → merge into `tests/test_curated_policy.py` with only the policy rules (a Board file for every year since 2004; a sprint with a `level` cites a Board minutes link; `release-managers` of the recognition year non-empty), on the model
- Modify: `tests/conftest.py` (`EMPTY_MAPPINGS` → `people.csv`, `identities.csv`, `affiliations.csv`, `organisations.csv`, `affiliation_proposals.csv`, `bot_accounts.csv`, `excluded_repositories.csv` headers); `scripts/lib/paths.py` (remove `OVERRIDES`, `SOURCES`, `PROPOSALS`, `COMMIT_AUTHORS`, `ACCOUNT_ALIASES`, `FULLNAMES`, `CHANGELOG_NAMES`)
- Test: `tests/test_unmatched_names.py`, `tests/test_unmatched_changelog_names.py` (adapt), new `tests/test_model_is_the_only_reader.py`

**Interfaces:**
- Produces: `test_model_is_the_only_reader`: no file under `scripts/` outside `scripts/lib/model/`, `scripts/tools/migrate_data_structure.py` and `scripts/tools/migrate_data/` contains `csv.DictReader(` or `open(` on a path under `curated/` (grep for `paths.COMMUNITY`, `paths.MAPPINGS_DIR`, `'curated/`).

- [ ] **Step 1: Write the failing test `test_model_is_the_only_reader` and adapt the tool tests.**
- [ ] **Step 2: Run to verify it fails (the old loaders still exist).**
- [ ] **Step 3: Switch the tools, delete the old modules and tests, write `test_curated_policy.py`.**
- [ ] **Step 4: `python -m pytest tests -x -q` — Expected: everything passes except `test_reproducible_outputs.py` (regenerated in Task 13).**
- [ ] **Step 5: Commit** — `"Make scripts/lib/model the only reader of curated/ (#139)"`.

---

### Task 13: Regenerate the outputs and audit the differences

**Files:**
- Modify: `derived/**`, `reports/**` (regenerated), `scripts/tools/migrate_data_structure.py` (add `audit` subcommand)

**Interfaces:**
- Produces: `audit(root) -> list[str]` — for `git diff --name-only derived reports` classifies every changed line: `person-rename` (`person:` cells), `deferred` (a row listed in `affiliation_proposals.csv`), `organiser-role` (community-page history `roles` counts of sprint/conference organisers), `positional-fix` (talk rows that had more speakers than organisations; trainings with an empty handle), `unexplained`. Prints the list; exit 1 on `unexplained`.

- [ ] **Step 1: Run `make run-organisation-stats run-plip-organisations three-year-summary five-year-summary ten-year-summary yearly-activity generate-report community-recognition community-page` with the `SUMMARY_END` and `RECOGNITION_YEAR` the Makefile defaults to.**
- [ ] **Step 2: Implement `audit`; run `python -m scripts.tools.migrate_data_structure audit`** — Expected: no `unexplained`; fix the migration or the consumer otherwise and return to Step 1.
- [ ] **Step 3: `python -m pytest tests/test_reproducible_outputs.py -q`** — PASS.
- [ ] **Step 4: Commit** — `"Regenerate the derived data and reports after the migration (#139)"` with the audit summary in the body.

---

### Task 14: Documentation

**Files:**
- Create: `scripts/tools/schema_docs.py` → writes `docs/reference/curated-files.md` from the schemas (one section per kind: file pattern, one row is, a table of fields with type, constraints and description, the custom checks that apply)
- Modify: `docs/reference/mapping-files.md` (replace by the registers section of the generated page: keep a short page that links), `docs/reference/data-files.md` (curated section → link; collected `username` and `matched_by` values), `docs/explanation/attribution.md` (affiliations, no default, no `Unmapped` rows), `docs/explanation/curated-community-data.md` (ids, sets, organisations only for entities, "Only people speak" kept), `docs/explanation/community-page.md` (matching by id), `docs/how-to/correct-an-organisation-mapping.md` → `add-an-affiliation.md`, `docs/how-to/add-curated-community-data.md` (find or add the person first), new `docs/how-to/add-a-person.md`, `docs/how-to/link-old-commits-to-a-person.md` (identities), `docs/how-to/find-a-contributor.md`, `docs/reference/make-targets.md` (`check`), `docs/glossary.md` (person id, affiliation, register), `AGENTS.md` (Layout and Rules: registers, ids, `make check`; drop the spelling and sorting rules the schema enforces), `curated/README.md`, `curated/mappings/README.md`
- Test: `tests/test_docs_and_archive.py` (add `test_curated_files_reference_is_current`: generated page equals `schema_docs.render()`)

- [ ] **Step 1: Write the failing test.**
- [ ] **Step 2: Implement `schema_docs.py`; write the docs; no numbers in prose.**
- [ ] **Step 3: `make docs`** — Expected: no warnings. `python -m pytest tests/test_docs_and_archive.py -q` — PASS.
- [ ] **Step 4: Commit** — `"Document the registers, the schema and the checks (#139)"`.

---

### Task 15: Editor tools

**Files:**
- Create: `scripts/tools/person.py`, `scripts/tools/affiliation.py`
- Modify: `Makefile` `help`, `docs/reference/make-targets.md` only if targets are added (they are not; the tools run as modules)
- Test: `tests/test_tool_person.py`, `tests/test_tool_affiliation.py`

**Interfaces:**
- `person.py`: `find(registry, query) -> list[Person]` (id, name fold, login, email, identity names); `add(mappings_dir, name, github, source) -> Person` appends to `people.csv` keeping the sort, id via `names.slugify` with the `-2`, `-3` collision rule of the migration; `main()` with `QUERY` or `--add NAME [--github LOGIN] --source URL`; prints CSV rows.
- `affiliation.py`: `explain(registry, person_id, year) -> str` — the organisation and the row (`affiliations.csv:<line>`) or `Unmapped (no row covers <year>)`.

- [ ] **Step 1: Write the failing tests** (`test_find_by_identity_name`, `test_add_generates_unique_id_and_keeps_sort`, `test_explain_names_the_row`).
- [ ] **Step 2: Run to verify they fail.** **Step 3: Implement.** **Step 4: PASS.**
- [ ] **Step 5: Commit** — `"Add the person and affiliation tools for editors (#139)"`.

---

### Task 16: Archive the spec and the plan, open the pull request

**Files:**
- Create: `archive/specs-and-plans/2026-10-19-data-structure-spec.md` (the issue comment, unchanged), `archive/specs-and-plans/2026-10-19-data-structure-plan.md` (this file, unchanged)

- [ ] **Step 1: Copy both files; `python -m pytest tests -q` and `make check docs`** — all PASS.
- [ ] **Step 2: Commit** — `"Archive the spec and the plan of the data structure (#139)"`.
- [ ] **Step 3: Open the PR** with: the migration report, the audit summary (which rows changed credit and why), the list of proposals to review, the follow-ups (review proposals; trim reaching-back ranges; delete `migrate_data_structure.py` and `migrate_data/` into `archive/`). Body ends with `Assisted-by: Claude Fable 5.1` and the generated-with line.
