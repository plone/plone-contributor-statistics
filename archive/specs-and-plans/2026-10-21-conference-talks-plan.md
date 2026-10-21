# Conference Talks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new curated kind `conference-talks` (keynotes, talks and panels of global and regional Plone conferences, with their recordings), read by the model, shown in the person box of the community page, documented, with Plone Conference 2021 as the first filled year.

**Architecture:** The kind follows `world-plone-day-talks` end to end: a Table Schema in `curated/schemas/`, one CSV per year in `curated/community-contributions/`, a role kind in `scripts/lib/model/community.py` (label "Speaker"), a `talks` list per person in `derived/community-page.json` from `scripts/derive/community_page.py`, and a "Talks" row in the person card drawn by `scripts/report/site/static/site.js`. No recognition points: `scripts/report/generate_community_recognition_report.py` lists its kinds explicitly in `COMMUNITY_RULES` and is not touched.

**Tech Stack:** Python 3.12, frictionless Table Schema, pytest (offline), Jinja2 templates, plain JavaScript; run everything with the project venv (`/home/jensens/.venvs/plone-contributor-statistics/bin/python`) from the repository root; `make check` runs the data checks (the lint step fails with flake8 installed, so run `python -m scripts.tools.check` and `python -m pytest tests` directly).

**Spec:** `archive/specs-and-plans/2026-10-21-conference-talks-design.md`

## Global Constraints

- Every row of curated data has a public record in `source` (a web address); a speaker not in the people register is added with `python -m scripts.tools.person --add "<name>" [--github <login>] --source <url>`, never by hand.
- Ids are opaque; logins keep their GitHub case; set cells use semicolons; UTF-8, Unix line endings; the schema is the format.
- A pull request that changes a data source, a format or the page updates `docs/` in the same pull request; no numbers or rankings in the docs.
- Code changes get offline pytest tests; the data change gets format checks only.
- No recognition points and no change to the wall, the levels or the points file.
- Lightning-talk sessions are not rows; World Plone Day talks stay in `YYYY-world-plone-day-talks.csv`.
- Work in a worktree on its own branch from `origin/main`; commit messages and the pull request end with `Assisted-by: <model name>` lines (implementing model first, then Claude Fable 5.1), no e-mail address, no `Co-Authored-By`.
- The design and this plan are committed unchanged under `archive/specs-and-plans/` before the pull request opens.

## Review Focus

1. A row with neither speakers nor organisations (a talk whose speaker has no public identity, named in `notes` only) must load, count for nobody and never raise: Task 2 tests it.
2. A recording cell that is empty, and a World Plone Day source that holds two links: the video of a talk is the first `http(s)://` address of the cell, `None` when there is none: Task 2 tests it.
3. A person who speaks at two conferences in one year: the talks come out sorted by event, then title, and the card shows the event in brackets only then: Tasks 3 and 4 test it.
4. The page script meets a person entry without a `talks` key (older derived data, the render test fixture): it must draw the card without the row, not throw: Task 4 tests the embedded data and guards the script.
5. A `type` outside Keynote, Talk, Panel, and a `scope` outside global, regional, must fail `make check`: Task 1 pins the enums in the schema test.

---

### Task 1: The schema and its registration

**Files:**
- Create: `curated/schemas/conference-talks.json`
- Modify: `tests/test_schemas.py:6-10` (KINDS), `tests/test_schemas.py:24-32` (set columns)
- Modify: `scripts/tools/schema_docs.py:33-43` (GROUPS, community group), `scripts/tools/schema_docs.py:66-72` (ONE_ROW_IS)
- Modify: `docs/reference/data-sources.md:25-34` (the table under "Curated by hand")
- Modify: `docs/explanation/curated-community-data.md:43-78` (the definitions list)
- Regenerate: `docs/reference/curated-files.md` with `python -m scripts.tools.schema_docs`

**Interfaces:**
- Produces: the kind name `conference-talks`; columns `event, scope, type, title, speakers, organisations, video, source, notes`; enums `scope ∈ {global, regional}`, `type ∈ {Keynote, Talk, Panel}`; `speakers` has `"x-set": "people"`, `organisations` has `"x-set": "organisations"`; `video` is an optional string with the constraint pattern `^https?://.*$`; `source` is required with pattern `.*https?://.*`; `event`, `scope`, `type`, `title` are required.

