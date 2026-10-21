# Conference talks: design

Date: 2026-10-21. Decided with Jens Klein in conversation; the calls marked *(builder's call)* are mine, the rest is his.

## Intent

Talks at Plone conferences are community contributions that the curated data does not hold. The data has the conference organisers, the trainers and the World Plone Day talks, but not the keynotes, talks and panels of the annual Plone Conference or of the regional conferences. Two things follow from that gap:

- The community page cannot show that a person spoke in a year, although it shows that they trained, organised or sat on the Board.
- Speaker pages and talk recordings are the richest dated source for a person's organisation in a given year (the affiliation work of #139 found Eric Bréhault's employer for 2020 and 2021 only in the audio of his talks), and nobody looks at them systematically.

The collection records the talks, shows them in the person box of the community page, and makes the speaker pages a regular source for affiliations.

## Goals

- A curated record of every keynote, talk and panel at Plone conferences, global and regional, from the first Plone Conference (2003) to the present, each with its public source and, where one exists, the link to its recording.
- The person box of the community page lists a speaker's talks of the year, each title linked to its video.
- The format follows the existing kinds of curated community data, so the schema, the checks, the model and the docs treat it like the others.

## Non-goals

- **No recognition points.** The counting rules are the Marketing Team's or the Board's. Talks are shown at person level and do not change the wall of contributors or the organisation levels. If the Marketing Team or the Board decides otherwise, that is a later change to the points file and the derive scripts.
- **No lightning talks for now.** A lightning-talk session is one recording with many three-to-five-minute talks; it is left out until someone wants it.
- **World Plone Day talks stay where they are**, in their own files with their own rules.
- Trainings stay in their own files; a tutorial in a talk programme is a training by the existing rule.
- Not a video archive: the link points to wherever the recording is published (YouTube, Vimeo, archived plone.tv); nothing is downloaded or mirrored.

## Anti-goals

- A talk without a public source. Every row links the programme page, the schedule, the speaker page or the recording that proves the talk took place; a talk remembered but not documented is not a row.
- Guessing speakers' organisations from the talk. The talk itself says nothing about the employer; only what the speaker page, the bio or the speaker in the recording says becomes an affiliation row, by the existing rule for World Plone Day talks.
- Treating the data as an "event" that counts for an organisation in the history. A talk is a person's contribution; the organisations column exists only for the rare talk given by a company team instead of named people, as in the World Plone Day files.

## The data

### Files

