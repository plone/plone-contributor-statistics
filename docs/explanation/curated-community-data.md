(explanation-curated-community-data)=

# Collected and curated data

Most of the data in this repository is collected: a script asks an API, and the answer is the data.
Some of it is curated: people compile it by hand from public sources and check every row.
This page explains why both kinds exist and why curated data follows stricter rules.

## Work that leaves no trace in code

Conferences, sprints, trainings, release management and team leadership are central to Plone.
No API records them in a form that a script could count.
So the statistics keep records of them in `curated/community/`, one file per kind with the rows of every year.

Rows of the current year are added as soon as they have a public record, such as a sprint report or the Board page of the new term.
The year stays incomplete until it ends, and the community page and the recognition only use it once the year is completed.

## Events and the records that point to them

An event is a gathering, one row of `curated/community/events.csv`.
Its `kind` says what it is:

- `conference`: the Plone Conference of a year;
- `symposium`: a regional conference, such as the Plone Tagung, the symposia or PloneConf Brasil;
- `wpd`: a World Plone Day event of one place, held in person, hybrid or online, or the online edition of a year;
- `sprint`: a sprint, with its `level` where the Board gave it one.

Every event has an id that is chosen once and never renamed, such as `plone-conference-2025`, `wpd-2025-04-10-bologna-italy` or `beethoven-sprint-2026`.
The talks, the trainings and the organisers are files of their own, and each row points to its event by that id:

- `curated/community/talks.csv` holds the talks of the conferences and the symposia, and the videos of World Plone Day.
  A World Plone Day talk points to the event of its place, and a talk of the online edition to `wpd-<year>-online`; `location` keeps where the talk was given, as the record named it.
- `curated/community/trainings.csv` holds the trainings of a conference or a symposium.
- `curated/community/organisers.csv` holds the organisers of an event, one row per person or organisation, with exactly one of the two.

The roles are tied to a year, not to an event: `curated/community/board-of-directors.csv`, `curated/community/team-leaders.csv`, `curated/community/release-managers.csv` and `curated/community/podcasts.csv` have one row per person and year, with the year in their `year` column.
The folder also holds the recognition files, `curated/community/community-recognition-points.csv` and `curated/community/community-recognition-levels.csv`, see {doc}`/reference/recognition-files`.

## Recorded is not counted

The files record more than the community page and the recognition count.
What counts, and for how many points, is decided by the Board and the Marketing Team; this project prepares the data and shows it, see {doc}`community-recognition`.
Today:

- World Plone Day events held online, and the online edition of a year, are recorded, so that their talks have an event, but count nowhere as events: the community page doesn't list them, and they earn no points.
  The talks given there are World Plone Day talks like any other.
- A person who organised a World Plone Day event is recorded, but counts neither as a role on the community page nor for points; the organisations of the event count.
- Trainings at a symposium are recorded, but only the trainings of the Plone Conference count.
- Conference talks count on the community page: their speakers are active people, and a team that gave one is an active organisation.
  They earn no recognition points.

## The order of a year's rows

The rows of a year keep their order in the files, and so do the organisers of an event.
The order decides which records count where the points have a limit: of the strategic sprints of a year, the first one that names an organisation counts for it, with that sprint's split, and only the first four World Plone Day talks of an organisation in a year count.
This is how the recognition has always read the rows, not a new rule, see {doc}`community-recognition`.
So add a new row after the rows of its year, a talk, a training or an organiser after the rows of the events of its year, and don't sort or reorder the rows of a year.

## People by id, organisations only for entities

A curated row refers to a person by their id in `curated/mappings/people.csv`, never by a name.
A person column holds one id.
A set column holds several ids separated by semicolons, but only where the elements have no attributes of their own: the trainers of a training and the speakers of a talk.
Where an element needs an attribute, such as the episodes of a host, the team of a leader or the role of a Board member, the file has one row per person.
The organisers of an event are rows of their own, so that each one cites its own source.

