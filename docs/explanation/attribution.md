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

## Today's organisation, with exceptions for the past

`organisations.csv` lists the current organisation of each account.
Most people stay with one organisation for the years in which they contribute, so one file covers most of the history.

When someone changed organisations, `organisation_mapping_overrides.csv` records the earlier one for the years it applied ([#16](https://github.com/plone/plone-contributor-statistics/issues/16)).
The organisation statistics are built year by year, and each year uses the overrides that apply to it.
A person who moved is therefore counted for the old organisation in the old years and for the new one in the new years.
Multi-year summaries add up the years, so such a person appears under both organisations.

Overrides exist only where someone knew about the change and recorded it.

Without an override, today's organisation applies to every year, also to years before the organisation existed.
An override with the organisation `Unmapped` prevents that: it marks the years in which a person's affiliation isn't documented, for example the years before their company was founded.
Their work in those years then counts as Unmapped, as the rule "when in doubt, Unmapped" asks.
For the early years especially, many past affiliations are unknown, and {doc}`history-and-coverage` explains what follows from that.

## Unmapped is not an organisation

An account without an entry is Unmapped.
Unmapped and independent contributors are two different groups ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).
Independent contributors are mapped: they chose to contribute on their own, and their entries say so.
Unmapped contributors are not mapped yet, and their affiliation is simply unknown.
Counted together, they would look like one big organisation that doesn't exist.

Unmapped is shown on its own line below the organisations, is not ranked among them, and gets no recognition points or level.
People without a GitHub account, who are counted under their name, are Unmapped too, because the mapping lists GitHub logins.

## A mapping needs a source

The mapping says something about real people and real organisations, so it needs evidence.
Acceptable sources are public records: a public profile, a company website, an archived page, a register entry, a conference speaker biography, or a confirmation by the person in public, such as a comment on a GitHub issue or pull request.
A confirmation that exists only in private doesn't count, because nobody else can check it.
A company email address in the person's commits is evidence for the years in which the person used it, but only in commits made in Git, see {doc}`history-and-coverage`.
Personal domains and project addresses, such as plone.org, say nothing about an employer.
When in doubt, a contributor stays Unmapped.

Many corrections come from the people themselves, by pull request, with a link or a short confirmation.
This keeps the mapping close to what people would say about their own work.
{doc}`/how-to/correct-an-organisation-mapping` shows how to send one.

## Small mistakes have large effects

A mapping file is easy to get wrong.
A single typo in a login sends a contributor's whole activity to Unmapped, and with it part of an organisation's numbers ([#38](https://github.com/plone/plone-contributor-statistics/issues/38)).
Logins are also case-sensitive in the lookup.
Format tests check every login in the mapping files, and every change goes through review.

```{seealso}
{doc}`/reference/mapping-files` describes the format and rules of the mapping files.
```
