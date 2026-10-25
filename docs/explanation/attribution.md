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

## Registers, sources and citations

The registers in `curated/mappings/` record who people are and which organisations they belonged to.
`curated/mappings/people.csv` has one row per person, with an opaque id and the name the person is published under, and `curated/mappings/organisations.csv` one row per organisation.
`curated/mappings/identities.csv` holds the strings that denote a person in the data, each of a kind:

- `github`: the GitHub login that the collected files count the person under, at most one per person.
- `github-alias`: a further GitHub account of the person, counted for the same person.
- `email`: a commit address that GitHub links to no account.
- `name`: a spelling of the name, such as a changelog nickname. A person without a GitHub account has their name as an identity of this kind, citing the record of the name.

`curated/mappings/affiliations.csv` has one row per person, organisation and period, with the first and the last year and a status.

The evidence is kept apart from the rows that read it.
The source register in `curated/sources/` holds every page, profile, commit, video or decision that a row rests on, each with an excerpt file of the passages we cite, see {doc}`/how-to/capture-a-source`.
`curated/mappings/citations.csv` links each affiliation to its sources, one row per source and passage, with the words of the source that support the affiliation as its snippet.
A snippet is verbatim: `make check` finds it in the excerpt of its source, so a reader sees what the record says without opening the page, and still after the page is gone.
An identity cites its source the same way, in its own `source` and `snippet` columns.
The notes of a citation or identity say in our words what the source shows, and keep the quotes that the excerpt doesn't hold.
A row never loses a source: new evidence is a new citation, and an old one stays.

## The status of an affiliation

An affiliation is a reading of its sources, and its status says what kind of reading it is:

- `stated`: the sources say that the person belonged to the organisation in those years.
- `assumed`: the row extends a range beyond its records, such as today's organisation for the years before the first record. It counts only in years that no stated row covers and no bridge fills, unless a decision chooses it in a year that the rules leave open, and its notes say what it rests on. When the registers were introduced, today's organisation was kept for every year of a person's activity; those rows are assumed until a record dates them.
- `denied`: the person did not belong to the organisation in those years. A denied row removes its organisation from its years, whatever other rows say, and its notes give the reason. A reviewer writes it when a proposal turns out wrong, citing where it was decided, so that the tools don't propose those years again.
- `proposed`: a tool or a contributor read the sources this way, and nobody has reviewed it yet. A proposed row never counts. A reviewer turns it into a stated or an assumed row, or into a denied one.

## An affiliation covers years