The organisation of a person is not written in the row.
The statistics take it from the {doc}`affiliations <attribution>` for the year of the row or of its event.
An organisation column holds the id of an organising entity that the source names, such as the company team that gave a talk or an organisation that held an event.
A group in a person column is not allowed: a company team goes into an organisation column, and a community or a role goes into `notes`.
A person or an organisation that the registers don't have yet is added to them first, see {doc}`/how-to/add-a-person`.
The format and the checks of every file are in {ref}`reference-curated-files`.

## No data without a source

Curated data is only as trustworthy as its sources.
Every row needs a public source: a page on plone.org, the minutes of the Foundation Board, a conference website, or an archived copy in the Wayback Machine.
The source is captured into the source register `curated/sources/sources.csv` first, with the passages we cite, see {doc}`/how-to/capture-a-source`.
The row cites it by its id in `sources`, and `cited_as` says in words what the row cites: the addresses, with their labels and quotes.
The community page shows `cited_as` as the record of the row and links its addresses.
The rows that came from the yearly files before the source register keep their old source cell verbatim in `cited_as`.
Unlike an affiliation, a community row has no snippets: the row itself is what the source says.

The sources of a row are the record for the row only.
The record for the organisation of a person belongs to an affiliation row; a biography that names it for the year is a source there, see {doc}`attribution`.
A memory counts as a source when people who took part confirm it in public, for example in a comment on the pull request.

Two events of a year may have no source: the Plone Conference of a year, `plone-conference-<year>`, and the online edition of World Plone Day, `wpd-<year>-online`.
They hold the talks, trainings and organisers that point to them, and those rows cite their sources.

Rows that no source supports are removed, even if they were probably right.
An unsourced row can't be checked, and it can't be corrected by someone who remembers it differently.

## Definitions come from the Foundation

Several kinds of curated data depend on a definition, and the definitions follow the Plone Foundation:

- A Board member is anyone the Board page of the term lists as a director or an officer, such as the treasurer, the secretary or the executive director, with or without a vote; advisory seats don't count.
- A strategic sprint is a sprint that the Board designated as strategic, that a team declared strategic under the Board's procedure, or that the Foundation funded, as recorded in the Board minutes.
  A sprint that the Board funded at the community level, or called not strategic, is a community sprint.
  The events file lists all known sprints, and says which were strategic.
- A release manager is someone approved by the Board or listed on the Release Team page.
- A team leader is someone named as the team's lead in the Board minutes or on the team's page, or who represented the team at the Steering Circle, the meeting of the team leads.
  A team can have several leaders in a year.
  Board committees such as the IP or Trademark Committee, programmes such as Google Summer of Code, and the Release Team, whose release managers count on their own, are not teams in this sense.
- An appointment by the Board counts until a source records a successor or an end.
- A podcast or live series counts for a year with at least five episodes in that year, split among its hosts; every series is recorded, also with fewer episodes.
- A World Plone Day talk is a video of the type `Talk`; teasers, streams, openings and podcast episodes are recorded, but are not talks.
  A full stream doesn't count when its parts are published as talks of their own.
  Only people speak: a talk counts for the organisations of its speakers, which the affiliations give for the year.
  What the talk itself says about a speaker's organisation, in the title or description of the video or on the event page, is an affiliation row for that year.
  A role in the Foundation or a community such as PloneGov-BR is not a speaker's organisation.
  A talk that names a company team instead of people has the team in its `organisations` column, and a talk that names no speaker and no team counts for no organisation.
- A conference talk is a keynote, a talk or a panel in the programme of a Plone conference: the annual Plone Conference, an event of the kind `conference`, or a regional conference such as the Plone Tagung, the symposia or PloneConf Brasil, an event of the kind `symposium`.
  World Plone Day is not a conference, and sprints and meetups are not; a tutorial is a training; lightning-talk sessions, one recording with many short talks, are not recorded for now.
  Only people speak: a talk that the programme attributes to a team instead of people names the team in its `organisations` column.
  What the speaker page, the bio or the speaker in the recording says about their organisation is an affiliation row for that year, with the page or the recording and its timestamp as the source; the talk row carries no organisation of the speaker.
  Talks are shown, in the person card of the community page, and not counted: they earn no recognition points until the Marketing Team or the Board decides otherwise.
