# Community page: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A generated community page at the root of the GitHub Pages site, with the Sphinx docs moved to `/docs/`.
All of the page's numbers come from a committed, tested data file.

**Architecture:**

- **Data (PR 1):**
  - The recognition script additionally records where each point comes from.
  - Two library modules resolve people and read community records and events.
  - A derive script writes `derived/community-page.json`, which the reproducibility test covers.
- **Site (PR 2):**
  - A report script renders the page from that JSON with Jinja2 into `_site/`, which is gitignored.
  - `make site` also builds the Sphinx docs into `_site/docs/`.
  - CI publishes `_site/`.

**Tech stack:** Python 3.12, pandas, Jinja2 (new in `requirements.txt`), plain JavaScript and inline SVG (no charting library), pytest, GNU Make, Sphinx, GitHub Actions.

**Spec:** `2026-10-19-community-page-design.md`, next to this plan in the scratchpad; it is archived in PR 1.

## Global constraints

- `AGENTS.md` rules:
  - work in a worktree, one branch per PR (`community-page-data`, `community-page-site`);
  - docs change in the same PR;
  - code gets offline tests, data gets format checks;
  - the spec and plan go to `archive/specs-and-plans/` in PR 1;
  - commits and PRs end with `Assisted-by: Claude Opus 5.5` and no other attribution line.
- **No runtime dependency on external services.** No `<script src>`, `<link href>`, font, image or iframe from another origin.
  Links in `<a href>` to GitHub, plone.org, YouTube and the like are fine.
- **No ranked list of people's names in the HTML.**
  Per-person counts live only in the embedded JSON, keyed by login or name and sorted alphabetically.
- **No home-made templating.** Use Jinja2 `Environment` and `FileSystemLoader`.
- The first screen (headline numbers and organisation wall), the organisation details and the history are rendered as static HTML, readable without JavaScript.
  JavaScript adds tabs, people search and graphs.
- The page reads only the committed data file. The derive step reads only committed data, never GitHub.
- The recognition outputs (`derived/community-recognition/*.csv`, `reports/community-recognition.md`) stay byte-identical: `tests/test_reproducible_outputs.py` must keep passing.
- The docs contain no statistics or rankings in prose.

## Review focus

1. **People counted twice.** The same login must count once, whether it comes from `collected/contributors/`, a handle column or a GitHub link in a Source cell.
   - Owner: Task 2, `test_handle_and_source_link_resolve_to_the_same_login`.
2. **Hidden organisations.** Every organisation in the recognition report of the year must appear on the wall, including independents and one-person companies.
   - Owner: Task 4 (`test_wall_lists_every_organisation_with_a_level`) and Task 5 (`test_page_shows_every_organisation_on_the_wall`).
3. **Fractional points and gaps between levels.** An organisation with 9.5 points must show its level and the points it still needs.
   - Owner: Task 4, `test_points_to_next_level_with_fractions`.
4. **Missing public records.** A contribution without a `Source` must render as "public record pending (#46)" with a link to its row on GitHub, not as an empty link.
   - Owner: Task 5, `test_contribution_without_source_links_its_row`.
5. **Years before pull requests exist (before 2010).** History must show "no pull requests yet", not 0.
   - Owner: Task 4 (`test_history_pull_requests_none_before_2010`) and Task 5 (`test_history_without_pull_requests`).

---

## PR 1: the data

### Task 1: Record where each recognition point comes from

**Files:**
- Modify: `scripts/report/generate_community_recognition_report.py` (`calculate_community_recognition_points`, around lines 147–348)
- Test: `tests/test_recognition_method.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Contribution: text: str; points: float; file: str | None; line: int | None; source: str | None`.
    - `file` is the path relative to the repository, for example `curated/community-contributions/2025-strategic-sprints.csv`.
    - `line` is the CSV line number (`reader.line_num`).
    - `source` is the row's `Source` or `Reference` cell; for World Plone Day talks it is `https://www.youtube.com/watch?v=<YouTube ID>`; otherwise `None`.
  - `calculate_community_recognition_points(..., contributions=None)`: if a dict is passed, it is filled as `{organisation: {category: [Contribution, ...]}}`, with Unmapped excluded like the other results.
    The return value and `org_details` stay exactly as they are, because the markdown writer parses those strings.
  - For PR contributions and PLIP contributions there is no single row: `file` is the organisation file (`derived/organisation-contributors/`), or `collected/plips/plone-plips-detailed.csv`, and `line` is `None`.

