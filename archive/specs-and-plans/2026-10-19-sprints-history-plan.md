# Plan: all Plone sprints 2003–2025, with their level

Part of #72 and #86, decided by Jens Klein in the review.

## Goal

- One file per year, `curated/community-contributions/YYYY-sprints.csv`, with all known Plone sprints, including Zope sprints with Plone people.
- Columns: `Sprint`, `Start`, `End`, `Location`, `Organiser(s)`, `Organisation`, `Level`, `Source`, `Notes`.
- `Level` is `strategic` or `community` where the Board decided on the sprint; the strategic sprints of the recognition come from there.
  The old `YYYY-strategic-sprints.csv` files are replaced.

## Rules

- A sprint counts if a public source shows that it took place, or announces it with date and place; announcement-only sprints get the note "announced, no report found".
- Plone Tune-Ups (bug days), cancelled sprints, proposals that never happened and preparation meetings stay out.
- Before 2011 no sprint has a level: strategic sprints did not exist yet.
- From 2011 on, a sprint is strategic if the Board designated it, a team declared it strategic under the Board's procedure, or the Foundation funded it; funding at the community level, or a sprint called not strategic, makes it a community sprint.
- The funding rules changed over time; the docs describe their history with the sources.
- Sorrento sprints are called Plone Open Garden, their official name.
- Organisations as the source states them, spelled as in `organisations.csv`; otherwise the organisers' organisations from the mapping of the year; otherwise Unmapped.

## Steps

1. Collect the sprints of 2003–2010, 2011–2019 and 2020–2025 with a quote and URL each.
2. Check the Board decision on every sprint from 2011 on in the minutes, and the funding guidelines of each era.
3. Merge, apply the rules, add new organisations to `organisations.csv`.
4. Switch the recognition script to the new files, update the tests and docs, regenerate, and compare the 2025 recognition.
