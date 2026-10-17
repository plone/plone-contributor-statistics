(explanation-community-recognition)=

# About the Community Recognition Program

The Plone Foundation's Community Recognition Program gives organisations a level, such as Platinum or Gold, for their contributions to Plone.
The levels are published on plone.org, and many readers come to this repository to understand them.
This page explains what the repository holds for the program, and what it can't explain yet.

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
Unmapped contributors get no points and no level ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).

## The published levels can't be reproduced yet

The published levels don't follow from the script and data in the repository ([#56](https://github.com/plone/plone-contributor-statistics/issues/56)).
The pull request counts on the page match the organisation files of that time, but the levels don't.
The likely reason is that the final version of the calculation was never committed.

The script and the points file also disagree with each other:

- The script gives 6 points per training, the points file 4.
- The script gives each organiser of a strategic sprint the full points, the points file splits them among the organisers.
- The script gives each organiser of a World Plone Day event the full points, the points file splits them.
- The script counts PLIPs over all years, the points file over the past five years, and only those merged and released ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).
- The script uses only the community data of 2025.

Until this is resolved, read the levels as the Foundation's published result, not as something this repository computes.
This page doesn't explain how the published levels were calculated, because the repository can't show it.

## Open work

The original authors were asked to commit the version that produced the published page.
Two pieces of work wait for input from Mikel Larreategi (erral):

- A weighting of contributions by year ([#34](https://github.com/plone/plone-contributor-statistics/pull/34)).
- A split into separate code and community recognition, discussed at the Beethoven Sprint 2026 (branch `split-code-and-community-contributions`).

Open questions about the inputs include how to count the Steering Circle ([#45](https://github.com/plone/plone-contributor-statistics/issues/45)) and the check of the 2025 community data against the Board minutes ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).

The PLIP level scripts `generate_plip_3tier_levels.py` and `analyze_plip_contributor_levels.py` are left over from earlier proposals, now in `archive/`.
They are not part of the program.

When the calculation is in the repository, this page will describe it.

```{seealso}
{doc}`/reference/recognition-files` describes the columns of the recognition files.
```
