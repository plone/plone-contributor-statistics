# Plan: World Plone Day events 2008 to 2019

Refs #72, #118.

## Research

- Collect every local World Plone Day event from the first edition in November 2008 to 2020 from public records: the plone.org event and host pages and their Wayback Machine captures, the 2008 registration wiki on openplans.org, the yearly host listings, plonegov.it, colab.interlegis.leg.br, community.plone.org and the Board minutes.
- Per event: date, location, format, organisations as written, the people named as organisers with their role, venue, a quote, the source, and notes.
- Venues, hosts that only give the room, and sponsors are not organisers.

## Decisions (Jens Klein)

- Add the organisations that are new to `curated/mappings/organisations.csv`, with an empty team.
- Include the events that were announced but have no report, with the note "announced, no report found": reports after the event were not usual then.

## Build

- One file per year, `curated/community-contributions/YYYY-world-plone-day-event.csv`, in the existing format.
- Spell organisations as in `organisations.csv`; variants of one organisation get one spelling; BlueDynamics Alliance is an alliance, not an organisation.
- Where a page names only people, the organisation comes from the organisation mapping of the year, or the Board page of the year, and `Source` cites it; otherwise `Unmapped`.
- `Notes` name the organisers and the venue.
- No file for 2020: the research found no local event of that year.

## Docs

- Coverage in `docs/reference/data-sources.md`, `docs/explanation/curated-community-data.md`, `docs/explanation/history-and-coverage.md`, `docs/explanation/known-limitations.md`; the `Notes` column in `docs/reference/data-files.md`; the events of the community page in `docs/explanation/community-page.md`.