- Work is attributed to the people who did it and their organisations, not to the Plone Foundation.
- PloneGov-BR and the Interlegis Program are not the same.
  PloneGov-BR is the community of practice of Plone users in the Brazilian public sector; it organises the events in Brasília.
  The Interlegis Program of the Federal Senate is an employer and one of PloneGov-BR's founding members; its staff count for Interlegis in their personal roles, such as Board seats and talks, while public bodies that host an event are its venue, not its organiser ([ILB annual report 2023](https://www12.senado.leg.br/interlegis/relatorios-ilb/relatorio-ilb-2023.pdf), p. 22).
  When the Foundation organised the online conferences of 2020 and 2021, the organisers are the people who did the organising work, found in the Board minutes and announcements.
- World Plone Day events count when they were held in person, or hybrid with an in-person meeting.
  Each local event is one event, with its own source; events held online, and the online edition of a year, an event of the format `online`, are recorded, but count nowhere as events.
  The organisers are the organisations that held the event, not the venue that hosted it.
  An event that was announced, but that no report confirms, is recorded with the note "announced, no report found"; reports after the event were not usual in the early years.
- A training is a session that the conference programme calls a training or a tutorial, including the tutorials in the talk programme of the early conferences, which had no separate training days.
  Trainings that the trainers organised and charged for themselves count too, when the conference announced them as its trainings.
  A training counts once, also when it has several parts or was given more than once; a training that a source records as cancelled or replaced, or that is missing from the room schedule, doesn't count.
  At a joint conference, only the Plone trainings count.
  Trainings at a symposium are recorded, but don't count.
  Where a trainer's bio names two organisations, the first one counts in the affiliation.

## The rules for sprints changed over time

Plone sprints are older than the Foundation's rules for them.
The first sprint took place in Bern in February 2003, and many followed without any designation.

The Board first discussed strategic sprints in 2009 and 2010, and funded the first one in 2011.
From late 2012, it budgeted strategic sprints, proposed by the teams, next to community sprints at a much lower level ([minutes of November 29, 2012](https://plone.org/foundation/meetings/minutes/2012/minutes-for-november-29-2012)).
The sponsorship policy said from 2013 that what counts as strategic "is in general decided by the various teams within the community" ([policy page of 2013](https://web.archive.org/web/20130211040131/http://plone.org/foundation/event-sponsorship/plone-event-sponsorship-policy)).
From December 2021, the Board graded the funding by size, from community to small, large and mega sprints ([minutes of December 9, 2021](https://plone.org/foundation/meetings/minutes/2021/plone-foundation-board-minutes-december-9-2021)).
Since March 2025, a sprint must serve the roadmap by shipping PLIPs to get funding at all ([minutes of March 6, 2025](https://plone.org/foundation/meetings/minutes/2025/plone-foundation-board-minutes-march-6-2025)).

So a sprint before 2011 has no level, and from 2011 on the level follows the rules of its time.

## Why scripts don't fetch curated data

Some curated data could be scraped, for example the trainings from a conference website.
The repository deliberately has no scripts for that ([#30](https://github.com/plone/plone-contributor-statistics/pull/30)).
A website lists what was announced, not what took place, and it doesn't know who sponsored a trainer's time.
Every run of such a script would overwrite the corrections that people made by hand.

The Board of Directors data followed the same path: a script used to read it from plone.org and guessed the organisations from the members' biographies.
It is curated now, with the Board page of each term as the source.

## Curated data reaches back further

The organising organisations of every Plone Conference since 2003 are recorded.
The rows from 2003 to 2019 also name the organisers and a source.
Board members, release managers and team leaders are recorded with sources from 2004 on ([#94](https://github.com/plone/plone-contributor-statistics/pull/94), [#99](https://github.com/plone/plone-contributor-statistics/pull/99), [#113](https://github.com/plone/plone-contributor-statistics/pull/113)).
Sprints are recorded from the first one in 2003, and the local World Plone Day events from the first World Plone Day in 2008.
Trainings are recorded from the first conference in 2003; podcasts start in 2020.
Collecting their earlier years needs sources that are hard to find, and people who remember ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).

```{seealso}
{doc}`/how-to/add-curated-community-data` shows how to add or correct curated data.
```
