# Plan: Board of Directors 2004–2025 with sources

Part of #86: curated community data needs a public record for every row.

## Goal

- One `YYYY-board-of-directors.csv` per year from 2004 to 2025, with the columns `Name`, `Organisation`, `Source`.
- Year Y holds the Board whose term ends in Y, as before.

## Sources

- The Board page of each term on plone.org, `https://plone.org/foundation/board/<slug>`.
- 2004: the formation board page (May–September 2004).
- 2005: no current page covers the Board of September 2004 to September 2005.
  The Wayback copy of the Board page from April 2005 lists it, and the minutes of November and December 2004 confirm the attendance.

## Rules

- Only voting directors count, not non-voting officers such as the treasurer, the executive director or advisory seats.
- The organisation is taken as the page states it, spelled as in `organisations.csv`.
- "Independent" or "freelancer" becomes "<Name> (independent)", following #53.
- Where the page names no organisation, the organisation mapping for that person and year is used, and the row cites its source.
  Otherwise the row is Unmapped.
- Quaive is a product, not an organisation.
  Guido Stevens counts for Cosent, his company.

## Steps

1. Extract the members from all Board pages, with quotes that state the organisation.
2. Write the files and add new organisations to `organisations.csv` with empty teams.
3. Retire `fetch_board_members.py`.
   It guessed organisations without sources and would overwrite the curated files.
4. Add a format check, `tests/test_board_of_directors_format.py`.
5. Update the docs: data sources, data files, and the curated-data explanation.
6. Compare the community recognition report before and after the change: only sourced differences are allowed.
   The report itself is regenerated in a separate pull request, because it also picks up the earlier mapping changes.