One file per year, `curated/community-contributions/YYYY-conference-talks.csv`, holding every conference of that year. The event is a column, not part of the file name, because a year has several conferences. *(Builder's call:* the kind is named `conference-talks`, distinct from `world-plone-day-talks`.)

### Columns

| Column | Content |
|---|---|
| `event` | The conference, as it named itself: "Plone Conference 2021", "Plone Tagung 2023", "PloneConf Brasil 2019", "Plone Symposium East 2011". Required. |
| `scope` | `global` for the annual Plone Conference, `regional` for every other conference. Required. |
| `type` | `Keynote`, `Talk` or `Panel`. Required. A talk the programme calls a talk, a presentation or a session is a `Talk`; a keynote is what the programme calls one; a panel is a discussion with several named participants, all of whom are its speakers. |
| `title` | The title as the programme gives it. Required. |
| `speakers` | Ids from the people register, several separated by semicolons (set column, `x-set: people`). Empty only for a talk given by a company team. |
| `organisations` | Ids from the organisations register, several separated by semicolons (set column, `x-set: organisations`), for a talk the programme attributes to a team instead of people. Normally empty. |
| `video` | The web address of the recording, when one exists. One link; a talk recorded in two parts gets the first part here and the second in `notes`. *(Builder's call.)* |
| `source` | The public record that proves the talk: the programme or schedule page, the speaker page, or the recording. Required, must contain a web address. |
| `notes` | Free text. |

The rows of a file are sorted by event, then title, so that one conference stays together. *(Builder's call.)*

Rules that carry over from the World Plone Day talks:

- Only people speak: a talk is listed under its speakers; the organisations column is for team talks only.
- What the speaker page, the bio or the speaker in the recording says about their organisation in that year is an affiliation row for that year, with the page or the recording (with a timestamp) as its source. The talk row itself carries no organisation of the speaker.
- A speaker not in the people register is added with the person tool, with the speaker page as the source; an unknown speaker without any public identity stays out of `speakers` and is named in `notes`.

### What counts as a conference

The annual Plone Conference (Vienna 2004 onward, including the online conferences of 2020 and 2021; the 2003 New Orleans conference counts if a programme is on record) and every regional Plone conference: Plone Tagung and its predecessors in the German-speaking countries, the Plone Symposium East and Midwest, PloneConf Brasil and the Brazilian symposia, Plone Open Garden, the Plone conferences in Japan, Italy, the Netherlands, France and elsewhere, as long as the event is a conference with a programme of talks. A sprint's talk evening and a meetup are not conferences. World Plone Day is excluded. The Alpine City Sprint is a sprint. *(Builder's call where the conversation did not name the event; the scope column makes any later redrawing cheap.)*

## The page

The person box of the community page (the search by login or name, one year at a time) shows, after "Community roles", a row "Talks" with the talks of that year: the title, linked to the video when there is one, with the event in brackets when the person spoke at more than one conference that year. *(Builder's call on the exact rendering; the box is rendered by `scripts/report/site/static/site.js` from `derived/community-page.json`, so the data gets a `talks` list per person and year with `title`, `event` and `video`.)* The row also lists the person's World Plone Day talks of that year, with the recording that is their source as the video, so the box shows every talk the data has. *(Builder's call.)*

**A talk is an activity.** Speaking makes a person active in that year, exactly as training, organising a sprint or a World Plone Day talk does: the kind is a role kind with the label "Speaker", and the World Plone Day talks take the same label instead of "Talk". *(The label change is the builder's call.)* The consequences are the ones every role has today: the person appears among the people active of the year, their organisation of that year among the organisations active, and the per-organisation history counts the role. Nothing else changes: no points, no change to the wall or the levels, no events entry in the history. The headline numbers of a year move when its talks are added; that is expected and documented, not a regression.

## Code and documentation

- Schema `curated/schemas/conference-talks.json`, registered in `curated/datapackage.json` by the datapackage tool, in the schema docs tool and in the schema tests like the other kinds.
- The model (`scripts/lib/model/community.py`) knows the kind as a role kind with the label "Speaker", the set column `speakers`, the key column `title`, and exposes the talks so that the derive script can list them per person; it needs no event rule.
- The derive script of the community page (`scripts/derive/community_page.py`) adds the talks to the people of the year; the page script renders them; the templates do not change unless the box moves into the template.
- The docs: the page on curated community data gets the definitions above (what a conference is, what counts as a talk, keynote, panel; lightning talks left out; no points); the community page explanation names the talks row; the curated files reference is regenerated.
- Tests: offline pytest for the model (reading a talks file, the role label, the set column), the derive step (talks per person, a speaker counted as active), the page data (the talks list in the derived JSON and in the data embedded in the rendered page, with a video and without one), and the schema. The row itself is drawn by the page script in the browser; the repository has no JavaScript test runner and does not get one for this. *(Builder's call.)*
- Checks: ids resolve against the registers, sorting, the enums; `make check` reports as for the other kinds.

## Filling the collection

Two kinds of pull request:

1. **Format first.** The schema, model, derive, page, docs and tests, with one conference as the worked example (Plone Conference 2021, where this started, including Eric Bréhault's talk). *(Builder's call.)*
2. **Then the data, year by year, newest first**, one pull request per year or per conference for the large years. Sources: the conference sites (`YYYY.ploneconf.org` live or in the Wayback Machine, the regional sites), the Plone YouTube channel playlists, Vimeo and the archived plone.tv for the years before YouTube. Research agents may collect; every row's source and every video link is re-fetched before it lands, as in the affiliation rounds. The speaker pages are read for organisations at the same time, and what they say goes into `affiliations.csv` (dated record) or stays out; a bio that names no employer is noted as checked. A recording is searched for a spoken introduction only by a person or a model reading the transcript, not by a script: auto-captions garble names.

The order of events within the data pull requests, and whether an agent round covers one year or several, is left to the builder.

## Constraints

- All rules of AGENTS.md: a public record per row, opaque ids, the person tool for new people, `make check` after every change, docs in the same pull request as the format, specs and plans archived in `archive/specs-and-plans/`, `Assisted-by` footers.
- No numbers in the docs.
- The reproducibility test: the format pull request regenerates `derived/community-page.json`; it changes by the talks of the example conference and by what a new role changes for every role today (the people and organisations active of that year, the history counts), and by nothing else.

## Left to the builder

- The exact JSON shape of the talks per person and the rendering in the box.
- Whether the `event` column gets a check against a fixed list (probably not: the list grows) or stays free text with the scope column as the only enum.
- Handling of a talk given twice (two conferences, one year): two rows, one per event.
- Handling of a speaker who appears under a nickname on the programme: the identities register, as for every other kind.
