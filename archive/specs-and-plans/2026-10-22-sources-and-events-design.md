# Sources, citations and events: design

Date: 2026-10-22. State of the data: `origin/main` at c987479 (after #171).
Builds on the structure agreed in #139 (https://github.com/plone/plone-contributor-statistics/issues/139#issuecomment-6276443815) and implemented in #145; this design changes parts of it and keeps the rest.

## Intent

The evidence behind the data should live in the repository, read once and stored.
Today every tool run, review round and research agent goes back to the web, mostly to the Wayback Machine, to re-read the same pages.
That takes ages and is no longer fair use of the Wayback Machine.
At the same time, the same pages are copied into dozens of cells: curated data cites 8,574 URLs, of which only 5,179 are distinct.
A `source` cell mixes a label, a quote, a URL, an archive URL and our own conclusions; decisions and conflicting records live in `notes` prose; the same event name is repeated on every talk row.

The fix is a small relational structure in plain files, not a graph database or RDF:
every source is a record of its own, stored once with the passages we cite from it (quotations, never a copy of the page);
every claim cites sources with a verbatim snippet;
who counts for which organisation is computed by the rules, and human decisions are themselves sources;
events are records that talks, trainings and organisers point to.

## Goals

- **Fetch once.** Every source is fetched once. The raw download stays in a local gitignored cache; the repository stores the passages we cite, which is all we may legally republish. Tools, checks, agents and the build work offline from the stored passages.
- **Store once.** A source has one row and an id; every use refers to the id.
- **Verifiable snippets.** A citation quotes the source verbatim, and a check proves offline that the quote is in the stored text.
- **Readings, not guesses.** An affiliation is our careful reading of what its sources say. Where we interpret, the row's `notes` say so. A new statement by the person is a new source, not an edit.
- **Rules compute, decisions settle.** The organisation a person counts for in a year is computed from the affiliations by the rules in `docs/explanation/attribution.md`, tie-breaks included. A recorded human decision overrides the rules for the years it covers, and settles what the rules can't; the decision is a source.
- **Events as records.** Conferences, symposia, World Plone Day locations and sprints are rows; talks, trainings and organisers point to them.
- **One file per kind.** Curated community data has one file per kind with a year (or an event that has a date), not one file per year.

## Non-goals

- No property graph, RDF, triple store or database server. Plain CSV and text files in git, read by `scripts/lib/model/`.
- `collected/` keeps its yearly files (the collectors rewrite only the current year; past years never change).
- No change to the attribution rules for code. They are restated as computation over the new tables, but what counts for whom stays as documented. (The organiser rule below is a deliberate change, in its own PR.)
- No new research. The migration moves what exists; it does not add evidence.
- The recognition points and levels files (`community-recognition-*.csv`) are rule tables, not records; they stay as they are.

## Anti-goals

- **Losing evidence.** A migration or a tool that drops a URL, a quote, a note or a reviewed decision is a failure even if everything else works (see the "evidence accumulates" rule: tools add evidence and never override it, unless the new evidence is stronger; conflicting records are stored, never only mentioned in a PR).
- **Changing the statistics by accident.** The mechanical part of the migration must regenerate `derived/` and `reports/` byte-identically (except "Generated on" lines).
- **Hammering the Wayback Machine.** The one-time capture of existing sources must be rate-limited and resumable; nothing fetches a source twice while its raw copy is in the local cache. A new quote from a source that isn't cached on this machine may need one more fetch; that is accepted.
- **Unreadable data.** Long texts don't go into CSV cells.
- **Republishing other people's pages.** The repository holds quotations with their source, never whole pages, Wayback copies or full captions.

## Constraints from the repository (unchanged)

- Opaque slug ids for people, organisations, and now events; never renamed. Frictionless Table Schema in `curated/schemas/` and `curated/datapackage.json` is the format authority; docs and checks derive from it.
- `scripts/lib/model/` is the only reader of `curated/`.
- Multi-valued cells (semicolons) only where the elements have no attributes and nothing runs parallel.
- Every curated row needs a public record (`AGENTS.md`); the exception for early CVS/SVN commit authors stays.
- Code changes get offline pytest tests with fakes for the network; data changes get format checks.
- A PR that changes what the docs describe updates `docs/` in the same PR. Specs and plans are archived in `archive/specs-and-plans/` before the PR.

## The structure

Decided with Jens in the brainstorm unless marked *(my call)*. The vocabulary of kinds is a first draft and will be refined.

### person

`id, name`

`name` is the name the person uses today (after a marriage, the new name). Everything else about a person is an identity.
*(my call)* The public record for the name is the person's `name` or `github` identity; `people.csv` loses its `github` and `source` columns.

### identity

`person, kind, value, source, snippet, notes`

One way a person appears in data. Kinds: `github` (login), `email`, `name` (another spelling or an earlier name), `svn` (Subversion/CVS user), `irc`, `discourse` (community.plone.org handle); more as needed.
`source` is a source id. The `github` column of `people.csv` and the "SVN user …" phrases now hidden in source text become identity rows.
The CVS/SVN exception: an early commit author identity may rest on a stated reason in `notes` instead of a public record.

### source

`id, kind, title, date, url, archive_url, fetched, notes`, plus an excerpt file `curated/sources/excerpts/<id>.md`.

- `kind` *(draft vocabulary)*: `page`, `speaker-page`, `profile`, `commit`, `video`, `pdf`, `register`, `issue-comment`, `decision`.
- `date`: the date the source speaks for: its publication date if it shows one (a commit's date, a news item's date), else the capture date of the archived copy, else, for a live page, the date it was fetched. Readings use it to decide which year a statement is about.
- `url`: the original URL; `archive_url`: the archived copy that was read, if any. The archive's capture time is part of that URL (`/web/<14-digit timestamp>id_/…`) and is not repeated in a column.
- `fetched`: when we read the source, as a UTC timestamp (`2026-10-22T14:03:51Z`), so it is clear which version of a changing page (a GitHub profile, a team page) the excerpt shows.
- The excerpt file holds the passages we cite, as plain text or Markdown, each with enough context to read it fairly (about the paragraph around the quote; for a list page, the entry; for a video, the caption lines around the statement with their timestamp). For a commit it holds author, date and message; for a GitHub profile the name, company, bio and location fields. It grows when a new citation quotes another passage of the same source. Whole pages, full captions and archived copies are not committed (legally we may only quote).
- *(my call)* The id is derived deterministically from the normalized original URL plus, for an archived copy, the capture timestamp (for example the first 12 hex digits of a SHA-1), so the same page can't get two rows. Two captures of one page at different dates are two sources. The builder may choose a different stable scheme.
- A source whose page is gone and has no capture keeps its row; its excerpt file says it could not be fetched, and citations to it are reported as unverified.

### decision

A decision is a source with `kind = decision`. Its `url` is the public record of the decision (a PR or issue comment, usually Jens's); its excerpt is the reasoning, for example "260 of his 261 commits of 2019 carry a personal address, so his own statement of 2019 decides".
Decisions are cited like any other source. A decision that exists only in a chat is not a decision.
*(my call)* One public comment is one source, even when it decides several cases (the #153 comment decides about ten rejections): its excerpt is the captured comment (our own repository's comment, so it may be stored whole), and the reason for each case is the snippet of the citation that uses it. A decision applies to the years of the affiliation that cites it; the migration splits rows so that a decision covers exactly the years it decides.

**A later decision overrules an earlier one** (agreed with Jens). Of two decisions covering the same person and year, the one with the later `date` counts. The earlier one stays as history and is never deleted. The later decision must say what it overrules: its citation names the earlier decision's source id in `supersedes`. Example: #153 put Ramon Navarro Bosch's 2016 with Intranetum by the tie-breaker; if he later states in public that 2016 was Onna, a new decision cites his statement and supersedes the #153 decision, and both stay readable.

### affiliation

`id, person, organisation, from, to, status, checked, notes`

Our reading: the person belonged to the organisation from `from` to `to` (empty `to` = ongoing).
`status`:
- `stated`: its citations say so, read carefully. An ambiguous sentence supports only what it unambiguously says: "working with Plone since 2005 at Zest Software" (2023) supports Zest in 2023, not 2005–2022; Maurits's 2012 page "has been a Plone programmer for Zest Software since 2005" supports 2005–2012.
- `assumed` *(my call)*: today's "not verified" rows (ranges extended beyond their records). Kept and counted as today, because Jens decided not to trim yet; stated rows win over assumed ones in a year where they overlap.
- `denied`: rare. A reading that the person did *not* belong to the organisation in those years, for example "the Zest address in Maurits's 2024–2025 commits is an old mailbox". Replaces `rejected_proposals.csv`. *(my call)* A `denied` row with an empty organisation records a reviewed "no public record for these years, stays Unmapped" (#86, about 50 such notes today), so the tools don't propose those years again.
- `proposed` *(my call)*: a reading a tool produced and nobody has reviewed. Never counted. Replaces `affiliation_proposals.csv`.

`checked` (the date someone last verified the row) stays as today.
Rows that today cover years by the bridging rule (notes "between records of … of the same organisation", 132 rows) stay `stated` with their ranges and notes *(my call)*: the rule gives the same result, and a stated record of another organisation inside such a span becomes a listed conflict, which is what should happen.

Affiliations of one person **may overlap**. Fred van Dijk's 2023 page ("Nowadays he works for both Zest and Kitconcept") is two stated affiliations for 2023; a conflicting speaker page that today sits in `notes` as "not applied" becomes its own stated affiliation. Which one counts is computed (below).

### citation

`affiliation, source, snippet, supersedes, notes`

One row per source an affiliation rests on; an affiliation may have many. `supersedes` is set only on a decision citation and names the source id of the decision it overrules.
`snippet` is verbatim text from the source's excerpt; the check normalizes whitespace and typographic quotes before comparing. *(my call)* `snippet` may be empty for citations the migration could not quote (labels like "GitHub profile, company: kitconcept" are our wording, not the page's); the label goes to `notes`, and a report lists citations without a snippet as work to do.
*(my call)* A migrated quote the captured text doesn't contain (an ellipsis, auto-captions, a PDF, another capture, a live page that changed since) stays as the snippet and is listed in a committed baseline of known mismatches with the reason; the check fails only for mismatches not in the baseline, so every new citation is verified and no old quote is lost.

### counting (computed, never edited)

The organisation a person counts for in a year is computed from the affiliations and written to `derived/`. The order, restating `attribution.md`:

1. `proposed` rows are ignored; a `denied` row removes its organisation from its years.
2. If a `stated` or `assumed` row of the year cites a `decision` for that year, it counts. A decision overrides every rule below; of several decisions for the same person and year, the latest counts.
3. If exactly one organisation remains, it counts. Stated rows win over assumed ones.
4. Change year: if one organisation also covers the year before and the other also covers the year after, the one the person leaves counts.
5. Bridging: two stated records of the same organisation cover the years between them when no stated record of another organisation lies between. *(my call)* Applied in the computation, so new readings can stay narrow; migrated rows keep their ranges, which already include bridged years.
6. Tie-breaks, automatic as today (Jens: "the tie breaks stay automatic unless there's a different decision recorded"):
   a. one record names two organisations for the same time: the one named first in the snippet counts;
   b. the organisation whose address most of the person's commits of that year carry (the model's existing `match_domain` on the commit addresses);
   c. if most commits carry a personal address: the organisation the person's own public statement of that year names *(my call: own statements are sources of kind `speaker-page`, `profile`, a personal page, or a comment by the person)*;
   d. if that names no employer: the organisation more of the year's records name.
7. Anything still undecided is a conflict: the check fails and lists it, and a recorded decision settles it.

Rule 6b needs, per login, year and mail domain, the number of commits. `collected/` doesn't hold commit addresses today, and counting must run from repository data alone (no clones in CI). *(my call)* A collector writes them to a new yearly file in `collected/` (login, domain, commits; domains only, no full addresses).

A year with no counting organisation is Unmapped, as today.

### events and community data

Each kind is one file in `curated/community/` *(folder name my call)*, with a year column or an event reference. Source references are source ids (a semicolon cell where there are several); community rows need no snippets *(my call)*, because the row itself is the reading.

- **event**: `id, kind, name, start, end, location, level, sources, notes`.
  `kind`: `conference` (the global Plone Conference, one a year), `symposium` (local or regional events, several a year), `wpd` (World Plone Day; one event per location, several a year), `sprint`. `level` holds the sprint level (`strategic` …), empty for other kinds *(my call)*.
- **talk**: `id, event, type, title, speakers, organisations, video, sources, notes`. `type`: keynote, talk, panel, full stream …. `speakers` are person ids; `organisations` holds a team the programme names instead of people (the existing rule). Today's `conference-talks` and `world-plone-day-talks` merge here; the old `scope` column goes, because the event's kind says it.
- **training**: `id, event, title, trainers, sources, notes`.
- **organiser**: `event, person, organisation, sources, notes`, exactly one of `person` and `organisation` set; one row per organiser, as many as the source names. An organisation is listed only when the source names it as organiser. Sponsors don't count and are not stored as organisers; a venue that only hosts isn't an organiser either (the existing rule). Replaces `plone-conference.csv` and the `organisers`/`organisations` cells of sprints and World Plone Day.
  **Organiser credit (rule change, decided by Jens):** an organisation gets credit for an event when the source names it directly, and also through an organiser person, by the organisation that person counts for in the event's year (computed, never stored). An organisation reached both ways gets credit once. Today only the stored organisations earn an event's recognition points; this change moves points (for example strategic sprints of 2012–2016 that name only people). *(my call)* It lands in its own PR after the mechanical migration, so the migration keeps the numbers identical. That PR also removes the organisations of the 2020 and 2021 conference rows that were taken "from the organisation mapping", not from the source; they come back through the organiser persons.
- **roles**: `board-of-directors` (`year, person, role, sources, notes`), `team-leaders` (`year, person, team, …`), `release-managers` (`year, person, …`), `podcasts` (`year, series, person, episodes, …`): one file each, the year as a column.
- `curated/plips/plone-plips-before-github.csv`, `bot_accounts.csv`, `excluded_repositories.csv`, `organisations.csv`: unchanged, except that a `source` column holding URLs becomes source ids *(my call)*.

## Capture tools

A reusable package, for example `scripts/tools/capture/` *(name my call)*, used by people, agents and the evidence tools alike:

- `capture <url> [--quote …]` returns the id of the existing source if the URL is known, and otherwise fetches it once, keeps the raw download in the local cache, writes the source row, and adds the passage around each given quote to the excerpt file. A known source is never fetched again while its raw copy is cached, unless asked explicitly (`--refresh`).
- Adapters by site, with a generic fallback, turn the raw download into readable text from which passages are cut:
  generic HTML: main-content extraction (trafilatura or readability) to drop header, menu, footer and ads;
  Wayback: fetch the raw capture with the `id_` URL form (`web.archive.org/web/<timestamp>id_/<url>`), which drops the toolbar and is lighter on their servers;
  Volto sites (plone.org, recent ploneconf.org): `++api++` JSON;
  GitHub profiles and commits: the API, or the local clones in `.cache/repositories` for commits;
  PDFs: pdftotext; videos: captions via yt-dlp; sched.org: its own adapter.
- The raw download is kept in a local gitignored cache (`.cache/sources/`, shared by the worktrees of one checkout), so a new quote or better extraction later works without fetching again.
- Safeguard: a quote the tool can't find in the extracted text is searched in the raw text too (extraction may have cut a sidebar bio); if it's still missing, the tool reports it instead of storing a passage.
- Politeness: a descriptive User-Agent, at most about 15 requests a minute to web.archive.org *(my call, tunable)*, retries with back-off, resumable runs.
- Live pages that change (GitHub profiles, plone.org and Foundation member pages) are captured as they are when captured; the source's `date` is the capture date *(my call)*. Where today's text no longer contains a migrated quote, the mismatch baseline lists it. For a dead URL cited without an archive copy, the tool asks the Wayback availability API once for the nearest capture and otherwise marks the source unreachable.
- Tests: offline, with recorded fixtures per adapter.

## Checks (new or changed)

- Every source row has an excerpt file and every excerpt file a row; no two sources share a canonical URL (and capture date).
- Every non-empty snippet appears in its source's excerpt.
- Every affiliation that counts has at least one citation; a `decision` citation's source has `kind = decision`.
- Two decisions covering the same person and year: the later one names the earlier one in `supersedes`, else the check fails (no reviewed decision is overruled by accident).
- Counting has no unresolved conflict (rule 6).
- Organiser rows have exactly one of person and organisation; talks and trainings point to existing events.
- The existing checks (sorting, ids, set cells, Frictionless schemas) carry over.

## Migration

One scripted step that moves everything without human decisions, then a reviewed step for what needs judgement. Human decisions are needed only where information conflicts and can't be resolved from the sources.

1. **Capture.** Collect all distinct URLs from curated data; capture each once with the capture tools (about 1,600 Wayback captures, rate-limited; about 400 commits from the local clones; the rest live pages and profiles). The excerpt of each source holds the passages around the quotes that cite it; for citations without a quote, the passages that name the person (any of their name identities) or the organisation. The 58 GitHub search URLs are replaced by the commits they found. Unreachable sources keep a row and are reported.
2. **Mechanical conversion.** Split every `source` cell into sources and citations: each URL becomes a source id; a quoted passage before it becomes the snippet; labels and our own wording go to the citation's `notes`. Existing affiliation rows keep their ranges; "not verified" rows become `assumed`; rejected proposals become `denied` rows citing the PR comment as a decision. `notes` are kept verbatim. People's `github` becomes an identity. Community files merge into one file per kind; events are created from the event names, sprint rows and World Plone Day rows.
   Acceptance: `derived/` and `reports/` regenerate with identical numbers, byte-identically except for provenance (*(my call)*: in `derived/community-page.json` each contribution names its curated file, line and raw source text; after the merge it names the new file and row and lists its sources' URLs, and the site's "data" link points there); an old-vs-new comparison shows every URL and every quote of the old data in the new data, per person.
3. **Reviewed restructuring.** Turn the evidence that lives in `notes` prose into rows: "not applied" conflicting records into stated affiliations; Jens's recorded tie-breaks (#153, #171 …) into decision sources; "SVN user …" into identities. Every conflict the new counting can't resolve is listed for Jens; each answer is recorded as a decision with a public record. Reports may change here only where a listed decision changes them.

*(my call)* Steps 1–2 are one PR, step 3 one or more reviewed PRs. Whether step 1 goes in its own PR because of its size is left to the builder.

## Documentation

Rewrite the parts of `docs/` that describe the registers, the community data, the attribution rules (including the organiser credit, in its PR) and the how-tos (`add-an-affiliation`, `add-curated-community-data`, the curated-files reference generated from the schemas) for the new structure; add a how-to for capturing a source and one for recording a decision. Update `AGENTS.md` (layout, mapping files) and the folder READMEs.

## Left to the builder

- Exact file and folder names, and the id scheme for sources, events, talks, trainings and affiliations, within the constraints above.
- The excerpt format details (front matter or not, how passages are separated, how much context around a quote, how a commit or profile is rendered).
- Which extraction library, and the adapter boundaries.
- How the model API exposes the new tables, as long as `derive/` and `report/` keep producing identical output after the mechanical migration.
- How to split the work into PRs beyond the order above.
