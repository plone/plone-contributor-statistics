# Migration of the notes to data, 2026-10-26

Plan 5, "From notes to data": what the notes of `curated/mappings/affiliations.csv` and `identities.csv` said in prose became rows, and the attribution rules (`docs/explanation/attribution.md`) compute what the notes only wrote down.
The method is documented in `docs/`, the design and the plan are in `archive/specs-and-plans/2026-10-25-notes-to-data-design.md` and `2026-10-25-notes-to-data-plan.md`.
The code ran in the commits named below, with the data it changed; it is archived unchanged except for the removal of the decision drafts, which the open cases made obsolete.
The archived tests are not run: pytest collects only `tests/`.

## Files

- `migrate_notes.py`: the three steps `fills`, `svn` and `conflicts` (`python -m scripts.tools.migrate_notes <step> [--write]` while it lived in `scripts/tools/`).
- `corrections.py`: two corrections after the steps (below).
- `tests/test_migrate_notes.py`: its offline tests.
- `dated-2019.txt`: the 92 sources of 2019.ploneconf.org that carried the placeholder date 2000-01-01 (or an archive date) and got the date of the conference, with their old dates and addresses.
- `source-date-conflicts.tsv`: the follow-up list, below.

## What ran

1. `fills` (commit `4b4947b`): the rows that only wrote down a bridge between two records of one organisation (notes "between records of A and B of the same organisation") were removed, because the rules bridge the years themselves.
   132 fill rows removed.
   Their notes moved to the nearer record as `bridged <from>-<to>: <note>`, 187 citations were accounted for, and 3 citations that no neighbour cited moved to the record that keeps the evidence.
   Fill rows that a record of another organisation or a denied row stands between were kept.
   The list of the removed rows is the difference to `4b4947b~1`.
2. `svn` (commit `26d5cca`): the Subversion users named in the notes of 25 identities became 20 identities of kind `svn`, one per person and user (two of Paul Everitt: `paul`, `zopepaul`), each citing the source of the first identity it was found on.
3. `conflicts` (commits `80e1a69`, `05b6b7d`, `c71dc36`): the records of another organisation that nine notes "not applied, the verified row stands" and "Kept, not deciding" named became ten stated rows, from nine records, each citing its source, and the old notes got "the record is row <id>".
   "ClearWind" is noted as an abbreviation of Clearwind Consulting.
4. The date corrections (commits `cd2d46e`, `376809e`): 93 source dates.
   The 92 pages of 2019.ploneconf.org with the placeholder date 2000-01-01 got the first day of the conference, 2019-10-21, as the captured front page `70669bc437fd` states it.
   The 2011 talk page `65f4cad3f712` that names Adaptive Path got the date the page shows, 2011-11-04, instead of its archive date.
   A 2019 archived copy of Ramon Navarro Bosch's speaker page was captured as `d35a5ea5b514`.
5. `corrections.py`, 2026-10-26:
   `earlier-review` prefixed the notes of the 16 rows that carry the old review texts (the nine verified rows and the rows written from their records) with "earlier review: ", the text kept verbatim.
   `checked` appended " (checked YYYY-MM-DD)" after the moved "bridged ..." fragment of each of the 132 removed fill rows, which all had a checked date, on 126 neighbour rows.

The rules changed in the same plan: bridging is computed, rule 6c lets the person's own statement decide when the commits decide nothing, and a year that no rule decides is an open case, a warning.

## Result

Bridging was accepted by Jens before the data steps: 347 person-years (49 of them active) are bridged by the documented rule and counted before as well, by the fill rows.
The steps 1 and 2 changed no counting (`python -m scripts.tools.attribution_changes --all-years` listed 0 changes).
Step 3 and rule 6c changed 8 active person-years, all accepted by Jens:

- alan-runyan 2003: Clear Noodle to Runyaga, LLC (own statement)
- andy-mckay 2003: AGM Web consulting to Clearwind Consulting (own statement)
- j-cameron-cooper 2003: J Cameron Cooper (independent) to Rice University (own statement)
- jodok-batlogg 2005: Telesis to solution2u.net GmbH (own statement)
- mikko-ohtamaa 2011: Red Innovation Oy to mFabrik (change year)
- p-j-onori 2011: Adaptive Path to Unmapped: an open case, no decision
- ramon-navarro-bosch 2020: Nuclia to Iskra (own statement)
- rob-gietema 2024: kitconcept GmbH to Rob Gietema (independent) (own statement)

The open case of P.J. Onori 2011 (Adaptive Path or Seabright) counts as Unmapped until a public decision settles it; `make check` warns and `python -m scripts.tools.decisions_review` lists it.

## Follow-up

`source-date-conflicts.tsv` lists the sources whose date is the archive copy's but whose page shows another year (368 sources, 168 of them cited by affiliations), with the columns id, date, page shows, number of affiliations that cite it, and address.
The rules read these dates for rules 6c and 6d, so they are worth a review of their own.
Two more sources carry a placeholder date and need one: `2f4dd4b922cb` and `ee15d109fadb`.
