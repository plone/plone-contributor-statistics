(explanation-attribution)=

# From a GitHub account to an organisation

GitHub knows accounts, not employers.
To say which organisations make Plone possible, the statistics need a second step: the organisation mapping.
This page explains how that mapping works, and why it is careful rather than complete.

## The organisation that sponsors the time

A contribution is attributed to the organisation that sponsors the contributor's time on Plone, in the year of the contribution.
That is usually the employer.
It can also be a client who pays for the work, or the person's own company.

The rule asks who made the work possible, not where someone happens to be employed.
A developer who works on Plone in their free time, while their employer has nothing to do with Plone, contributes as a private person.
Self-employed people and volunteers therefore have entries of their own, such as `Name (independent)`.
Self-employed people with a company name use that name.

## An affiliation covers years

The registers in `curated/mappings/` record who belongs to which organisation.
`curated/mappings/people.csv` has one row per person, `curated/mappings/organisations.csv` one row per organisation, and `curated/mappings/affiliations.csv` one row per person, organisation and period, with the first and the last year.
The organisation of a person in a year is the affiliation row that covers that year.

There is no default.
A year that no row covers is Unmapped.
Today's organisation is a row with an empty last year, so it runs up to the present, and a row for a past organisation is a row like any other.
`Unmapped` is never written as an organisation, because a gap in the rows says the same.
A person who changed organisations has one row for each, and the organisation statistics, which are built year by year, count the person for the old organisation in the old years and for the new one in the new years ([#16](https://github.com/plone/plone-contributor-statistics/issues/16)).
Multi-year summaries add up the years, so such a person appears under both organisations.

A biography that names an employer for a conference year is an affiliation row for that year, with the biography as its record.
It is then also evidence for the commits of that year, as signatures and participant lists are.
Rows exist only where someone knew about the affiliation and recorded it.
For the early years especially, many affiliations are unknown, and {doc}`history-and-coverage` explains what follows from that.

Statements that no accepted record confirms yet wait in `curated/mappings/affiliation_proposals.csv`.
No script reads it.
A reviewer checks each proposal and moves it into `curated/mappings/affiliations.csv` with its record, or leaves it out.

## Unmapped is not an organisation

A person without an affiliation row for a year is Unmapped in that year.
Unmapped and independent contributors are two different groups ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).
Independent contributors are mapped: they chose to contribute on their own, and their organisation has the kind `independent`.
Unmapped contributors are not mapped yet, and their affiliation is simply unknown.
Counted together, they would look like one big organisation that doesn't exist.

Unmapped is shown on its own line below the organisations, is not ranked among them, and gets no recognition points or level.
A commit or pull request under a login that the registers don't know is Unmapped too.
People without a GitHub account have a row in `curated/mappings/people.csv` like everyone else, and can have affiliations.

## A mapping needs a source

The mapping says something about real people and real organisations, so it needs evidence.
Acceptable sources are public records: a public profile, a company website, an archived page, a register entry, a conference speaker biography, a public participant list of a community sprint, the signature of the person's message on a public mailing list, or a confirmation by the person in public, such as a comment on a GitHub issue or pull request.
A participant list is evidence only for the year of the sprint.
A signature is evidence for the year of the message, and so is the company address that the message was sent from, because both were written at the time.
A personal website is no employer, and a link to it says nothing about one; but what the person writes there about an employer or their own business is evidence for the time it was written.
A confirmation that exists only in private doesn't count, because nobody else can check it.
A company email address in the person's commits is evidence for the years in which the person used it, but only in commits made in Git, see {doc}`history-and-coverage`.
Personal domains and project addresses, such as plone.org, say nothing about an employer.
A programme such as Google Summer of Code is not an employer.
Where one record names two organisations for the same time, the first one counts.
When in doubt, a contributor stays Unmapped.

Many corrections come from the people themselves, by pull request, with a link or a short confirmation.
This keeps the mapping close to what people would say about their own work.
{doc}`/how-to/add-an-affiliation` shows how to send one.

## Small mistakes are caught by checks

A register is easy to get wrong.
A single typo in a login used to send a contributor's whole activity to Unmapped, and with it part of an organisation's numbers ([#38](https://github.com/plone/plone-contributor-statistics/issues/38)).
Now every file has a schema, and `make check` validates it.
The checks say the file, the row and the column of an error: an id that no register has, an affiliation that overlaps another one of the same person, a name that differs from another only in case or accents, or a source without a link.
Every change still goes through review.

```{seealso}
{ref}`reference-curated-files` describes the format and the checks of the registers.
```
