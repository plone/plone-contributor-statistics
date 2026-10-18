# Design: community page

Date: 2026-10-19
Repository: `plone/plone-contributor-statistics`
Related: #56 (published recognition page not reproducible), #103 (charts in the repository instead of Flourish), #116 (work attributed to the Plone Foundation), #117 (matching people across code and community work)

## 1. Intent

Plone's Community Recognition page on plone.org was made outside this repository, and it can't be reproduced.
The repository now has clean, sourced, tested data.
It needs its own generated page that shows who builds Plone: the information on the published page, and more of it, in a nicer way.
The page is generated from the repository's data and published on the repository's GitHub Pages site, with no external service.

The page must be inviting, and its data must be clear and right.
Turning it into a plone.org news item is a separate, later step, possibly done by an LLM, and is out of scope.

### Readers

1. **The newcomer.** For example, a company that has just heard of Plone.
   In a few seconds they must see that Plone thrives, and which organisations do the work, so they know whom they could hire.
   This is earned visibility, unlike the sponsors page, where visibility is bought.
   They aren't interested in details.
2. **The curious community member.**
   They want to dig in:
   - as an individual, to see where they stand in a year, per category;
   - as an organisation, to see why it has its recognition level, and how it collected its points.
3. **The long-time member.**
   They want to page through history, year by year, back to 2003.

The first screen is for reader 1.
Everything deeper is reachable, but out of the way.

## 2. Goals, non-goals, anti-goals

Goals

- A generated community page at the root of the GitHub Pages site, in a look in the spirit of plone.org.
- The Sphinx documentation moves to `/docs/`.
  The page links to the docs, and the docs link back to the page.
- First screen: the numbers that show whether Plone thrives, and every organisation with a recognition level.
- Below it, tabs for organisations, people and history.
- Transparency: every number links to its source rows and public records, and to the rules in the docs.
- A committed data file with every number the page shows, so that changes to the numbers show up in pull requests.

Non-goals

- Publishing on plone.org, or producing a news item.
- Redirects from the old docs URLs.
  The docs have been online for about two days, so breaking those links is accepted.
