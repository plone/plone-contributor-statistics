(explanation-curated-community-data)=

# Collected and curated data

Most of the data in this repository is collected: a script asks an API, and the answer is the data.
Some of it is curated: people compile it by hand from public sources and check every row.
This page explains why both kinds exist and why curated data follows stricter rules.

## Work that leaves no trace in code

Conferences, sprints, trainings, release management and team leadership are central to Plone.
No API records them in a form that a script could count.
So the statistics keep lists of them, one file per year and kind, in `curated/community-contributions/`.

Files of the current year are started as soon as the first rows have a public record, such as a sprint report or the Board page of the new term.
They stay incomplete until the year ends, and the community page and the recognition only use them once the year is completed.

## People by id, organisations only for entities

A curated row refers to a person by their id in `curated/mappings/people.csv`, never by a name.
A person column holds one id.
A set column holds several ids separated by semicolons, but only where the elements have no attributes of their own: the trainers of a training, the speakers of a talk, and the organisers of a sprint, a conference or an event.
Where an element needs an attribute, such as the episodes of a host, the team of a leader or the role of a Board member, the kind has one row per person.

The organisation of a person is not written in the row.
The statistics take it from the {doc}`affiliations <attribution>` for the year of the file.
An organisation column holds the ids of organising entities that the source names, such as the company team that gave a talk or the organisations that held an event.
A group in a person column is not allowed: a company team goes into an organisation column, and a community or a role goes into `notes`.
A person or an organisation that the registers don't have yet is added to them first, see {doc}`/how-to/add-a-person`.
The format and the checks of every kind are in {ref}`reference-curated-files`.

## No data without a source

Curated data is only as trustworthy as its sources.
Every row needs a public source: a page on plone.org, the minutes of the Foundation Board, a conference website, or an archived copy in the Wayback Machine.
The `source` of a row holds the record for the row only.
The record for the organisation of a person belongs to an affiliation row; a biography that names it for the year is a source there, see {doc}`attribution`.
A memory counts as a source when people who took part confirm it in public, for example in a comment on the pull request.

Rows that no source supports are removed, even if they were probably right.
An unsourced row can't be checked, and it can't be corrected by someone who remembers it differently.

## Definitions come from the Foundation

Several kinds of curated data depend on a definition, and the definitions follow the Plone Foundation:

- A Board member is anyone the Board page of the term lists as a director or an officer, such as the treasurer, the secretary or the executive director, with or without a vote; advisory seats don't count.
- A strategic sprint is a sprint that the Board designated as strategic, that a team declared strategic under the Board's procedure, or that the Foundation funded, as recorded in the Board minutes.
  A sprint that the Board funded at the community level, or called not strategic, is a community sprint.
  The sprint files list all known sprints, and say which were strategic.
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
- A conference talk is a keynote, a talk or a panel in the programme of a Plone conference: the annual Plone Conference, with the scope `global`, or a regional conference such as the Plone Tagung, the symposia or PloneConf Brasil, with the scope `regional`.
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
  Each local event is one event, with its own source; online editions are recorded, but don't count.
  The organisers are the organisations that held the event, not the venue that hosted it.
  An event that was announced, but that no report confirms, is recorded with the note "announced, no report found"; reports after the event were not usual in the early years.
- A training is a session that the conference programme calls a training or a tutorial, including the tutorials in the talk programme of the early conferences, which had no separate training days.
  Trainings that the trainers organised and charged for themselves count too, when the conference announced them as its trainings.
  A training counts once, also when it has several parts or was given more than once; a training that a source records as cancelled or replaced, or that is missing from the room schedule, doesn't count.
  At a joint conference, only the Plone trainings count.
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

The Board of Directors files followed the same path: a script used to read them from plone.org and guessed the organisations from the members' biographies.
They are curated now, with the Board page of each term as the source.

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