The organisation of a person in a year is computed from the affiliations that cover the year, by the rules in the next section.
There is no default.
A year that no row covers is Unmapped.
Today's organisation is a row with an empty last year, so it runs up to the present, and a row for a past organisation is a row like any other.
`Unmapped` is never written as an organisation, because a gap in the rows says the same.
A person who changed organisations has one row for each, and the organisation statistics, which are built year by year, count the person for the old organisation in the old years and for the new one in the new years ([#16](https://github.com/plone/plone-contributor-statistics/issues/16)).
Multi-year summaries add up the years, so such a person appears under both organisations.

The rows of one person may overlap.
Two public records can name different organisations for the same year, when a person works for two at once, or when a record of the year of a change names the new organisation.
Each record is a row of its own, and the rules decide which organisation the year counts for.
The records that do not decide the year stay cited, so that nobody has to research them again.

Two records of the same organisation also cover the years between them, when no record names another organisation in between: a person named on a company's team page in two years was not elsewhere in the years between, however many they are.
This is a convention: the statistics are built by year, and a year has one organisation per person.
It is computed, by rule 5 below, and needs no row of its own: a stated row of another organisation or a denied row of the same one in between breaks the bridge, while an assumed row or a note doesn't.
A period that begins and ends within one year doesn't appear at all.

A biography that names an employer for a conference year is an affiliation row for that year, with the biography as its record.
It is then also evidence for the commits of that year, as signatures and participant lists are.
Rows exist only where someone knew about the affiliation and recorded it.
For the early years especially, many affiliations are unknown, and {doc}`history-and-coverage` explains what follows from that.

(explanation-attribution-rules)=

## How the year is decided

For each person and year, the rules below are applied in this order, and the first one that leaves a single organisation decides.
Recorded facts and the rules come first: proposals are ignored and denials remove their organisation, then the rules decide where they can, and a decision settles only what they leave open.
The statistics, the community page and `python -m scripts.tools.affiliation` all compute the organisation this way, see {ref}`how-to-add-an-affiliation-check`.

1.  **Proposals and denials.**
    Proposed rows are ignored.
    A denied row removes its organisation from its years.
    A denied row without an organisation, which would record a reviewed "stays Unmapped", is not used here.
2.  **Stated over assumed.**
    Where stated rows cover the year, or a bridge fills it (rule 5), the assumed rows drop out of the rules below.
3.  **One organisation.**
    If one organisation is left, it counts.
4.  **Change year.**
    When a person changes organisation during a year, the whole year counts for the organisation the person leaves, and the new affiliation starts with the following year.
    Of two organisations, the one that also covers the year before and not the year after counts, when the other covers the year after and not the year before.
    A record dated in the year of the change may therefore name the new organisation without changing how the year is counted.
5.  **Bridging.**
    Two years covered by stated rows of an organisation cover the years between them for it, when no stated row of another organisation covers any of them and no denied row of the organisation does, however many years they are.
    The bridged years count as stated years of the organisation, for rules 2 to 4 and 6 as well.
    Assumed rows neither start, end nor break a bridge, and notes never stop one.
6.  **Tie-breaks**, among the organisations that are left, in this order:

    6a. Named first
    : Where one record names two organisations for the same time, the first one counts.
      When the rows of all of them cite the same source with a snippet, the organisation whose snippet comes first in its excerpt counts, and when one sentence names them all, the one whose name or alias comes first in it.
      When the shared sources name different organisations first, this rule doesn't decide.

    6b. Commits
    : The year goes to the organisation whose address most of the person's commits of that year carry, because the commits are what the statistics count.
      This holds when the commits under the addresses of the organisations in question outnumber those under personal addresses; commits under other addresses are left out.
      A domain of the person's own, such as one with their name, is personal, unless an organisation of the register claims it.

    6c. Own statement
    : When the commits of the organisations in question do not outnumber the personal ones, the year follows the person's own public statement of that year, a speaker page or profile dated in the year, if the statements name exactly one of the organisations.
      This holds also when there are no commits of the person to weigh.
      A speaker listing says whom the person worked on Plone for, more than a mail signature or an old address does.

    6d. Records
    : Otherwise the organisation that more distinct sources dated in the year name counts.

    Rules 6b and 6c read the commits that the collected files count under the person's username: the `github` login, or `person:<id>` for a person without one, whose commits the collected files count by the commit addresses.
    A source that could not be captured has no passage, and only the day of the attempt as its date, so rules 6c and 6d leave it out.
    A source is dated as {doc}`/how-to/capture-a-source` says: a placeholder date on a page doesn't count, and a conference page is dated by the conference.
7.  **Decision.**
    When the rules leave the year open, a reviewer can decide in public: the decision is a public comment, by a maintainer, by someone else, or by the person or the organisation in question.
    Older decisions sit in comments on pull requests and issues of this repository.
    The comment is captured as a source of the kind `decision`, and the row it chooses cites it.
    The latest decision for a person and year counts, by the date of its source.
    A decision settles only what the rules leave open: for a year that the rules decide, it is not applied, it is outdated, because facts recorded since then decide the year.
    `python -m scripts.tools.decisions_review` lists the decisions with this status and the sources dated after each of them.
    A decision that overrules an earlier one for the same person and year names it in the `supersedes` column of its citation; `make check` fails when it doesn't, so that no decision is overruled by accident.
    A decision that a denied row cites takes no part in this rule, because the denial already removes its organisation.
8.  **Conflict.**
    Otherwise the year is an open case: it counts as Unmapped until a decision settles it.
    `make check` prints a warning that names the person, the year and the organisations, and `python -m scripts.tools.decisions_review` lists the open cases next to the decisions.
    An open case is a warning, not an error, because the year is known to be undecided.

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
Acceptable sources are public records, captured into the source register: a public profile, a company website, an archived page, a register entry, a conference speaker biography, a public participant list of a community sprint, the signature of the person's message on a public mailing list, or a confirmation by the person in public, such as a comment on a GitHub issue or pull request.
A participant list is evidence only for the year of the sprint.
A signature is evidence for the year of the message, and so is the company address that the message was sent from, because both were written at the time.
A personal website is no employer, and a link to it says nothing about one; but what the person writes there about an employer or their own business is evidence for the time it was written.
A confirmation that exists only in private doesn't count, because nobody else can check it.
A company email address in the person's commits is evidence for the years in which the person used it, but only in commits made in Git, see {doc}`history-and-coverage`.
An address can outlive the employment, as an old mailbox: where a dated record names another organisation for the same years, such as the person's own business on its own or an alliance's page, the record counts, and the address only documents the mailbox.
The address never becomes a stated row: a proposal from it becomes a `denied` row with the reason in its notes, so the tools don't propose those years again.
The tool described in {ref}`find-affiliations-in-commit-addresses` proposes such affiliations.
Commits in the repositories of an organisation's own GitHub organisation are evidence of the same kind for that organisation in the year of the commits.
The tool described in {ref}`find-affiliations-in-the-github-commit-search` finds both kinds in the GitHub commit search, for the years that assumed rows only guess.
Personal domains, project addresses, such as plone.org, and the domain of an alliance of companies, such as the BlueDynamics Alliance, say nothing about an employer.
A programme such as Google Summer of Code is not an employer.
When in doubt, a contributor stays Unmapped.

Many corrections come from the people themselves, by pull request, with a link or a short confirmation.
This keeps the mapping close to what people would say about their own work.
{doc}`/how-to/add-an-affiliation` shows how to send one.

## Small mistakes are caught by checks

A register is easy to get wrong.
A single typo in a login used to send a contributor's whole activity to Unmapped, and with it part of an organisation's numbers ([#38](https://github.com/plone/plone-contributor-statistics/issues/38)).
Now every file has a schema, and `make check` validates it.
The checks say the file, the row and the column of an error: an id that no register has, a name that differs from another only in case or accents, an affiliation without a citation, or a snippet that the excerpt of its source doesn't hold.
They also compute the organisation of every person and year, and warn about each year that no rule decides, and name each decision that overrules an earlier one without naming it.
Every change still goes through review.

```{seealso}
{ref}`reference-curated-files` describes the format and the checks of the registers.
```