- [ ] **Step 1: Write the failing tests** in `tests/test_schemas.py`: add `'conference-talks'` to `KINDS`, add `'conference-talks': {'speakers': 'people', 'organisations': 'organisations'}` to `expected` in `test_set_columns_name_their_register`, and add:

```python
def test_conference_talk_enums():
    fields = {f['name']: f for f in json.loads((SCHEMAS / 'conference-talks.json').read_text())['fields']}
    assert fields['scope']['constraints']['enum'] == ['global', 'regional']
    assert fields['type']['constraints']['enum'] == ['Keynote', 'Talk', 'Panel']
    assert fields['video']['constraints'] == {'pattern': '^https?://.*$'}
    assert [f for f in fields if fields[f].get('constraints', {}).get('required')] == ['event', 'scope', 'type', 'title', 'source']
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_schemas.py -q`
Expected: FAIL, `test_every_kind_has_a_valid_schema` (the schema file is missing) and `test_conference_talk_enums`.

- [ ] **Step 3: Write `curated/schemas/conference-talks.json`** in the shape of `world-plone-day-talks.json`: the fields in the column order of the Interfaces block, each with a one-sentence `description` (the event "as the conference named itself"; the scope "`global` for the annual Plone Conference, `regional` for every other conference"; the type "Keynote, Talk or Panel, as the programme calls it; lightning-talk sessions are not recorded"; the video "the web address of the recording, when one exists; one link, a second part goes to the notes"), no `primaryKey`.

- [ ] **Step 4: Run the schema tests**

Run: `python -m pytest tests/test_schemas.py -q`
Expected: PASS

- [ ] **Step 5: Register the kind in the docs tooling and the docs.** In `scripts/tools/schema_docs.py` add `('conference-talks', 'Conference talks')` to the community group after `('world-plone-day-talks', 'World Plone Day talks')`, and `'conference-talks': 'one keynote, talk or panel at a Plone conference, global or regional.'` to `ONE_ROW_IS`. Run `python -m scripts.tools.schema_docs` to regenerate `docs/reference/curated-files.md`. In `docs/reference/data-sources.md` add the row `| Conference talks | 2021 | \`curated/community-contributions/YYYY-conference-talks.csv\` | 2021 |` after the trainings row. In `docs/explanation/curated-community-data.md` add one bullet to the definitions list, after the World Plone Day talk bullet, saying: a conference talk is a keynote, talk or panel in the programme of a Plone conference, the annual Plone Conference (scope `global`) or a regional conference such as the Plone Tagung, the symposia or PloneConf Brasil (scope `regional`); World Plone Day is not a conference and sprints and meetups are not; tutorials are trainings; lightning-talk sessions are not recorded for now; only people speak, a team talk names the team in `organisations`; what the speaker page, the bio or the speaker in the recording says about their organisation is an affiliation row for that year, with the page or the recording and its timestamp as the source; talks are shown, not counted, and earn no recognition points until the Marketing Team or the Board decides otherwise.

- [ ] **Step 6: Run the docs tests and the schema docs test**

Run: `python -m pytest tests/test_docs_and_archive.py tests/test_schemas.py -q`
Expected: PASS (the test at `tests/test_docs_and_archive.py:215` sees the kind in GROUPS and in the reference)

- [ ] **Step 7: Commit**

```bash
git add curated/schemas/conference-talks.json tests/test_schemas.py scripts/tools/schema_docs.py docs/reference/curated-files.md docs/reference/data-sources.md docs/explanation/curated-community-data.md
git commit -m "Add the conference-talks kind: schema, reference and definitions"
```

### Task 2: The model reads talks

**Files:**
- Modify: `scripts/lib/model/community.py:16-38` (ROLE_KINDS, KEY_COLUMNS), add `Talk` and `talks()` after `roles()`
- Modify: `scripts/lib/model/__init__.py` (export `Talk`, `talks`)
- Test: `tests/test_model_community.py`

