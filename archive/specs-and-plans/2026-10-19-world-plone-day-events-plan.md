# Plan: one row per local World Plone Day event (#118)

Decided by Jens Klein in the review.

## Format

`curated/community-contributions/YYYY-world-plone-day-event.csv`: `Date`, `Location`, `Format`, `Organisation`, `Source`, `Notes`.
One row per local event, with its own source.
`Format` is `in person`, `hybrid` or `online`.

## Rules

- Only events held in person, or hybrid with an in-person meeting, count for the recognition and as events on the community page.
- Online editions are recorded, but don't count.
- The organisers are the organisations that held the event; venues and hosts are not organisers.
- Where the source names only people, the organisation comes from the organisation mapping of the year, and the row cites it.
- Events that no source shows as held in person stay out until a record turns up.
- The points stay as in the points file: 3 per event, split among its organising organisations.

## Steps

1. Research every local event of 2021–2025 with its source, and check the existing rows.
2. Write the files, add new organisations.
3. Count only in-person and hybrid events in the recognition script and on the community page.
4. Update tests and docs, regenerate, and compare the 2025 recognition.
