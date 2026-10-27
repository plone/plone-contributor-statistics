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

- `curated/community/community-recognition-points.csv` lists the points per kind of contribution, how they are split, and the time window.
- `curated/community/community-recognition-levels.csv` lists the levels and their point ranges.
- The {doc}`curated data <curated-community-data>` records the community work.
- The {doc}`organisation statistics <attribution>` and the PLIP files record the code contributions.

`scripts/report/generate_community_recognition_report.py` turns these inputs into points and levels per organisation.
It names each organisation by its name in `curated/mappings/organisations.csv`; the curated data and the affiliations refer to it by its id, so every record of an organisation adds up.
Unmapped contributors get no points and no level ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).
Independent contributors are mapped, to an organisation of the kind `independent`, and get points and a level like any other organisation.

Only the repositories of the `plone` GitHub organisation count.
The program recognises work on Plone itself, so an organisation's own repositories and the `collective` organisation stay out, even when they are built on Plone.

## How the script calculates

The script follows `curated/community/community-recognition-points.csv`, with the points written into its code; it doesn't read the file.
It looks at one recognition year: community work counts in that year, code in the five years up to and including it.

Most rules are a direct reading of the points file.
Where an event has several organisers, its points are split among them: a strategic sprint, a World Plone Day event, a conference.
A training's points are split among its trainers, each share going to the trainer's organisation.
The points of an organised event go to the organisations among its organisers in `curated/community/organisers.csv`.
A person among the organisers of a sprint or of the Plone Conference counts as a role on the community page, Sprint organiser or Conference organiser, and not for points; a person who organised a World Plone Day event is recorded, and counts for neither.
An organisation gets points for one strategic sprint per year at most, and for four World Plone Day talks per year at most.
Only World Plone Day events held in person or hybrid count, and only the trainings of the Plone Conference.
Pull requests count as an average per year over the five years, from the yearly organisation files, so a person counts for the organisation of each year.

In three places the script differs from the points file ([#56](https://github.com/plone/plone-contributor-statistics/issues/56)):

- Community sprints get no points: only sprints of the level `strategic` do, although the points file lists points for organising a community sprint.
- A team's 6 points are split among all its leaders, each share going to the leader's organisation, where the points file gives 6 points per leader and allows one leader per team. The script doesn't check that the team meets every month and publishes its minutes.
- A podcast or live series counts through each host with at least five episodes in the year: `episodes` is counted per host, and the points of the series are split among the hosts who reach five. A host with fewer episodes gets no share, even when the series has five or more, where the points file asks for five episodes of the series.

PLIPs count in the same way.
`scripts/derive/plip_organisation_stats.py` gives each PLIP to its author's organisation in the year the PLIP was closed ([#95](https://github.com/plone/plone-contributor-statistics/issues/95)).
The points file asks for PLIPs that were merged and released, but the data only says whether a PLIP is closed.
So a closed PLIP counts as merged and released ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).

The order of the rows decides which ones count where the points have a limit.
Of the strategic sprints of a year, the first one in `curated/community/events.csv` that names an organisation counts for it, with that sprint's split.
Of the World Plone Day talks of an organisation in a year, the first four in `curated/community/talks.csv` count.
The script has always read the rows this way: when the community data moved from one file per year and kind to one file per kind, the rows of each year kept their order.
Reordering the rows of a year can change the points.

What counts, and for how many points, is decided by the Board and the Marketing Team.
This repository prepares the data and shows what the points file gives on it; it doesn't decide on credit.

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

An open question about the inputs is the check of the 2025 community data against the Board minutes ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).

The PLIP level scripts left over from earlier proposals are in `archive/`, in the folder `plip-levels/`.
They are not part of the program.

```{seealso}
{doc}`/reference/recognition-files` describes the columns of the recognition files.
```