- [ ] **Step 1: Write the failing tests.**
  - `test_contributions_carry_file_line_and_source(data)`: a strategic sprint row with a `Source` gives a `Contribution` whose `points == 12`, whose `file` ends with `2025-strategic-sprints.csv`, with `line == 2`, and whose `source` is the row's link.
  - `test_wpd_talk_source_is_the_video(data)`: the source is `https://www.youtube.com/watch?v=abc`.
  - `test_contributions_match_points(data)`: for every organisation and category, the sum of the contribution points equals `org_points`.
- [ ] **Step 2:** Run `python -m pytest tests/test_recognition_method.py -q`.
  Expected: the three new tests fail.
- [ ] **Step 3:** Implement.
  Record a `Contribution` next to each existing `org_details[...].append(...)`, with the same text and the points added in that step.
- [ ] **Step 4:** Run `make test`.
  Expected: everything passes, including `test_reproducible_outputs.py`.
- [ ] **Step 5:** Commit: "Record where each recognition point comes from".

### Task 2: One identity per person

**Files:**
- Create: `scripts/lib/people.py`
- Test: `tests/test_people_identity.py`

**Interfaces:**
- Produces:
  - `normalise(name: str) -> str`: lower case, without accents (`unicodedata` NFKD) and without extra whitespace.
  - `is_group(name: str, organisations: set[str]) -> bool`: true for entries ending in " team" (case-insensitive), entries equal to an organisation name, and entries that contain `;`.
  - `class PersonIndex`:
    - `__init__(self, logins_by_name: dict[str, str])`;
    - `key(self, name: str = '', handle: str = '') -> str | None`: returns the handle if given; else the login known for `normalise(name)`; else `'name:' + normalise(name)`; `None` for an empty or group name.
  - `build_person_index(community_rows, commit_authors_path=paths.COMMIT_AUTHORS, fullnames_path=paths.FULLNAMES) -> PersonIndex`, collecting name → login from:
    - rows that have both a person name and a handle (`Github`, `GitHub Handle(s)`, paired by position when they are separated by semicolons);
    - `https://github.com/<login>` links in `Source` cells of rows with one person, but only when the row has a single person and a single link;
    - `commit_authors.csv` rows with a `name` and a `github_username`;
    - `mapping-github-username-to-fullname.csv`.

    A name that would map to two different logins maps to none (fail safe).

- [ ] **Step 1: Write the failing tests:**
  - `test_normalise_ignores_case_and_accents`: `"Víctor Fernández"` becomes `"victor fernandez"`.
  - `test_groups_are_not_people`: `"PloneGov-BR team"`, `"Klein & Partner KG;BlueDynamics Alliance"`, and `"RedTurtle"` (when it is in organisations) give `True`.
  - `test_handle_and_source_link_resolve_to_the_same_login` (review focus 1): a release manager row with handle `davisagli`, and a team leader row "David Glick" whose source is `https://github.com/davisagli`, give the same key.
  - `test_ambiguous_name_maps_to_no_login`.
  - `test_unknown_name_gets_a_name_key`: the key is `"name:jane doe"`.
- [ ] **Step 2:** Run the tests. Expected: they fail with `ModuleNotFoundError`.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `make test`. Expected: everything passes.
- [ ] **Step 5:** Commit: "Resolve one identity per person across code and community work".

### Task 3: Community records and events

