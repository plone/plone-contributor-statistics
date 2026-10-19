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
Entries in person columns that are groups, such as a team or an organisation, don't count as people; they count for their organisation.

Code work identifies people by their GitHub login, but most community roles name a person without a login.
A person is matched to their login where the data links the two: a login column, a link to the person's GitHub profile in the source of a row that names only them, the commit author mapping, or the name mapping in `curated/mappings/mapping-github-username-to-fullname.csv`, which links names to logins with public records.
A person without such a link counts by name, so someone who did both code and community work without a recorded link can still be counted twice ([#117](https://github.com/plone/plone-contributor-statistics/issues/117)).

## Organisations active

An organisation is active in a period if its people did code work in it, as the organisation statistics attribute it, or if it is named in community work or as an event organiser.
Unmapped contributors, self-employed people (`Name (independent)`) and `Plone Foundation (community volunteer)` are not counted as organisations.

## Events

Events are the gatherings the curated data records:

-   the Plone Conference, one per year;
-   sprints, one per recorded sprint, strategic or community, and before 2011 without a level;
-   World Plone Day, one per year, with its organising organisations ([#118](https://github.com/plone/plone-contributor-statistics/issues/118)).

Trainings are sessions at the conference, not events of their own.
Meetups join the count once they are recorded; the list of event kinds is `EVENT_RULES` in `scripts/lib/community.py`.

## Recognition levels

The wall shows every organisation with a recognition level, grouped by level.
The levels come from `scripts/report/generate_community_recognition_report.py` for the last completed year.
They can differ from the levels published on plone.org in August 2026, see {doc}`community-recognition`.

For each organisation, the page lists its points per category and the contributions behind them.
Each contribution links to its row in the data and to its public record; rows without a public record yet are marked as pending ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).
Points for pull requests add up the yearly organisation statistics of five years, so they link to the organisation's row in each of those files, one link per year.

For each organisation, a small graph shows its yearly counts since 2003 in four areas: commits and merged pull requests, as the organisation statistics attribute them; community roles, one per person and role in the curated community data; and events it organised.
These are counts, not points: points exist only for the recognition years.

## People

The page doesn't list people in a ranking.
It lets you search for one person, by GitHub login or by name, and shows for a year where they stand in commits and in merged pull requests among the people with at least one, and which community roles they held.
A name finds the person's login where the data links the two, see "People active" above.
Without a search, the page shows how many people made one, two to nine, ten to 49, or 50 and more commits and merged pull requests in the year, without names.

## History

For each year since 2003, the page shows:

-   the number of people active, as defined above, in that year;
-   the commits and merged pull requests of the year, from the yearly contributor files; years without any merged pull request say so instead of showing zero, because Plone's work moved to pull requests on GitHub only around 2010;
-   the Board of Directors and the team leads, named, because these are public roles;
-   the events, as defined above, with their organisers and sources.
