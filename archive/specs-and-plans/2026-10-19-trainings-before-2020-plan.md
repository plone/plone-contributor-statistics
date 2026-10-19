# Plan: Plone Conference trainings 2003 to 2019

Refs #66, #72.

## Research

- Collect the trainings and tutorials of every Plone Conference from 2003 to 2019 from public records: the plone.org conference pages, the archived conference websites, the speaker bios of the year, mailing-list announcements, the Board minutes, and the changelog of plone/training.
- Per training: title, trainers, GitHub logins where clearly identifiable, organisations as the source gives them, date, source, quote and notes.

## Decisions (Jens Klein)

1. Tutorials that the programme calls tutorials count as trainings, also in the talk programme of the early conferences; a talk that only calls itself a tutorial doesn't.
2. Trainings that the trainers organised and charged for themselves count, when the conference announced them.
3. 2012: the announced trainings count, with the note "announced, no report found"; the Board minutes say nine trainings filled the spots.
4. One row per training, also with several parts or repeated sessions; Hacking Plone 101–104 (2016) are four trainings.
5. Joint conference 2013: only the Plone trainings; "Geographic Information and Content Management" has no Plone in its summary and is left out.
6. 2010: "Theming Plone 4" and "XDV Tutorial" are missing from the room schedule and are left out.
7. 2016: where the overview and the training page name different trainers, both are listed, with a note.
8. A trainer whose bio names two organisations counts for the first one.

Cancelled or replaced trainings are left out.

## Build

- One file per year, in the existing format plus a `Notes` column.
- Organisations from the source; otherwise from the organisation mapping or the Board page of the year, cited in `Source`; otherwise `Unmapped`.
- New organisations are added to `organisations.csv` with an empty team.

## Docs

- Coverage in `docs/reference/data-sources.md`, `docs/explanation/curated-community-data.md`, `docs/explanation/history-and-coverage.md`, `docs/explanation/known-limitations.md`; the `Notes` column in `docs/reference/data-files.md`; the training rules in `docs/explanation/curated-community-data.md`.