**Interfaces:**
- Produces: `ROLE_KINDS['conference-talks'] == ('Speaker', 'speakers', 'title')`, `ROLE_KINDS['world-plone-day-talks'] == ('Speaker', 'speakers', 'title')`, `KEY_COLUMNS['conference-talks'] == 'title'`.
- Produces: `@dataclass(frozen=True) class Talk: kind: str; year: int; person: str; title: str; event: str; video: str | None; file: str; line: int; source: str` and `def talks(year, community_dir=paths.COMMUNITY) -> list[Talk]`: one `Talk` per speaker and row of `conference-talks` (every type) and of `world-plone-day-talks` whose `type` is in `TALK_TYPES`; for a conference talk `event` is the `event` cell and `video` the `video` cell or `None` when empty; for a World Plone Day talk `event` is `f'World Plone Day {year}'` and `video` the first `https?://\S+` match in `source`, `None` when there is none; order: conference talks in file order, then World Plone Day talks in file order.

- [ ] **Step 1: Write the failing tests** in `tests/test_model_community.py` (the `community` fixture writes files into `paths.COMMUNITY`; `SRC` is the sample source):

```python
TALKS = 'event,scope,type,title,speakers,organisations,video,source,notes\n'

def test_conference_talks_are_speaker_roles_of_every_type(community):
    community('2021-conference-talks.csv', TALKS +
              f'Plone Conference 2021,global,Keynote,Opening keynote,pbauer,,https://v/1,{SRC},\n'
              f'Plone Conference 2021,global,Panel,The panel,pbauer;tschorr,,,{SRC},\n'
              f'Plone Tagung 2021,regional,Talk,Team talk,,starzel,,{SRC},\n'
              f'Plone Tagung 2021,regional,Talk,Nobody known,,,,{SRC},speaker without a public identity\n')
    assert [(r.person, r.label, r.detail, r.line) for r in roles(2021)] == [
        ('pbauer', 'Speaker', 'Opening keynote', 2), ('pbauer', 'Speaker', 'The panel', 3),
        ('tschorr', 'Speaker', 'The panel', 3)]
    found = items(2021, 'conference-talks')
    assert [i.key for i in found] == ['Opening keynote', 'The panel', 'Team talk', 'Nobody known']
    assert found[2].people == () and found[2].organisations == ('starzel',)
    assert found[3].people == () and found[3].organisations == ()

def test_world_plone_day_speakers_are_speakers_too(community):
    community('2023-world-plone-day-talks.csv',
              f'title,speakers,organisations,type,location,source,notes\nA talk,pbauer,,Talk,,{SRC},\n')
    assert [(r.person, r.label) for r in roles(2023)] == [('pbauer', 'Speaker')]

def test_talks_per_person_with_event_and_video(community):
    community('2021-conference-talks.csv', TALKS +
              f'Plone Tagung 2021,regional,Talk,Regional talk,pbauer,,,{SRC},\n'
              f'Plone Conference 2021,global,Talk,Global talk,pbauer;tschorr,,https://v/2,{SRC},\n')
    community('2021-world-plone-day-talks.csv',
              'title,speakers,organisations,type,location,source,notes\n'
              'WPD talk,pbauer,,Talk,,https://www.youtube.com/watch?v=abc; https://example.org/event,\n'
              f'A teaser,pbauer,,Teaser,,{SRC},\n')
    found = talks(2021)
    assert [(t.person, t.event, t.title, t.video) for t in found] == [
        ('pbauer', 'Plone Tagung 2021', 'Regional talk', None),
        ('pbauer', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('tschorr', 'Plone Conference 2021', 'Global talk', 'https://v/2'),
        ('pbauer', 'World Plone Day 2021', 'WPD talk', 'https://www.youtube.com/watch?v=abc')]
    assert found[0].kind == 'conference-talks' and found[3].kind == 'world-plone-day-talks'
    assert found[1].line == 3 and found[1].source == SRC

def test_talks_of_a_year_without_files(community):
    assert talks(2019) == []
```

