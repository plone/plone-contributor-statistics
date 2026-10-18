(explanation-community-recognition)=

# About the Community Recognition Program

The Plone Foundation's Community Recognition Program gives organisations a level, such as Platinum or Gold, for their contributions to Plone.
The levels are published on plone.org, and many readers come to this repository to understand them.
This page explains what the repository holds for the program, how it calculates the levels, and why the published levels differ.

## The published levels

The Foundation published the first version of the levels in August 2026 on the [Community Recognition page](https://plone.org/foundation/community-recognition).
The page says that the data, the method and the points are in this repository.
The levels combine code contributions, PLIPs, and community work such as sprints, trainings, release management and the Board.

## What the repository holds

The program's inputs are here:

- `data/community-contributions/community-recognition-points.csv` lists the points per kind of contribution, how they are split, and the time window.
- `data/community-contributions/community-recognition-levels.csv` lists the levels and their point ranges.
- The {doc}`curated data <curated-community-data>` records the community work.
- The {doc}`organisation statistics <attribution>` and the PLIP files record the code contributions.

`generate_community_recognition_report.py` turns these inputs into points and levels per organisation.
It spells each organisation as in `organisations.csv`, so that different spellings in the inputs add up to one organisation.
Unmapped contributors get no points and no level ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).

Only the repositories of the `plone` GitHub organisation count.
The program recognises work on Plone itself, so an organisation's own repositories and the `collective` organisation stay out, even when they are built on Plone.

## How the script calculates

The script applies `data/community-contributions/community-recognition-points.csv` as it is written.
It looks at one recognition year: community work counts in that year, code in the five years up to and including it.

Most rules are a direct reading of the points file.
Where an event has several organisers, its points are split among them: a strategic sprint, a World Plone Day event, a conference, a training.
An organisation gets points for one strategic sprint per year at most.
Pull requests count as an average per year over the five years, from the yearly organisation files, so a person counts for the organisation of each year.

PLIPs count in the same way.
`plip_organisation_stats.py` gives each PLIP to its author's organisation in the year the PLIP was closed ([#95](https://github.com/plone/plone-contributor-statistics/issues/95)).
The points file asks for PLIPs that were merged and released, but the data only says whether a PLIP is closed.
So a closed PLIP counts as merged and released ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).

## Why the published levels differ

The levels published in August 2026 were not calculated in this repository ([#56](https://github.com/plone/plone-contributor-statistics/issues/56)).
Érico Andrei explained in [#28](https://github.com/plone/plone-contributor-statistics/pull/28#issuecomment-6235721046) that the report came from a fork, and that it couldn't be merged back, because fixing the mappings had needed personal data that doesn't belong in a public repository.
He suggested to archive this repository, to keep the ranking calculation in a new one, and to make id.plone.org and plone.org the source of truth for the data.

A reconstruction on the data of that time comes close to the published levels.
It uses the same windows as the script, but gives each organiser of a strategic sprint the full points instead of a share.
It also needs some decisions that were made on the published page itself:
Nuclia's record went to Iskra, Érico Andrei counted for both kitconcept and Simples Consultoria, and the Interlegis Program and PloneGov-BR were merged.

Since then, the organisation mapping was corrected with public records, see {doc}`attribution` and {doc}`history-and-coverage`.
Those corrections move code contributions between organisations, so the script's levels on today's data differ from the published ones for some organisations.
Read the published levels as the Foundation's decision of August 2026, and the script's levels as what the points file gives on the current data.

## Open work

Two pieces of work wait for input from Mikel Larreategi (erral):

- A weighting of contributions by year ([#34](https://github.com/plone/plone-contributor-statistics/pull/34)).
- A split into separate code and community recognition, discussed at the Beethoven Sprint 2026 (branch `split-code-and-community-contributions`).

Open questions about the inputs include how to count the Steering Circle ([#45](https://github.com/plone/plone-contributor-statistics/issues/45)) and the check of the 2025 community data against the Board minutes ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).

The PLIP level scripts `generate_plip_3tier_levels.py` and `analyze_plip_contributor_levels.py` are left over from the proposals that are now in `archive/`.
They are not part of the program.

```{seealso}
{doc}`/reference/recognition-files` describes the columns of the recognition files.
```
