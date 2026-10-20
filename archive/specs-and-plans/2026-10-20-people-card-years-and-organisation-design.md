# Design: the person card pages through the years and names the organisation

Date: 2026-10-20
Repository: `plone/plone-contributor-statistics`
Builds on: `archive/specs-and-plans/2026-10-19-community-page-design.md` (the community page), `2026-10-19-data-structure-spec.md` (the registers and affiliations)

## 1. Intent

The People tab of the community page shows one person's card for one year: their place in commits and merged pull requests, and their community roles.
The maintainer asked for two things when looking at a card:

1. page through the years on the card itself, with left and right carets or whatever fits best, instead of going back to the year menu;
2. see which organisation the person's work is attributed to in that year.

Both serve reader 2 of the community page design, the curious community member looking at where they stand.
The second also makes the attribution visible to the people it concerns: someone who sees "none recorded" knows what to fix, and the footer already links to how.

## 2. Goals, non-goals, anti-goals

Goals

- From a card, reach the previous and the next year with one click, and keep paging.
- The card names the organisation the affiliations give the person for that year, the same attribution the organisation statistics use.
- No new data collection: the derive step adds one field it already knows.

Non-goals

- A list or chart of all the years a person was active (a possible follow-up).
- Changing the search, the year menu, or the anonymous distribution table.
- Keyboard shortcuts beyond the buttons themselves.

Anti-goals, from the community page design

- A ranked list of people's names.
- Showing "Unmapped" as if it were an organisation.

## 3. Decisions

### 3.1 Paging (my call, the maintainer left the control to me)

- Two buttons on the card, one on each side of its heading: `‹ 2023` on the left and `2026 ›` on the right.
- Each button jumps to the **nearest year in which the person was active**, in that direction, and its label says which year that is.
  Stepping one year at a time would show "not active" cards for every gap, and a person active in 2010 and 2025 would need fourteen clicks; a labelled jump makes the gap visible and costs one click.
- A button is disabled when there is no active year in its direction.
- The year menu is the single source of truth: a button sets the menu's year and re-renders, so the anonymous distribution table follows, as it does today.
- When the chosen year has no entry for a person the data knows (from the register's names, or from another year), the card says so, "Jane Doe wasn't active in 2020.", and still offers the two buttons.
  An unknown name keeps today's "Nobody with that GitHub login or name" message, without buttons.
- After a click, focus moves to the same button in the new card, so paging with the keyboard keeps working while the card is replaced.

### 3.2 The organisation of the year

- `scripts/derive/community_page.py` adds `organisation` to every entry of `people[<year>]`: `Registry.organisation_of(person, year)` for a registered person, `Unmapped` for a login outside the register.
  This is the same lookup `organisation_stats.py` uses for the code work, so the card and the organisation statistics agree.
- The card gets a row `Organisation`.
  - A name links to the organisation's entry in the Organisations tab when it has a recognition level; the page data for the search carries `organisations`, a map from name to slug, for that.
  - `Unmapped` shows as "none recorded", linked to the how-to on adding an affiliation (the footer's "Correct your organisation" target), through a `data-docs` attribute on the result element, so the script needs no knowledge of the docs URL.
  - Independent people and the foundation show their organisation name as the register spells it, as the History tab does.

### 3.3 Docs and tests

- `docs/explanation/community-page.md`, section People: the organisation row and what "none recorded" means, and the paging to the nearest active years.
- `docs/reference/data-files.md`: the per-person entries carry the organisation of the year.
- Offline tests: the derive step gives the affiliation of the year, Unmapped outside the register, and respects the years of an affiliation; the renderer embeds the organisation map and the docs attribute; the existing people tests gain the new field.
- The browser script has no test harness in the repository; it is checked by hand in a browser against the regenerated data.
- `derived/community-page.json` is regenerated, because the reproducibility test compares it with what the scripts make.

## 4. Left to the builder

- The exact wording of the card's "not active" sentence and the button labels.
- The styling of the buttons, within the page's look.