Change the expectation of `test_roles_skip_non_talks` from `('pbauer', 'Talk', 'A talk')` to `('pbauer', 'Speaker', 'A talk')`, and import `talks` next to `roles`.

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_model_community.py -q`
Expected: FAIL (`talks` cannot be imported; the role tests see no `conference-talks` kind and the label `Talk`)

- [ ] **Step 3: Implement.** In `scripts/lib/model/community.py` add `'conference-talks': ('Speaker', 'speakers', 'title')` to `ROLE_KINDS`, change the World Plone Day label to `'Speaker'`, add `'conference-talks': 'title'` to `KEY_COLUMNS`, add the `Talk` dataclass next to `Role`, and `talks(year, community_dir=paths.COMMUNITY)` after `roles()`, built from `items()` for both kinds with `re.search(r'https?://\S+', source)` for the World Plone Day video (strip a trailing `;` or `,` from the match). Export `Talk` and `talks` in `scripts/lib/model/__init__.py`.

- [ ] **Step 4: Run the model tests**

Run: `python -m pytest tests/test_model_community.py tests/test_model_is_the_only_reader.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole suite**, because the label change reaches the recognition report and the page: `python -m pytest tests -q`. Expected: PASS, or failures only where a test spells out the old label `Talk`; fix those expectations to `Speaker`.

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/model/community.py scripts/lib/model/__init__.py tests/test_model_community.py
git commit -m "Read conference talks in the model and call every speaker a Speaker"
```

### Task 3: The page data lists talks per person

**Files:**
- Modify: `scripts/derive/community_page.py:53-72` (`people_of_year`, `talk_organisations`), `:187-235` (`build_page_data`)
- Test: `tests/test_community_page_data.py`

**Interfaces:**
- Consumes: `talks(year)` and `Talk` from Task 2.
- Produces: `people_of_year(year, registry, year_roles, year_talks)`; every person entry of `data['people'][str(year)]` has `'talks': [{'title': str, 'event': str, 'video': str | None}, ...]`, sorted by `(event, title)`, `[]` for people without talks; `talk_organisations(year, registry)` also counts the `organisations` of `conference-talks` rows (every type), so a team talk makes its organisation active and gives it a role count in the history, as for World Plone Day.

- [ ] **Step 1: Write the failing tests** in `tests/test_community_page_data.py` (fixture `repo`; `write(path, text)`; timo is kitconcept, mauro RedTurtle; import `events, load_registry, roles` from `scripts.lib.model` for the team-talk test):

```python
CONF_TALKS = 'event,scope,type,title,speakers,organisations,video,source,notes\n'

def test_a_speaker_is_active_and_lists_the_talks_sorted(repo):
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Tagung 2025,regional,Talk,Zope news,timo,,,https://s/1,\n'
          'Plone Conference 2025,global,Keynote,A keynote,timo;mauro,,https://v/1,https://s/2,\n')
    write(paths.COMMUNITY / '2025-world-plone-day-talks.csv', TALKS + 'WPD talk,timo,,Talk,Online,https://v/3,\n')
    data = community_page.build_page_data(2025)
    timo = next(p for p in data['people']['2025'] if p['id'] == 'timo')
    assert timo['roles'] == ['Speaker']
    assert timo['talks'] == [{'title': 'A keynote', 'event': 'Plone Conference 2025', 'video': 'https://v/1'},
                             {'title': 'Zope news', 'event': 'Plone Tagung 2025', 'video': None},
                             {'title': 'WPD talk', 'event': 'World Plone Day 2025', 'video': 'https://v/3'}]
    mauro = next(p for p in data['people']['2025'] if p['id'] == 'mauro')
    assert mauro['talks'] == [{'title': 'A keynote', 'event': 'Plone Conference 2025', 'video': 'https://v/1'}]
    assert data['history']['2025']['people_active'] == 2
    assert data['headline']['year']['organisations'] == 2  # RedTurtle (conference, mauro) and kitconcept (timo)