- New data collection.
  For example, reviews and comments per person (#61), meetups, or community sprints.
  The page shows only what the data holds; community sprints are being recorded elsewhere and join when they land, see 4.3.
- Changing the recognition method or the levels.

Anti-goals: these would make the work a failure even if everything technically works.

- **Hiding organisations.**
  Every organisation with a recognition level must be visible on the first screen.
  Showing some and folding the rest away ("+ 39 more") is not acceptable.
- **A ranked list of people's names.**
  People are never listed by name in a ranking.
  Public roles (Board, team leads, release managers, organisers) may be named.
- **Numbers without a definition or a source.**
  Every number on the page must be traceable to its definition in the docs, and to the rows that make it up.
- **External services at runtime.**
  No CDNs, no external fonts, no analytics, no third-party embeds.
  Every asset is served from the site itself.
- **A home-made static site generator.**
  Use existing libraries: Jinja2 for templating, at least.

## 3. Constraints

- Follow the repository rules in `AGENTS.md`:
  - work in a worktree;
  - update the docs in the same PR;
  - code gets offline pytest tests, data gets format checks;
  - archive specs and plans to `archive/specs-and-plans/` before the PR;
  - end commits and PRs with `Assisted-by:`.
- Statistics in prose: the docs must not contain rankings or numbers, because they go stale.
  The page is generated output, so it may.
- The page reads only committed data: `curated/`, `collected/`, `derived/`.
  It never calls GitHub.
- CI builds and deploys the site from `.github/workflows/docs.yml`, which currently publishes `docs/_build/html` as the whole site.
- The layout rules apply: code goes in `scripts/`, data in `derived/`; generated HTML isn't committed, and is gitignored like `docs/_build/`.

## 4. Decided parts

### 4.1 Site structure (decided with the maintainer)

| Path | Content |
|---|---|
| `/` | The community page: generated, in a Plone look, with links to the docs. |
| `/docs/` | The Sphinx documentation, moved from the root. `html_baseurl` and links in `README.md` and `AGENTS.md` follow. |

- CI builds both into one Pages artifact.
- The HTML of the page is built in CI only.
- Developers preview it locally with new Make targets, the way they preview the docs.
  For example, `make site` builds it, and a target serves or opens the result; the exact names are the builder's call.

### 4.2 First screen (decided with the maintainer)

- **Two periods:** the last completed year, and the five years up to and including it.
  The full history since 2003 appears at most as a small secondary line.
- **Three plain numbers per period, no charts.**
  The definitions are in 4.3.
  - **People active.**
  - **Organisations active.**
  - **Events.**
- **The organisation wall:**
  - every organisation with a recognition level, grouped by level (Platinum, Gold, Silver, Bronze, Community Contributor), as the marketing team communicates it;
  - none hidden;
  - each name links to its detail in the Organisations tab.
- **Levels come from the script (decided with the maintainer: the script is the truth).**
  - They come from `derived/community-recognition/YYYY-community-recognition-report.csv` for the last completed year.
  - A visible note links to the explanation of why they can differ from the levels published on plone.org in August 2026 (`docs/explanation/community-recognition.md`).
- **Who is on the wall (decided with the maintainer):**
  - every entry with a level is shown, including self-employed people ("Name (independent)") and one-person companies, because they are businesses; naming them is fine, since all the data is public record;
  - the Plone Foundation is shown as the script calculates it; its attribution is a data flaw tracked in #116 and out of scope here.

### 4.3 Definitions of the numbers

Decided with the maintainer:

- **People active** in a period: everyone with **code work** or **community work** in it.
  - Code work is a commit or a merged pull request (`collected/contributors/`).
  - Community work is a public role or contribution in `curated/community-contributions/`: Board, team lead, release manager, conference organiser, talk (World Plone Day), training, sprint organiser, podcast.
  - Unmapped and self-employed people count.
- **Organisations active** in a period: organisations with code work or community work in it.
  Unmapped, and self-employed people ("Name (independent)"), drop out.
- **Events:** what the data records as gatherings.
  - The current kinds are the Plone Conference, World Plone Day events and strategic sprints.
  - Community sprints join when they're recorded; meetups join if they ever are.
  - Trainings are sessions within the conference, not separate events.
  - The event kinds are a short list in the code that new kinds can join.

Settled after the review:

- **People identity** (decided with the maintainer: the matching gap is #117, out of scope here):
  - A person is keyed by GitHub login where the existing data resolves one: the handle columns, the `https://github.com/<login>` links in Source cells, `commit_authors.csv` and `mapping-github-username-to-fullname.csv`.
  - Names that stay unmatched count as their own people, compared without case and accents.
  - Group entries in person columns, such as "PloneGov-BR team", don't count as people.
  - The docs and a note on the page say that "people active" may count a person twice until #117 is solved.
- **Counting events** (my call):
  - **Plone Conference:** one per year with a file.
  - **Strategic sprints:** one per distinct sprint name per year.
  - **World Plone Day:** one per year with rows, with its organising organisations listed under it.
    Each row is an organisation, and all rows of a year share the yearly link, so counting rows would make World Plone Day more than half of all events.
    A location column would allow counting local events (#118).
  - The points are unchanged; changing the method is a non-goal.

### 4.4 Below the first screen: tabs

Decided with the maintainer: the tabs layout.
The former "Community work" tab folds into History.

- **Organisations:**
  - choose an organisation;
  - see its recognition level, its points and the gap to the next level;
  - see the points per category, expandable down to the contributions behind them (which sprint, shared with whom, how many merged pull requests and by how many people);
  - every point links to its source row and its public record, and the rules link to the points file and to the docs.
    Rows without a public record yet (#46, about a fifth of the 2025 points) link to their row on GitHub, marked "public record pending" (my call);
  - a contribution graph over the years, split by area: code, community roles, events.
    It shows raw yearly counts per area (commits and merged pull requests, roles, events), not points, because points exist only for the recognition year (my call).
- **People:**
  - no list of names;
  - search for a person, then see, for a chosen year, where they stand in each category, for example "27th of 112 in merged pull requests";
  - see the community roles they held that year;
  - without a search, show only anonymous distributions.
  - Categories:
    - **Commits.**
    - **Merged pull requests.**
    - **Community roles**, listed, not ranked.
  - Reviews per person aren't available (#61).
  - The page data carries the yearly counts per login (and per unmatched name), sorted alphabetically, and the browser works out ranks.
    This is the same data that `collected/contributors/` already publishes (my call).
    A person's code work and community roles appear together only where the identity is resolved (#117).
- **History:** one page or section per year from 2003, with:
  - the Board and the team leads, named;
  - the number of active people;
  - commits, and merged pull requests from 2010 on, when they exist;
  - the events held, with links to their sources.

### 4.5 How it's built

Decided with the maintainer: Jinja2, no home-made site generator, CI-only HTML, and a local preview.
My calls:

- **Two steps, matching the pipeline:**
  1. A derive script in `scripts/derive/` computes every number and list the page shows into committed data in `derived/`.
     A single JSON file, or a few, is the builder's call.
     The reproducibility test (`tests/test_reproducible_outputs.py`) covers it.
  2. A report script in `scripts/report/` renders the page from that data with Jinja2 into a gitignored build folder.
     It adds the data as JSON for the interactive parts.
- **Templates and static assets** live next to the report script, for example `scripts/report/site/templates/` and `static/`; the exact place is the builder's call.
- **Interactivity:** tabs, search, expanding details and graphs use plain JavaScript.
  - Charts are inline SVG, or a small, permissively licensed charting library copied into the repository, never loaded from a CDN.
  - The library choice is the builder's.
- **Look:** in the spirit of plone.org: Plone blue, clear type, generous whitespace.
  - The page uses a system font stack, or a font file in the repository; no external fonts.
  - It works on mobile, and the first screen reads without JavaScript.
- **CI:** `docs.yml` builds the Sphinx docs into `/docs/` and the page into `/` of one artifact.
  Pull requests build both, without deploying.

### 4.6 Tests and docs

- Offline tests for the derive step:
  - each definition in 4.3, on small fixtures;
  - every organisation with a level appears in the data for the wall;
  - Unmapped and independents drop out of "organisations active".
- A build test: the page renders from the committed data, contains every organisation with a level, and contains no ranked list of people's names.
- The docs get:
  - an explanation page for the community page: what each number means, with the definitions of 4.3 and links to the data;
  - the new Make targets in `make-targets.md`;
  - the new data file in `data-files.md`;
  - the site structure in `README.md` and `AGENTS.md`.

## 5. Left to the builder

- The names and the number of the data files, and the exact paths of templates and static assets.
- The Make target names for building and previewing.
- The charting approach: inline SVG, or a copied library.
- Visual details within "the spirit of plone.org".
- How the page and its tabs are split into PRs.
- How the year pages are navigated.

## 6. Follow-ups outside this work

- #116: work attributed to the Plone Foundation instead of the people who did it.
- #117: matching people across code and community work.
- #118: World Plone Day locations; a location column with sources would allow counting local events.
- **The talk types the recognition script counts (#119).**
  It skips only a list of types, so types such as "Newsroom" are counted as World Plone Day talks.
  #119; the data must be right.
