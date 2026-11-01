# PLIPs on the community page: design

Date: 2026-11-01
Status: draft for review

## Intent

Issue #104 asks how to bring back the PLIP report: `reports/plips.md` was archived because its generator was never in the repository.
PR #189 adds that old generator, `generate_plip_report.py`, unchanged in the repository root.
It cannot run on the current layout (wrong paths, an `organisations.csv` format that no longer exists), it counts PLIPs by the year they were opened, open ones included, against the rule of #95, it ignores the affiliations by year, and it writes a timestamp, so its output is never reproducible.

The maintainers decided not to bring back a Markdown report.
The PLIPs go where the rest of the data is shown: on the community page, generated from `derived/community-page.json`, linked to their public records, and counted with the same rule as the recognition points.
What Timo Stollenwerk wanted from `plips.md`, an overview of which PLIPs happened and from which organisations, comes from a new PLIP block per year in the History tab, without a ranking.

Today PLIPs appear on the page only as the recognition category "PLIP Contributions" of an organisation, one line such as "Significant PLIP Contributor (34 PLIPs)", without the PLIPs behind the number.
A person's card shows no PLIPs at all.

## Goals

- A person's card in the People search lists the PLIPs the person proposed that were closed in the card's year, each linked to its GitHub issue.
- An organisation's category "PLIP Contributions" lists the PLIPs behind its count, each linked.
- Each year in the History tab lists the PLIPs closed in that year, grouped by organisation.
- All three use one counting: the PLIPs of `collected/plips/plone-plips-detailed.csv` that are closed, in the year of closing, for the organisation the affiliations give the author in that year (#95). A closed PLIP stands in for a merged and released one (#14).
- The list behind an organisation's points and the number in its contribution text come from the same computation, so they cannot differ.
- PR #189 is replaced: it is closed with a comment that points to this work, and #104 is closed by its pull request.

## Non-goals

- A Markdown report of PLIPs, and rankings of people or organisations by PLIPs.
- Open PLIPs. They are not shown anywhere on the page.
- The PLIPs from before GitHub (`curated/plips/plone-plips-before-github.csv`). They stay recorded and uncounted, as `docs/explanation/known-limitations.md` says.
- Changing which PLIPs count, the points, or the levels. Whether only merged and released PLIPs should count is #14, a separate decision.
- A PLIP series in the organisation's yearly graph.
- `derived/plone-plip-organisations.csv` and `make run-plip-organisations` stay as they are.

## Anti-goals

The work fails, even if it technically works, when:

- A person's name or login appears in the visible page outside the person card. The page lists no people by name except the Board and the team leads (`test_people_are_not_listed_in_the_html`). The lists in the Organisations and History tabs show no author; whoever wants to know follows the link to the issue.
- The list of an organisation's PLIPs and the count in its points disagree.
- The page clutters: the PLIPs must read as compact, scannable lists, not walls of text.
- The derived data stops being deterministic.

## Decided with the maintainers

### Person card (People tab)

A new row after "Community roles" and before "Talks", shown only when the person has PLIPs in the year.

- Label: "PLIPs (n)". Not "PLIPs closed": that reads as if the person closed them.
- The card's existing note line says what the row means: "PLIPs: proposed by them and closed in <year>."
- Grouped by project, the project named once per group, then each PLIP as its title, linked to the issue, followed by its number in small grey type, separated by " · ":

  ```
  PLIPs (6)   volto   Vitest #6326 · Complete removal of Semantic UI from Volto #6323 · …
              aurora  React Router 7 #2
              plone.restapi  Behaviors implementation #641
  ```

- The groups by size, largest first, ties by project name; within a group by number, highest first.
- No author on the card: it is the person's own card.

### Organisation entry (Organisations tab)

In the category "PLIP Contributions", below the contribution line ("Significant PLIP Contributor (34 PLIPs)", its points and its "data" link, which stay), the PLIPs behind it:

- Grouped by year of closing, newest first, each group with its count.
- Each PLIP: title linked to the issue, then a short reference in small grey type: the repository name without `plone/`, `#`, the number, e.g. `volto#6396`.
- No author.
- An organisation with fewer than two PLIPs has no points in the category, so no category and no list, as today.

### History tab

Each year gets a block "PLIPs" after "Events" and before "Board of Directors", shown only when the year has PLIPs; the year's summary line adds " · n PLIPs" when there are any.

- All PLIPs closed in the year, grouped by the author's organisation of that year.
- Groups in alphabetical order (case-insensitive), no ranking; PLIPs without an organisation in a last group labelled "no organisation recorded".
- Each PLIP as on the organisation entry: title linked, grey reference `volto#6326`, no author.
- Every group with its count.
- The groups carry the organisation's name as the register has it, self-employed people included, such as "Name (independent)", and the Plone Foundation; they are organisation names, as on the wall and among the event organisers, not author lines. How people without a company are named, e.g. "Name (self-employed)" or "Name (private)" when no commercial connection is known, is a separate question for its own issue, not part of this work.

### Activity

A PLIP closed in a year makes its author active in that year, as code work does:

- The person counts among "people active" of the year, in the headline and in History, and has a card for the year; the card's paging stops at that year.
- Of the 240 PLIPs closed up to 2025, 13 person-years have no commits or merged pull requests besides the PLIP, so the counts of people active rise slightly.
- The page covers 2003 up to the recognition year (`data.year`); PLIPs closed later, such as those of 2026, are not shown until the page moves to that year (builder check, my call: the page's years stay as they are).

## Constraints

- Every number on the page comes from `derived/community-page.json`, written by `scripts/derive/community_page.py`; `scripts/report/community_page.py` and the templates only render it. The person card is drawn by `scripts/report/site/static/site.js` from the embedded people data.
- The data must stay deterministic: sorted lists, no timestamps (`tests/test_reproducible_outputs.py`).
- A PLIP author is resolved like code work: `code_key` gives the registered person's id, else the login in lower case; the organisation comes from the registry for the login and year, as `plip_organisation_stats.organisation_lookup` does.
- No external assets on the page; the links go to the GitHub issues (`html_url` in the PLIP file).
- Offline pytest tests for the new data and the rendering; the docs updated in the same pull request: `docs/explanation/community-page.md` (People active, Organisations active, Recognition levels, People, History) and an entry in `docs/explanation/method-history.md`, since the definition of people active changes.
- The design and the plan are added unchanged to `archive/specs-and-plans/` as the last step before the pull request.
- The pull request ends with `Assisted-by:` lines naming the models, no `Co-Authored-By`.

## Left to the builder

- The exact JSON shape of the PLIPs in `community-page.json` (per person, per organisation, per history year), as long as the template and the script need no counting of their own beyond grouping for display, and the names of the fields.
- How the recognition computation hands its PLIP groups to the page data, so that list and count share one computation.
- Whether the grouping for display happens in Python or in the template and script.
- The CSS for the grouped lists, within the page's existing style.
- Whether "organisations active" counts an organisation through its people's PLIPs (my call: yes, for consistency with people active; it rarely changes anything, since such an organisation nearly always has code work too).
- The project label: the repository name without `plone/` (`volto`, `aurora`, `plone.restapi`, `Products.CMFPlone`), my call.