**Files:**
- Create: `scripts/lib/community.py`
- Test: `tests/test_community_records.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Record: kind: str; year: int; person: str; handle: str; organisation: str; label: str; file: str; line: int; source: str | None`.
    One record per person and role.
    Multi-person cells (`Trainer(s)`, `Speaker(s)`, `Organiser(s)`) are split on `;`, and `organisation` is paired by position when that column has the same number of parts.
  - `ROLE_KINDS`: a dict from file kind to (label, person column, handle column or None), for example:
    - `'board-of-directors': ('Board', 'Name', None)`
    - `'team-leaders': ('Team lead', 'Name', None)`
    - `'release-managers': ('Release manager', 'Name', 'Github')`
    - `'plone-conference-trainings': ('Trainer', 'Trainer(s)', 'GitHub Handle(s)')`
    - `'world-plone-day-talks': ('Talk', 'Speaker(s)', None)`; only rows of type `Talk` count as roles here
    - `'strategic-sprints': ('Sprint organiser', 'Organiser/Host', None)`
    - `'podcasts': ('Podcast', 'Name', None)`
    - `'plone-conference': ('Conference organiser', 'Organiser(s)', None)`; only where that column exists
  - `community_records(year, community_dir=paths.COMMUNITY) -> list[Record]`.
  - `@dataclass(frozen=True) class Event: kind: str; year: int; name: str; organisations: tuple[str, ...]; sources: tuple[str, ...]`.
  - `EVENT_KINDS = ('plone-conference', 'strategic-sprints', 'world-plone-day-event')`, documented as "add new kinds here", for example community sprints.
  - `events(year, community_dir=paths.COMMUNITY) -> list[Event]`:
    - **Plone Conference:** one event per year with a non-empty file, named `Plone Conference YYYY`, listing all its organisations.
    - **Strategic sprints:** one event per distinct `Sprint` name.
    - **World Plone Day:** one event per year with rows, named `World Plone Day YYYY`, with the organisations of all rows and the distinct references.

- [ ] **Step 1: Write the failing tests:**
  - `test_trainers_are_split_and_paired_with_handles_and_organisations`
  - `test_only_talks_count_as_wpd_roles`
  - `test_world_plone_day_is_one_event_per_year`: three organisation rows give one event with three organisations.
  - `test_strategic_sprints_count_by_name`: two rows of the same sprint give one event.
  - `test_conference_is_one_event_per_year`
  - `test_records_carry_file_line_and_source`
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `make test`. Expected: everything passes.
- [ ] **Step 5:** Commit: "Read community roles and events in one place".

### Task 4: Derive the community page data

**Files:**
- Create: `scripts/derive/community_page.py`
- Modify:
  - `scripts/lib/paths.py`: add `COMMUNITY_PAGE = Path('derived/community-page.json')`.
  - `Makefile`: target `community-page`, a help line, and `.PHONY`; `year` runs it after `community-recognition`.
  - `tests/test_reproducible_outputs.py`: add `'community-page'` to `TARGETS` and `.json` to the compared suffixes.
  - `docs/reference/data-files.md` and `docs/reference/make-targets.md`.
