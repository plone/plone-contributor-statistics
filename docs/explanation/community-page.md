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
-   Community work is a role or contribution in the curated community data: Board member, team lead, release manager, conference organiser, trainer, conference talk, World Plone Day talk, sprint organiser, or podcast host, see {doc}`curated-community-data`.

Unmapped people and self-employed people count.
Groups, such as a team or an organisation, are not people: they are not in a person column, they count for their organisation.

Code work identifies people by their GitHub login, or by `person:<id>` for commit authors without an account, and community roles by their id in `curated/mappings/people.csv`.
The register joins the two: a login resolves to the person who has it as an identity of the kind `github` or `github-alias`.
A person counts once, however many roles and logins they have.
Someone who did both code and community work can be counted twice only while the register holds them as two people, or does not know the login of their code work ([#117](https://github.com/plone/plone-contributor-statistics/issues/117)); `python -m scripts.tools.unmatched_names` lists such people.

## Organisations active

An organisation is active in a period if its people did code work in it, as the organisation statistics attribute it, if its people held a community role, or if it is named as an organising entity.
A role counts for the organisation that the affiliations give the person for the year, an organiser role too.
A team talk, with an organisation instead of speakers, counts for that organisation.
Unmapped contributors, self-employed people (organisations of the kind `independent`) and the Plone Foundation (the kind `foundation`) are not counted as organisations.

## Events

Events are the gatherings of `curated/community/events.csv`, see {doc}`curated-community-data`.
The page counts:

-   the Plone Conference, one per year whose organisers are recorded;
-   sprints, one per recorded sprint, whether strategic, community or without a level;
-   World Plone Day, one per local event held in person or hybrid, with its organising organisations ([#118](https://github.com/plone/plone-contributor-statistics/issues/118)).

World Plone Day events held online, and the online edition of a year, are recorded, but are not counted as events; their talks are.
Symposia, the regional conferences, can be recorded as events of the kind `symposium`, with their talks; they are not counted as events.
Trainings are sessions at the conference, not events of their own.
Meetups join the count once they are recorded: they need a kind in the schema of `curated/community/events.csv` and a rule in `EVENT_RULES` in `scripts/lib/model/community.py`.

## Recognition levels

The wall shows every organisation with a recognition level, grouped by level.
The levels come from `scripts/report/generate_community_recognition_report.py` for the last completed year.
They can differ from the levels published on plone.org in August 2026, see {doc}`community-recognition`.

For each organisation, the page lists its points per category and the contributions behind them.
Each contribution links to its row in the data and to its public record; a curated row without a web address in its record would be marked as pending ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)), but the checks no longer let such a row in.
Points for pull requests add up the yearly organisation statistics of five years, so they link to the organisation's row in each of those files, one link per year.

For each organisation, a small graph shows its yearly counts since 2003 in four areas: commits and merged pull requests, as the organisation statistics attribute them; community roles, one per person and record in the curated community data, such as each talk or training, plus one per talk that names the organisation as a team; and events it organised.
These are counts, not points: points exist only for the recognition years.

## People

The page doesn't list people in a ranking.
It lets you search for one person, by GitHub login or by name, and shows for a year where they stand in commits and in merged pull requests among the people with at least one, which community roles they held, and which organisation their work of that year is attributed to.
The organisation is the one the affiliations give the person for the year, see {doc}`attribution`: an organisation with a recognition level links to its entry, and a year without an affiliation shows "none recorded", with a link to {doc}`/how-to/add-an-affiliation`.
The card also lists the person's talks of the year, at conferences and on World Plone Day, each title linked to its recording where one exists, with the event in brackets when they spoke at more than one; talks count as community work like any role, and conference talks earn no recognition points, see {doc}`curated-community-data`.
A name finds the person through the register, see "People active" above.
The card pages to the nearest earlier and later years in which the person was active, and says so when the chosen year isn't one of them.
Below the search, the page shows for the chosen year how many people made one, two to nine, ten to 49, or 50 and more merged pull requests, and the same for commits, without names.

## History

For each year since 2003, the page shows:

-   the number of people active, as defined above, in that year;
-   the commits and merged pull requests of the year, from the yearly contributor files; years without any merged pull request say so instead of showing zero, because Plone's work moved to pull requests on GitHub only around 2011, see {doc}`history-and-coverage`;
-   the Board of Directors and the team leads, named, because these are public roles;
-   the events, as defined above, with their organising organisations and sources.