def test_people_without_talks_have_an_empty_list(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\n')
    [entry] = community_page.build_page_data(2025)['people']['2025']
    assert entry['talks'] == []

def test_a_team_conference_talk_counts_the_organisation(repo):
    # No points, so kitconcept has no entry under data['organisations']; the history function shows the role count
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Conference 2025,global,Talk,Team talk,,kitconcept,,https://s/1,\n')
    data = community_page.build_page_data(2025)
    assert data['headline']['year']['organisations'] == 2
    assert data['history']['2025']['people_active'] == 0
    registry = load_registry()
    history = community_page.organisation_history(2025, registry, roles(2025), events(2025))
    assert history['kitconcept GmbH']['roles'] == 1

def test_conference_talks_earn_no_points(repo):
    write(paths.COMMUNITY / '2025-conference-talks.csv', CONF_TALKS +
          'Plone Conference 2025,global,Keynote,A keynote,timo,,https://v/1,https://s/2,\n')
    data = community_page.build_page_data(2025)
    assert 'kitconcept-gmbh' not in data['organisations']
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_community_page_data.py -q`
Expected: FAIL (`talks` key missing; `people_of_year` has no talks parameter)

- [ ] **Step 3: Implement.** Import `talks` from `scripts.lib.model`. In `build_page_data` compute `year_talks = {y: talks(y) for y in all_years}` and pass `year_talks[y]` to `people_of_year`. In `people_of_year` add `'talks': []` to the default entry, append `{'title', 'event', 'video'}` per `Talk` to `found[talk.person]['talks']`, and sort each list by `(event, title)`. In `talk_organisations` iterate `items(year, 'conference-talks')` as well, without a type filter.

- [ ] **Step 4: Run the page data tests**

Run: `python -m pytest tests/test_community_page_data.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/derive/community_page.py tests/test_community_page_data.py
git commit -m "List a person's talks of the year in the community page data"
```

### Task 4: The person card shows the talks

**Files:**
- Modify: `scripts/report/site/static/site.js:173-188` (the facts list of the card)
- Modify: `docs/explanation/community-page.md:28` (community work list), `:72` (the card)
- Test: `tests/test_community_page_render.py`

**Interfaces:**
- Consumes: the `talks` list per person entry from Task 3.
- Produces: in the card, after the "Community roles" row, a row "Talks" whose `dd` holds one entry per talk, separated by `' · '`: an `<a>` with `href` = `video` and the title as text when `video` is set, the title as plain text otherwise, followed by ` (event)` only when the person's talks of that year name more than one distinct event; the row is left out when `match.talks` is missing or empty.

- [ ] **Step 1: Write the failing test** in `tests/test_community_page_render.py`: add to the `'people'` fixture entry of `secret-person` the key `'talks': [{'title': 'Secret talk', 'event': 'Plone Conference 2025', 'video': 'https://v/1'}]`, and add:

```python
def test_people_data_carries_the_talks(page):
    data = page.split('<script type="application/json" id="people-data">')[1].split('</script>')[0]
    assert json.loads(data)['years']['2025'][0]['talks'] == [
        {'title': 'Secret talk', 'event': 'Plone Conference 2025', 'video': 'https://v/1'}]
    assert 'Secret talk' not in page.split('<script type="application/json" id="people-data">')[0]

def test_page_script_draws_the_talks_row():
    script = (REPO / 'scripts/report/site/static/site.js').read_text(encoding='utf-8')
    assert "'Talks'" in script and 'match.talks || []' in script
```

(`REPO` is the repository root as the other render tests resolve it; add it if the module has none.)

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_community_page_render.py -q`
Expected: FAIL on `test_page_script_draws_the_talks_row` (the data test may already pass, since the page embeds the entry as given)

- [ ] **Step 3: Implement in `site.js`.** In `render()`, after the facts rows are appended, build the "Talks" row from `var talks = match.talks || [];` when `talks.length`: a `dt` with text `'Talks'` and a `dd` with the entries of the Interfaces block (count distinct `event` values to decide on the brackets). Keep the existing rows untouched.

- [ ] **Step 4: Run the render tests, then look at the page once.** `python -m pytest tests/test_community_page_render.py -q` → PASS. Then `make site` and open `_site/index.html` (or `make site-serve`), search for `Eric` in 2021 only after Task 5, or temporarily for a trainer of any year to see the card still renders; no browser test is added.

- [ ] **Step 5: Update the docs.** In `docs/explanation/community-page.md` add "conference talk" to the community-work list at line 28 (keep "World Plone Day talk"), and in the people-card paragraph at line 72 say that the card lists the person's talks of the year, each title linked to its recording where one exists, World Plone Day talks included, and that talks are shown, not counted.

- [ ] **Step 6: Run the docs tests and commit**

Run: `python -m pytest tests/test_docs_and_archive.py tests/test_community_page_render.py -q` → PASS

```bash
git add scripts/report/site/static/site.js docs/explanation/community-page.md tests/test_community_page_render.py
git commit -m "Show a person's talks in the card of the community page"
```

### Task 5: Plone Conference 2021, the first filled year

**Files:**
- Create: `curated/community-contributions/2021-conference-talks.csv`
- Modify: `curated/mappings/people.csv` only through the person tool, for speakers missing from the register
- Regenerate: `curated/datapackage.json` (`python -m scripts.tools.datapackage`), `derived/` and `reports/` (the targets `make community-page` and the others that `tests/test_reproducible_outputs.py` runs; the sequence is in `tests/test_reproducible_outputs.py`)

**Interfaces:**
- Consumes: the schema of Task 1 and the model of Task 2.
- Produces: one row per keynote, talk and panel of Plone Conference 2021 (online, 23–29 October 2021), `scope` `global`, `event` `Plone Conference 2021`; no lightning talks, no trainings, no open spaces, no sprint sessions.

- [ ] **Step 1: Collect the programme.** The site is gone (it redirects to YouTube), but the Wayback Machine holds it: the talk list as JSON at `http://web.archive.org/web/20220805092311id_/https://2021.ploneconf.org/++api++/schedule/talks`, the schedule at `http://web.archive.org/web/20211015140825id_/https://2021.ploneconf.org/schedule/<slug>` per talk, and the speaker pages at `http://web.archive.org/web/20211017162610id_/https://2021.ploneconf.org/speakers/<slug>` (26 speakers linked from the speakers page). Fetch with `curl -sL --compressed`; the Wayback Machine returns empty bodies at times, retry after a pause. Write the rows from the schedule: `type` `Keynote` where the programme says keynote, `Panel` where several named people discuss, `Talk` otherwise; `title` as printed; `speakers` as register ids; `source` the archived schedule page of the talk.
- [ ] **Step 2: Find the recordings.** The talks are in the Plone YouTube channel's playlist `PLGN9BI-OAQkQDLQinBwdEXpebDTQCwdGi` ("Plone Conference 2021"); map each talk to its video by title, put `https://www.youtube.com/watch?v=<id>` in `video`; a talk without a recording keeps the cell empty.
- [ ] **Step 3: Resolve the speakers.** `python -m scripts.tools.person <name or login>` for each; add missing speakers with `python -m scripts.tools.person --add "<name>" --github <login> --source <archived speaker page>`; a speaker with no GitHub login and no other public identity stays out of `speakers` and is named in `notes`.
- [ ] **Step 4: Note the affiliations for the data round, do not apply them here.** For every speaker page that names an employer, write the person id, the organisation and the page into the pull request description under "affiliation evidence found"; the affiliation rows are the next pull request's job (the format PR stays about the format).
- [ ] **Step 5: Sort the file** by `event`, then `title`, save as UTF-8 with Unix line endings, and run `python -m scripts.tools.datapackage` then `python -m scripts.tools.check`. Expected: no errors; fix ids and enums until clean.
- [ ] **Step 6: Regenerate the outputs** with the make targets that `tests/test_reproducible_outputs.py` runs (organisation stats, PLIP organisations, the three summaries, yearly activity, the report, community recognition, community page, with `SUMMARY_END` and `RECOGNITION_YEAR` as that test derives them), then `git diff --stat`. Expected: `derived/community-page.json` changes (the 2021 people entries gain talks and the Speaker role, the 2021 people active and organisations active move, the history role counts of the speakers' organisations move); `reports/community-recognition.md` and the recognition CSVs do not change.
- [ ] **Step 7: Run everything**

Run: `python -m pytest tests -q` → PASS (868 before this work, plus the new tests); `python -m scripts.tools.check` → clean.

- [ ] **Step 8: Commit**

```bash
git add curated/community-contributions/2021-conference-talks.csv curated/mappings/people.csv curated/datapackage.json derived reports
git commit -m "Record the keynotes, talks and panels of Plone Conference 2021"
```

### Task 6: Archive the design and the plan, open the pull request

**Files:**
- Add: `archive/specs-and-plans/2026-10-21-conference-talks-design.md`, `archive/specs-and-plans/2026-10-21-conference-talks-plan.md` (already in the worktree, untracked)

- [ ] **Step 1: Commit the two documents unchanged**

```bash
git add archive/specs-and-plans/2026-10-21-conference-talks-design.md archive/specs-and-plans/2026-10-21-conference-talks-plan.md
git commit -m "Archive the design and the plan of the conference talks"
```

- [ ] **Step 2: Check the documentation builds**: `make docs` with the venv on `PATH` (warnings are errors). Expected: a clean build.
- [ ] **Step 3: Push the branch and open the pull request** with a description that says what the kind is, that talks are shown and not counted, that Plone Conference 2021 is the worked example, lists the affiliation evidence found on the speaker pages for the next round, and ends with the `Assisted-by` lines. Refs #139 for the affiliation side.
