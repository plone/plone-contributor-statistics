(explanation-curated-community-data)=

# Collected and curated data

Most of the data in this repository is collected: a script asks an API, and the answer is the data.
Some of it is curated: people compile it by hand from public sources and check every row.
This page explains why both kinds exist and why curated data follows stricter rules.

## Work that leaves no trace in code

Conferences, sprints, trainings, release management and team leadership are central to Plone.
No API records them in a form that a script could count.
So the statistics keep lists of them, one file per year and kind, in `curated/community-contributions/`.

## No data without a source

Curated data is only as trustworthy as its sources.
Every row needs a public source: a page on plone.org, the minutes of the Foundation Board, a conference website, or an archived copy in the Wayback Machine.
Where a source names only people, the organisation comes from the {doc}`organisation mapping <attribution>` for that year, and the row says so.
A memory counts as a source when people who took part confirm it in public, for example in a comment on the pull request.

Organisations are spelled as in `curated/mappings/organisations.csv`; for the files of the current recognition year, a format check makes sure of it.

Rows that no source supports are removed, even if they were probably right.
An unsourced row can't be checked, and it can't be corrected by someone who remembers it differently.
Some files don't have a source column yet, such as the 2025 files and the podcast hosts, and they are being checked against sources ([#46](https://github.com/plone/plone-contributor-statistics/issues/46)).

## Definitions come from the Foundation

Several kinds of curated data depend on a definition, and the definitions follow the Plone Foundation:

- A Board member is anyone the Board page of the term lists as a director or an officer, such as the treasurer, the secretary or the executive director, with or without a vote; advisory seats don't count.
- A strategic sprint is a sprint that the Board designated as strategic, as recorded in the Board minutes.
- A release manager is someone approved by the Board or listed on the Release Team page.
- A team leader is someone named as the team's lead in the Board minutes or on the team's page, or who represented the team at the Steering Circle, the meeting of the team leads.
  A team can have several leaders in a year.
  Board committees such as the IP or Trademark Committee, programmes such as Google Summer of Code, and the Release Team, whose release managers count on their own, are not teams in this sense.
- An appointment by the Board counts until a source records a successor or an end.
- World Plone Day events count when they were held in person.

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
Other curated data starts in 2020.
Collecting the earlier years needs sources that are hard to find, and people who remember ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).

```{seealso}
{doc}`/how-to/add-curated-community-data` shows how to add or correct curated data.
```
