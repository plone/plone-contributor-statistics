---
myst:
  html_meta:
    "description": "What the numbers on the generated Plone community page mean, and how they are counted."
    "property=og:description": "What the numbers on the generated Plone community page mean, and how they are counted."
    "property=og:title": "The community page"
---

(explanation-community-page)=

# The community page

The community page shows who builds Plone: how many people and organisations are active, which events took place, and every organisation with a community recognition level.
It is generated from the committed data of this repository; every number on it comes from `derived/community-page.json`, which `scripts/derive/community_page.py` writes.
This page explains what the numbers mean.

## Periods

The page shows the last completed year, and the five years up to and including it.
These are the years of the community recognition, see {doc}`community-recognition`.
The number of people since 2003 is a secondary line.

## People active

A person is active in a period if they did code work or community work in it.

-   Code work is a commit or a merged pull request in the yearly contributor files, see {doc}`counting-rules`.
-   Community work is a role or contribution in the curated community data: Board member, team lead, release manager, conference organiser, trainer, World Plone Day talk, sprint organiser, or podcast host, see {doc}`curated-community-data`.

Unmapped people and self-employed people count.
Entries in person columns that are groups, such as a team, don't count.

Code work identifies people by their GitHub login, but most community roles name a person without a login.
A person is matched to their login where the data links the two: a login column, a link to the person's GitHub profile in the source, the commit author mapping, or the name mapping.
A person without such a link counts by name, so someone who did both code and community work can be counted twice ([#117](https://github.com/plone/plone-contributor-statistics/issues/117)).

## Organisations active

An organisation is active in a period if its people did code work in it, as the organisation statistics attribute it, or if it is named in community work or as an event organiser.
Unmapped contributors and self-employed people (`Name (independent)`) are not counted as organisations.

## Events

Events are the gatherings the curated data records:

-   the Plone Conference, one per year;
-   strategic sprints, one per sprint name;
-   World Plone Day, one per year, with its organising organisations ([#118](https://github.com/plone/plone-contributor-statistics/issues/118)).

Trainings are sessions at the conference, not events of their own.
Community sprints and meetups join the count once they are recorded; the list of event kinds is `EVENT_RULES` in `scripts/lib/community.py`.

## Recognition levels

The wall shows every organisation with a recognition level, grouped by level.
The levels come from `scripts/report/generate_community_recognition_report.py` for the last completed year.
They can differ from the levels published on plone.org in August 2026, see {doc}`community-recognition`.

For each organisation, the page lists its points per category and the contributions behind them.
Each contribution links to its row in the data and to its public record; rows without a public record yet are marked as pending ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).

## People

The page doesn't list people in a ranking.
It lets you search for one person, and shows for a year where they stand in commits and in merged pull requests, and which community roles they held.
