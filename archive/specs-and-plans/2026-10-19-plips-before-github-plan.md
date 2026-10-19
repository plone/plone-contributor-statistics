# Plan: record the PLIPs from before GitHub

Refs #14.

## Research

- Collect the PLIPs from before the move to GitHub issues from public records: the wiki pages under plone.org/development/plips (2004–2005), the plone.org roadmap (products/plone/roadmap/N), the Trac tickets and reports on dev.plone.org, the plips folder of buildout.coredev, the changelog of Products.CMFPlone and the plone-developers list, all through the Wayback Machine where the pages are gone.
- Per PLIP: number, title, proposer, implementers, state, proposed and completed dates, release, a quote, the source, and notes.

## Decisions (Jens Klein)

- Record them in one curated file, `curated/plips/plone-plips-before-github.csv`.
- Keep the rows where a roadmap PLIP and a Trac ticket are the same PLIP; mark the pair in `Same as`.
- Record first: no script counts the file, neither the PLIP statistics nor the recognition.

## Build

- `Numbering` is `roadmap` (wiki and roadmap share one numbering) or `trac`.
- Names and logins as the source gives them, separated by semicolons.
- State as the source gives it, at the date of the archived copy.

## Code, tests and docs

- `scripts/lib/paths.py`: `PLIPS_BEFORE_GITHUB`.
- `tests/test_plips_before_github_format.py`: columns, one sourced row per PLIP, `Same as` points back.
- `docs/reference/data-files.md`, `docs/reference/data-sources.md`, `docs/explanation/history-and-coverage.md`, `docs/explanation/known-limitations.md`, `curated/README.md`.
