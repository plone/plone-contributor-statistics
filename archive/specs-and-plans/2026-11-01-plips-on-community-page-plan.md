# PLIPs on the community page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the PLIPs on the community page: on a person's card, behind an organisation's "PLIP Contributions" points, and per year in the History tab, instead of the Markdown report of PR #189.

**Architecture:** `scripts/derive/community_page.py` adds the PLIPs, already grouped for display, to `derived/community-page.json`; the recognition report exposes the PLIP groups its points come from, so the organisation's list and count share one computation. The Jinja template renders the organisation and History lists, `site.js` the person card row; neither counts or sorts.

**Tech Stack:** Python 3, pytest, Jinja2, plain JavaScript, Sphinx/MyST docs.

**Spec:** `2026-11-01-plips-on-community-page-design.md` (next to this plan; archived together into `archive/specs-and-plans/`).

## Global Constraints

- Work in the worktree `/home/jensens/ws/cdev/pcs-plips`, branch `plips-on-community-page` (from `origin/main`). Python: `~/.venvs/plone-contributor-statistics/bin/python`; run pytest as `~/.venvs/plone-contributor-statistics/bin/python -m pytest`.
- Which PLIPs: rows of `collected/plips/plone-plips-detailed.csv` with `state == 'closed'`, in the year of `closed_at`, for `registry.organisation_for_username(author, year)` (#95). Open PLIPs appear nowhere.
- Only the page's years (`FIRST_YEAR` up to `data.year`); later PLIPs are not shown.
- No author name or login in any visible PLIP list (organisation entry, History). The person card is the only place that ties PLIPs to a person.
- A PLIP entry everywhere: `{'repository': 'volto', 'number': 6326, 'title': 'Vitest', 'url': '<html_url>'}`; `repository` is the repository name without `plone/`.
- Person card label `PLIPs (n)`, never "PLIPs closed"; note sentence `PLIPs: proposed by them and closed in <year>.`
- Grey reference in organisation and History lists: `<repository>#<number>`, e.g. `volto#6396`; on the person card only `#<number>`, since the group names the project.
- Unmapped is shown in History as the last group, labelled `no organisation recorded`; every other organisation under its register name, independents and the Plone Foundation included (naming of independents: #191, not here).
- Deterministic output: every list sorted as specified, no timestamps.
- Commit messages end with `Assisted-by: <implementing model>` (then `Assisted-by: Claude Opus 5.5` when a subagent wrote it); never `Co-Authored-By`, never an email address.

## Review Focus

- A PLIP author without a register entry (unknown login): keyed by the login in lower case on the card, `no organisation recorded` in History; must not crash. Test in Task 1 and Task 2.
- A PLIP whose author's login differs in case from the register (`Rudd-O`): must land on the same person as their commits (`code_key`). Test in Task 1.
- An organisation with exactly one PLIP in the window: no points, so no category; its `plips` must be empty and nothing rendered. Test in Task 2.
- A PLIP title with HTML characters (`<`, `&`, quotes): escaped in the template and set as text in the script. Test in Task 3 (template); Task 4 uses `textContent` only.
- A closed PLIP with an empty `closed_at`: it must fall in the year `plip_organisation_stats.plip_year` gives (the year created), as the points do; `closed_plips` uses `plip_year`. Test in Task 1.

---

### Task 1: PLIPs in the people data, and PLIPs make people and organisations active

**Files:**
- Modify: `scripts/derive/community_page.py`
- Test: `tests/test_community_page_data.py`

**Interfaces:**
- Produces in `scripts/derive/community_page.py`:
  - `plip_entry(plip: dict) -> dict` — the entry of the Global Constraints.
  - `closed_plips(up_to: int) -> dict[int, list[dict]]` — raw closed PLIP rows of `paths.PLIPS_DETAILED` by `plip_organisation_stats.plip_year`, years `FIRST_YEAR..up_to`; reads with `read_rows`.
  - `plips_by_repository(rows: list[dict]) -> list[dict]` — `[{'repository': 'volto', 'plips': [entry, ...]}]`, groups by size descending, ties by repository name (casefold); entries by number descending.
  - `people_of_year(year, registry, year_roles, year_talks, year_plips)` — each person gets `'plips': plips_by_repository(...)`, `[]` when none; a PLIP author is keyed by `code_key(registry, author)`.
  - `organisations_of_year(year, registry, year_roles, year_events, year_plips)` — adds `registry.organisation_for_username(author, year)` for each PLIP, still filtered by `is_counted_organisation`.

- [ ] **Step 1: Write the failing tests** in `tests/test_community_page_data.py`, using the `repo` fixture and the module's `write` and `PLIPS` header:

```python
def plip(number, author, closed, repository='plone/volto', title='A PLIP', state='closed'):
    return (f'{number},{title},{author},{state},{closed[:4]}-01-01,{closed},'
            f'{closed if state == "closed" else ""},{repository},https://github.com/{repository}/issues/{number}\n')


def test_a_person_lists_the_plips_closed_in_the_year_grouped_by_repository(repo):
    write(paths.PLIPS_DETAILED, PLIPS + plip(6326, 'tisto', '2025-04-12', title='Vitest')
          + plip(6320, 'tisto', '2025-02-02') + plip(2, 'tisto', '2025-04-08', 'plone/aurora')
          + plip(641, 'TISTO', '2025-09-13', 'plone/plone.restapi')
          + plip(7, 'tisto', '2024-05-01') + plip(9, 'tisto', '', state='open'))
    timo = next(p for p in community_page.build_page_data(2025)['people']['2025'] if p['id'] == 'timo')
    assert timo['plips'] == [
        {'repository': 'volto', 'plips': [
            {'repository': 'volto', 'number': 6326, 'title': 'Vitest',
             'url': 'https://github.com/plone/volto/issues/6326'},
            {'repository': 'volto', 'number': 6320, 'title': 'A PLIP',
             'url': 'https://github.com/plone/volto/issues/6320'}]},
        {'repository': 'aurora', 'plips': [{'repository': 'aurora', 'number': 2, 'title': 'A PLIP',
                                            'url': 'https://github.com/plone/aurora/issues/2'}]},
        {'repository': 'plone.restapi', 'plips': [{'repository': 'plone.restapi', 'number': 641, 'title': 'A PLIP',
                                                   'url': 'https://github.com/plone/plone.restapi/issues/641'}]}]


def test_a_plip_makes_its_author_and_organisation_active(repo):
    write(paths.PLIPS_DETAILED, PLIPS + plip(1, 'tisto', '2025-03-01') + plip(2, 'stranger', '2025-03-02'))
    data = community_page.build_page_data(2025)
    assert [p['id'] for p in data['people']['2025']] == ['stranger', 'timo']
    assert data['history']['2025']['people_active'] == 2
    # RedTurtle through the conference of the fixture, kitconcept through timo's PLIP; stranger has none
    assert data['headline']['year']['organisations'] == 2


def test_people_without_plips_have_an_empty_list(repo):
    write(paths.contributors_file(2025), CONTRIBUTORS + 'tisto,10,5\n')
    [entry] = community_page.build_page_data(2025)['people']['2025']
    assert entry['plips'] == []


def test_a_closed_plip_without_a_closing_date_counts_in_the_year_it_was_created(repo):
    # The same rule as plip_organisation_stats.plip_year, so the page and the points agree
    write(paths.PLIPS_DETAILED, PLIPS + '3,Old,tisto,closed,2024-02-01,2024-02-02,,plone/volto,https://u/3\n')
    data = community_page.build_page_data(2025)
    assert [p['id'] for p in data['people']['2024']] == ['timo']
    assert data['people']['2025'] == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_data.py -k "plip" -v`
Expected: FAIL (`KeyError: 'plips'`, wrong people lists).

- [ ] **Step 3: Implement** the functions of the Interfaces block; `build_page_data` reads `closed_plips(year)` once and passes `year_plips[y]` (`[]` for a year without) to `people_of_year` and `organisations_of_year`.

- [ ] **Step 4: Run the whole file to verify it passes**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_data.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/derive/community_page.py tests/test_community_page_data.py
git commit -m "List a person's PLIPs in the community page data"
```

---

### Task 2: PLIPs behind an organisation's points and in the History years

**Files:**
- Modify: `scripts/report/generate_community_recognition_report.py:71-75` (`load_plip_data`)
- Modify: `scripts/derive/community_page.py`
- Test: `tests/test_community_page_data.py`, `tests/test_recognition_method.py`

**Interfaces:**
- Consumes: `plip_entry`, `closed_plips` from Task 1.
- Produces:
  - In `generate_community_recognition_report.py`: `closed_plips_by_organisation(years, plips_file=paths.PLIPS_DETAILED, registry=None) -> dict[str, list[dict]]` — the grouping `load_plip_data` uses today; `load_plip_data` becomes `{org: {'closed_plips': len(rows)} for org, rows in closed_plips_by_organisation(...).items()}`, its output unchanged.
  - In `community_page.py`: `plips_by_year(rows) -> list[dict]` — `[{'year': 2025, 'plips': [entry, ...]}]`, years descending, entries by number descending.
  - `plips_by_organisation(rows, year, registry) -> list[dict]` — `[{'organisation': 'kitconcept GmbH', 'plips': [entry, ...]}, ..., {'organisation': None, 'plips': [...]}]`; named groups by name casefold, Unmapped as `None` last; entries by number descending.
  - Organisation data gets `'plips': plips_by_year(...)` from `closed_plips_by_organisation(recognition.five_years(year), registry=registry)[name]` when `'PLIP Contributions'` is among its categories, else `[]`.
  - History of a year gets `'plips': plips_by_organisation(year_plips[year], year, registry)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_community_page_data.py` (reusing `plip` from Task 1):

```python
def test_an_organisation_lists_the_plips_behind_its_points_by_year(repo):
    write(paths.PLIPS_DETAILED, PLIPS + plip(5, 'tisto', '2025-01-01') + plip(4, 'robgietema', '2025-02-01')
          + plip(3, 'tisto', '2023-01-01') + plip(1, 'tisto', '2019-01-01'))
    kitconcept = community_page.build_page_data(2025)['organisations']['kitconcept-gmbh']
    assert [(g['year'], [p['number'] for p in g['plips']]) for g in kitconcept['plips']] == [(2025, [5, 4]), (2023, [3])]
    [contribution] = kitconcept['categories']['PLIP Contributions']['contributions']
    assert contribution['text'].endswith(f"({sum(len(g['plips']) for g in kitconcept['plips'])} PLIPs)")


def test_an_organisation_without_plip_points_has_no_plip_list(repo):
    write(paths.PLIPS_DETAILED, PLIPS + plip(5, 'tisto', '2025-01-01'))
    write(paths.organisation_contributors_file(2025), ORGANISATIONS + 'kitconcept GmbH,0,500,1\n')
    kitconcept = community_page.build_page_data(2025)['organisations']['kitconcept-gmbh']
    assert 'PLIP Contributions' not in kitconcept['categories']
    assert kitconcept['plips'] == []


def test_history_groups_the_plips_of_the_year_by_organisation(repo):
    write(paths.PLIPS_DETAILED, PLIPS + plip(5, 'tisto', '2025-01-01') + plip(6, 'stranger', '2025-01-02')
          + plip(7, 'mamico', '2025-01-03') + plip(8, 'tisto', '2024-01-01'))
    history = community_page.build_page_data(2025)['history']
    assert [(g['organisation'], [p['number'] for p in g['plips']]) for g in history['2025']['plips']] == [
        ('kitconcept GmbH', [5]), ('RedTurtle', [7]), (None, [6])]
    assert [g['organisation'] for g in history['2024']['plips']] == ['kitconcept GmbH']
    assert history['2023']['plips'] == []
```

In `tests/test_recognition_method.py`, next to `test_plips_count_when_closed_in_the_five_years_for_the_organisation_of_that_year`, with the same rows:

```python
def test_closed_plips_by_organisation_returns_the_rows_load_plip_data_counts(data):
    rows = [f'{n},PLIP,tisto,closed,{year}-01-01,{year}-06-01,{year}-06-01,plone/volto,u\n'
            for n, year in enumerate([2019, 2021, 2022, 2023], 1)]
    write(data / 'plips.csv', PLIP_HEADER + ''.join(rows))
    groups = recognition.closed_plips_by_organisation(recognition.five_years(2025), str(data / 'plips.csv'))
    assert {org: [p['number'] for p in rows] for org, rows in groups.items()} == {
        'kitconcept GmbH': ['3', '4'], 'Unmapped': ['2']}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_data.py tests/test_recognition_method.py -k "plip" -v`
Expected: FAIL (`KeyError: 'plips'`, `AttributeError: closed_plips_by_organisation`).

- [ ] **Step 3: Implement** the functions of the Interfaces block. The organisation's list and the recognition count both come from `closed_plips_by_organisation`; `build_page_data` calls it once for the window and passes the result to `organisation_data`.

- [ ] **Step 4: Run both files to verify they pass**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_data.py tests/test_recognition_method.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/report/generate_community_recognition_report.py scripts/derive/community_page.py tests/test_community_page_data.py tests/test_recognition_method.py
git commit -m "Add the PLIPs behind the points and the PLIPs of each year to the page data"
```

---

### Task 3: Render the PLIP lists of organisations and History

**Files:**
- Modify: `scripts/report/site/templates/index.html` (organisation categories loop, History year)
- Modify: `scripts/report/site/static/site.css`
- Test: `tests/test_community_page_render.py`

**Interfaces:**
- Consumes: `organisation.plips` (`[{'year', 'plips'}]`) and `item.plips` (`[{'organisation', 'plips'}]`) from Task 2; entries as in the Global Constraints.

Markup, one shared shape for both lists:

```html
<ul class="plips">
  <li><span class="group">2025 <span class="count">2</span></span>
    <a href="URL">TITLE</a> <span class="ref">volto#6396</span> · <a …>…</a> <span class="ref">…</span></li>
</ul>
```

- Organisation: inside the `<details>` of the category `PLIP Contributions`, after `<ul class="contributions">`, when `organisation.plips`.
- History: `<h3>PLIPs</h3>` and the list after the Events block, before Board, when `item.plips`; group label the organisation name, or `no organisation recorded` for `None`. The year summary appends ` · N PLIPs` (N = total entries) when there are any. The condition "No community records for this year yet." also requires `not item.plips`.
- CSS: `.plips` without bullets, `.plips .group` muted, bold, small; `.plips .count` muted, normal weight; `.plips .ref` muted, small, monospace. Use the existing tokens (`var(--muted)`).

- [ ] **Step 1: Write the failing tests.** Add to `DATA` in `tests/test_community_page_render.py`: `'plips': [{'year': 2025, 'plips': [{'repository': 'volto', 'number': 6396, 'title': 'Remove <config> & co', 'url': 'https://github.com/plone/volto/issues/6396'}]}]` on `redturtle`, `'plips': []` on `jane-doe-independent`, `'plips': []` on every history year except `2025`, which gets `[{'organisation': 'RedTurtle', 'plips': [<the same entry>]}, {'organisation': None, 'plips': [{'repository': 'plone.restapi', 'number': 641, 'title': 'Behaviors', 'url': 'https://github.com/plone/plone.restapi/issues/641'}]}]`. Then:

```python
def test_organisation_lists_the_plips_behind_its_points(page):
    org = page.split('id="org-redturtle"')[1].split('id="org-')[0]
    assert 'href="https://github.com/plone/volto/issues/6396"' in org
    assert 'Remove &lt;config&gt; &amp; co' in org
    assert '>volto#6396<' in org


def test_history_lists_the_plips_of_the_year_by_organisation(page):
    year = page.split('id="year-2025"')[1].split('</details>')[0]
    assert '2 PLIPs' in year
    assert year.index('>RedTurtle') < year.index('no organisation recorded')
    assert '>plone.restapi#641<' in year
    assert 'PLIPs' not in page.split('id="year-2005"')[1].split('</details>')[0]


def test_plip_lists_name_no_author(page):
    visible = page.split('<script type="application/json" id="people-data">')[0]
    assert 'Secret Person' not in visible and 'secretlogin' not in visible
```

- [ ] **Step 2: Run them to verify they fail**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_render.py -v`
Expected: the two list tests FAIL; the rest PASS.

- [ ] **Step 3: Implement** the markup and CSS above.

- [ ] **Step 4: Run to verify they pass**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_render.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/report/site/templates/index.html scripts/report/site/static/site.css tests/test_community_page_render.py
git commit -m "Show the PLIPs of organisations and years on the community page"
```

---

### Task 4: The PLIPs row on the person card

**Files:**
- Modify: `scripts/report/site/static/site.js` (`render()`, after the facts rows, before the Talks block)
- Modify: `scripts/report/site/static/site.css` (reuse `.plips` from Task 3 where it fits)
- Test: `tests/test_community_page_render.py`

**Interfaces:**
- Consumes: `match.plips` (`[{'repository', 'plips': [entry]}]`) from Task 1, embedded through the existing people data.

Behaviour:
- When `(match.plips || []).length`: a `dt` `PLIPs (n)`, n the total of entries, and a `dd` with one line per group: the repository name in a `span.group`, then the entries joined by ` · `, each an `a` (`href` = url, `textContent` = title) followed by a `span.ref` `#<number>`. Only `textContent`, never `innerHTML`, for titles.
- The row goes after "Community roles" and before "Talks".
- When the row is shown, the note line gets the sentence `PLIPs: proposed by them and closed in <year>.` before its existing text.

- [ ] **Step 1: Write the failing tests**

```python
def test_people_data_carries_the_plips(page):
    data = page.split('<script type="application/json" id="people-data">')[1].split('</script>')[0]
    assert json.loads(data)['years']['2025'][0]['plips'][0]['repository'] == 'volto'


def test_page_script_draws_the_plips_row():
    script = (REPO / 'scripts/report/site/static/site.js').read_text(encoding='utf-8')
    assert "'PLIPs ('" in script and 'match.plips || []' in script
    assert 'PLIPs: proposed by them and closed in ' in script
    assert script.index('match.plips || []') < script.index('match.talks || []')
```

Add `'plips': [{'repository': 'volto', 'plips': [{'repository': 'volto', 'number': 6326, 'title': 'Vitest', 'url': 'https://github.com/plone/volto/issues/6326'}]}]` to `secret-person` in `DATA`.

- [ ] **Step 2: Run them to verify they fail**

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_render.py -k plips -v`
Expected: `test_page_script_draws_the_plips_row` FAILs.

- [ ] **Step 3: Implement** the behaviour in `site.js` in the style of the Talks block.

- [ ] **Step 4: Run to verify they pass**, and check the card by hand

Run: `~/.venvs/plone-contributor-statistics/bin/python -m pytest tests/test_community_page_render.py -v`
Expected: all PASS.
Then `make community-page site` in the worktree, open `_site/index.html`, search `tisto`, year 2025: the card shows `PLIPs (6)` grouped volto / aurora / plone.restapi; the History year 2025 and kitconcept's PLIP category show their lists.

- [ ] **Step 5: Commit**

```bash
git add scripts/report/site/static/site.js scripts/report/site/static/site.css tests/test_community_page_render.py
git commit -m "Show a person's PLIPs on their card"
```

---

### Task 5: Docs, derived data, checks

**Files:**
- Modify: `docs/explanation/community-page.md` (People active, Organisations active, Recognition levels, People, History)
- Modify: `docs/explanation/method-history.md` (one entry in the current list, linking #104)
- Modify: `derived/community-page.json` (regenerated, never by hand)

- [ ] **Step 1: Update the docs.** In `community-page.md`:
  - People active: code work also includes a PLIP closed in the year, proposed by the person.
  - Organisations active: also through the PLIPs of its people.
  - Recognition levels: the category PLIP Contributions lists its PLIPs by year of closing, each linked to its issue, without the author.
  - People: the card lists the person's PLIPs of the year, grouped by project; what "PLIPs" means (proposed by them, closed in the year; a closed PLIP stands for a finished one, #14).
  - History: the PLIPs of the year, grouped by the organisation of the author in that year, alphabetically, without authors.
  - No numbers or rankings (AGENTS.md).
  In `method-history.md`: "A PLIP closed in a year makes its author active in that year, and the community page lists the PLIPs on the person's card, behind an organisation's points and per year ([#104](https://github.com/plone/plone-contributor-statistics/issues/104))."

- [ ] **Step 2: Regenerate and check**

Run: `make community-page` then `git diff --stat derived/`
Expected: only `derived/community-page.json` changes.
Run: `make test` and `make docs`
Expected: all tests pass, docs build without warnings. (`make check` runs flake8 too; compare its lint output with `origin/main` and report only new messages.)

- [ ] **Step 3: Commit**

```bash
git add docs derived/community-page.json
git commit -m "Document the PLIPs on the community page, regenerate its data"
```

---

### Task 6: Archive, pull request, close #189

- [ ] **Step 1:** Copy the design and this plan unchanged to `archive/specs-and-plans/2026-11-01-plips-on-community-page-design.md` and `…-plan.md`; commit "Archive the design and plan of the PLIPs on the community page".
- [ ] **Step 2:** Push the branch and open the pull request: what and why, the three places, the change in "people active", "Closes #104", "Replaces #189", refers to #191; ends with one `Assisted-by:` line per model.
- [ ] **Step 3:** After the user confirms, comment on #189 (thanks, the PLIPs are now on the page, link the new PR, why no Markdown report) and close it.