- Create: `docs/explanation/community-page.md`.
  It explains the page: the three numbers and their exact definitions (design §4.3), the levels coming from the script with a link to `community-recognition.md`, the possible double count (#117), and the event counting (#118).
  Link it in `docs/explanation/index.md`.
- Test: `tests/test_community_page_data.py`

**Interfaces:**
- Consumes: Task 1 (`Contribution`, `contributions=`), Task 2 (`build_person_index`, `PersonIndex.key`, `is_group`) and Task 3 (`community_records`, `events`, `EVENT_KINDS`).
- Produces `build_page_data(year: int) -> dict`.
  `main()` writes it with `json.dump(..., indent=1, sort_keys=True, ensure_ascii=False)` and a final newline.
  `--year` defaults to `years.RECOGNITION_YEAR`.
  The schema, at the top level:

```text
year, years (the five years up to year, oldest first)
headline: {year: {people, organisations, events}, five_years: {people, organisations, events}, since_2003: {people}}
levels: [{name, min, max (null for the last)}]
wall: [{level, organisations: [{name, slug, points}]}]       # every entry of the recognition report, by level, then name
organisations: {slug: {name, level, points, next_level, points_to_next,
                       categories: {category: {points, contributions: [{text, points, file, line, source}]}},
                       history: {YYYY: {commits, pull_requests, roles, events}}}}
people: {YYYY: [{id, commits, pull_requests, roles: [label]}]}   # id = login or "name:<normalised>", sorted by id
history: {YYYY: {people_active, commits, pull_requests (null before 2010),
                 board: [{name, organisation, source}], team_leads: [{name, team, organisation, source}],
                 events: [{kind, name, organisations, sources}]}}
```

- Definitions, from design §4.3:
  - **People active** in a set of years is the number of distinct keys over code work and community work.
    - Code work is the `username` of each row in `collected/contributors/YYYY-plone-contributors.csv` with commits > 0 or merged PRs > 0.
    - Community work is the `PersonIndex.key` of each `Record`; group entries are left out.
  - **Organisations active** in a set of years is the number of distinct organisations over:
    - the `organisation` column of `derived/organisation-contributors/` (rows with commits or PRs);
    - the organisations of `Record`s and `Event`s.

    Leave out `Unmapped`, names ending in `(independent)`, and `Plone Foundation (community volunteer)`.
  - **Events** is the number of `events()` in the years.
- `slug` is the lower-case ASCII name with runs of other characters replaced by `-`.
- `points_to_next` is `next_level.min - points`, or `null` at the highest level.

- [ ] **Step 1: Write the failing tests**, on a small fixture repository built with `tmp_repo`:
  - `test_people_active_counts_code_and_community_once` (review focus 1)
  - `test_organisations_active_leave_out_unmapped_and_independents`
  - `test_events_count_one_world_plone_day_per_year`
  - `test_wall_lists_every_organisation_with_a_level`, including an independent (review focus 2)
  - `test_points_to_next_level_with_fractions`: 9.5 points with Silver from 10 gives `points_to_next == 0.5` (review focus 3)
  - `test_history_pull_requests_none_before_2010` (review focus 5)
  - `test_people_are_sorted_by_id_and_carry_no_rank`
  - `test_data_is_deterministic`: two runs give identical bytes.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement, then run `make community-page` to write `derived/community-page.json`.
- [ ] **Step 4:** Run `make test`, including `test_reproducible_outputs.py` with the new target, and `make docs`.
  Expected: everything passes.
- [ ] **Step 5:** Copy the spec and this plan unchanged to `archive/specs-and-plans/2026-10-19-community-page-{design,plan}.md`.
  Commit: "Derive the data of the community page".
- [ ] **Step 6:** Ask a fresh reviewer to check the branch.
  Then push and open PR 1, "Derive the data of the community page", with an "Assisted-by" footer.

## PR 2: the site

### Task 5: Render the page

**Files:**
- Create:
  - `scripts/report/community_page.py`
  - `scripts/report/site/templates/` with `base.html` and `index.html`, plus partials as the builder likes
  - `scripts/report/site/static/` with `site.css` and `site.js`
- Modify:
  - `requirements.txt`: add `jinja2>=3.1`.
  - `Makefile`: targets `site` and `site-serve`, help lines, `.PHONY`, and `clean` removes `_site`.
  - `.gitignore`: add `_site/`.
  - `tests/test_layout.py`: `test_scripts_run_as_modules` covers the new script automatically; check that it passes.
- Test: `tests/test_community_page_render.py`

**Interfaces:**
- Consumes the Task 4 JSON (`paths.COMMUNITY_PAGE`).
- Produces:
  - `render(data: dict, out_dir: Path, docs_url: str = 'docs/') -> None`.
    It writes `out_dir/index.html` and copies `static/` to `out_dir/static/`.
    It embeds the people data as `<script type="application/json" id="people-data">`.
  - `main()` takes `--out` (default `_site`).
  - `make site`:
    1. `python -m scripts.report.community_page --out _site`
    2. `python -m sphinx -W --keep-going -n -b html docs _site/docs`
  - `make site-serve`: `python -m http.server --directory _site 8000`, with a printed URL.
- Page content follows design §4.2 and §4.4:
  - **Header:** the Plone look and a "Documentation" link to `docs/`.
  - **First screen:** two periods with three numbers each, a small "since 2003" line, and a note that people may be counted twice (link to the explanation).
  - **Organisation wall:** grouped by level, every entry visible, each linking to `#org-<slug>`, and a note that the levels can differ from plone.org (link).
  - **Organisations section:** one `<section id="org-<slug>">` per organisation, containing:
    - the level, the points and the gap to the next level;
    - `<details>` per category, listing the contributions;
    - each contribution with a source link, or "public record pending (#46)" and a link to `https://github.com/plone/plone-contributor-statistics/blob/main/<file>#L<line>`;
    - a small inline-SVG graph of the yearly counts per area.
  - **People section:** a search box (JavaScript), and the categories per year with "Nth of M" for the found person.
    There is no names list, and a `<noscript>` note.
  - **History section:** one block per year, newest first, collapsible, with the Board, team leads, people active, commits, pull requests or "no pull requests yet", and the events with source links.
  - **Footer:** links to the docs, the explanation page, the data file on GitHub and the repository.
- Tabs: a CSS and JavaScript enhancement over the sections. Without JavaScript, all sections show one after another.
- Look: Plone blue, a system font stack, a responsive layout; no external assets.

- [ ] **Step 1: Write the failing tests**, rendering a small fixture dict into `tmp_path`:
  - `test_page_shows_every_organisation_on_the_wall` (review focus 2)
  - `test_contribution_without_source_links_its_row` (review focus 4)
  - `test_history_without_pull_requests` (review focus 5)
  - `test_no_external_assets`: parse `index.html` and assert that no `src` or `<link href>` starts with `http`.
  - `test_people_are_not_listed_in_the_html`: the fixture's person ids appear only inside the `people-data` script element.
  - `test_links_to_the_docs`
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement.
  Check the real page with `make site site-serve`, in a browser at desktop and phone width.
- [ ] **Step 4:** Run `make test` and `make site`. Expected: everything passes, and the build succeeds without warnings.
- [ ] **Step 5:** Commit: "Render the community page".

### Task 6: Publish the page at the root, and the docs under /docs/

**Files:**
- Modify:
  - `.github/workflows/docs.yml`: install `requirements.txt` and `requirements-docs.txt`, run `make site`, and upload `_site`.
  - `docs/conf.py`: `html_baseurl = "https://plone.github.io/plone-contributor-statistics/docs/"`.
  - Every absolute docs URL in `README.md`, `AGENTS.md`, `docs/contributing/documentation.md` and the folder READMEs (`curated/`, `collected/`, `derived/`, `reports/`, `scripts/`): insert `docs/` after `plone-contributor-statistics/`.
    Find them with `git grep -n "plone.github.io/plone-contributor-statistics/"`.
  - `README.md`: the site structure (the page at the root, the docs at `/docs/`) and the `make site` and `make site-serve` targets.
  - `AGENTS.md`: the site structure in the Commands and Layout sections.
  - `docs/index.md`: a link to the community page (`../`).
  - `docs/reference/make-targets.md`: `site`, `site-serve`, and the changed `clean`.
- Test: extend `tests/test_docs_and_archive.py`:
  - `test_docs_workflow_publishes_the_site`: the build job runs `make site` and uploads `_site`.
  - `test_absolute_docs_urls_point_below_docs`: no `plone.github.io/plone-contributor-statistics/<x>` with `<x>` other than `docs/` in tracked text files outside `archive/`.

- [ ] **Step 1:** Write both tests. Run them. Expected: they fail.
- [ ] **Step 2:** Make the changes.
- [ ] **Step 3:** Run `make test docs site`. Expected: everything passes.
- [ ] **Step 4:** Commit: "Publish the community page at the root and the docs under /docs/".
- [ ] **Step 5:** Ask a fresh reviewer to check the branch, then push and open PR 2.
  The PR says that the old docs URLs move to `/docs/`, without redirects, as decided.
