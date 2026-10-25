---
myst:
  html_meta:
    "description": "Terms used in the Plone contributor statistics documentation."
    "property=og:description": "Terms used in the Plone contributor statistics documentation."
    "property=og:title": "Glossary"
---

(glossary)=

# Glossary

```{glossary}
affiliation
    A row of `curated/mappings/affiliations.csv`: a person belonged to an organisation from one year to another, as its {term}`citations <citation>` show.
    Its status is `stated`, `assumed`, `denied` or `proposed`.
    The organisation of a person in a year is computed from the affiliations that cover it, and a year that no affiliation covers is {term}`Unmapped`.

bot account
    A GitHub account that is not a person, such as a continuous integration bot or a GitHub App.
    GitHub Apps have a `[bot]` suffix.
    Bots that GitHub lists as users are named in `curated/mappings/bot_accounts.csv`.
    The statistics leave bot accounts out.

citation
    A row of `curated/mappings/citations.csv`: an {term}`affiliation` rests on a {term}`source`, with the {term}`snippet` of the source that supports it.

curated data
    Data that people collect and check by hand against a public source, as opposed to data that a script collects from an API.
    Curated data lives in `curated/`.

decision
    A public comment on an issue or pull request of this repository that says which organisation a year of a person counts for, where the records disagree.
    It is a {term}`source` of the kind `decision`, and the affiliation it chooses cites it.

default branch
    The main branch of a repository on GitHub, for example `main` or `master`.

event
    A gathering of the Plone community, one row of `curated/community/events.csv`, with an id that is chosen once and never renamed.
    Its {term}`event kind` says what it is.
    Talks, trainings and {term}`organisers <organiser>` point to it by its id.

event kind
    The `kind` of an {term}`event`: `conference` for the Plone Conference of a year, `symposium` for a regional conference, `wpd` for a World Plone Day event of one place or the online edition of a year, and `sprint` for a sprint.

excluded repository
    A repository of the `plone` GitHub organisation that the statistics skip.
    Each one is listed with a reason in `curated/mappings/excluded_repositories.csv`.

identity
    A string that denotes a person in the data: the GitHub login the person is counted under (kind `github`), a further GitHub account (`github-alias`), a commit email address (`email`) or a spelling of the name (`name`).
    Identities are listed in `curated/mappings/identities.csv`, each with the id of its person and the {term}`source` that connects them.

independent contributor
    A self-employed person or volunteer whose organisation has the kind `independent` in `curated/mappings/organisations.csv`, for example `Name (independent)`.
    An independent contributor is mapped, unlike an {term}`Unmapped` one.

merge commit
    A commit with more than one parent, created when a branch or pull request is merged.
    The statistics don't count merge commits.

organiser
    A person or an organisation that organised an {term}`event`, one row of `curated/community/organisers.csv` with exactly one of the two.
    An organisation in that row is an {term}`organising entity`.

organising entity
    An organisation that a source names as organiser of an event or giver of a talk, such as a company team.
    Curated data names it by its id in an organisation column; the organisation of a person comes from their {term}`affiliation`.

person id
    The opaque identifier of a person in `curated/mappings/people.csv`, such as `jane-doe`.
    Every other file refers to the person by it.
    An id is chosen when the row is created and never renamed.

PLIP
    A Plone Improvement Proposal: a GitHub issue with the label `03 type: feature (plip)` that proposes a larger change to Plone.

PR interaction
    A comment or review on a pull request by someone other than a bot.

register
    One of the files `curated/mappings/people.csv`, `curated/mappings/identities.csv`, `curated/mappings/affiliations.csv`, `curated/mappings/citations.csv` and `curated/mappings/organisations.csv`, or the source register `curated/sources/sources.csv`.
    They hold every person, name, affiliation, citation, organisation and source once.

release branch
    A branch for a release line of a package, named like `2.5`, `3.0` or `4.3.x`.

set column
    A column of a curated file that holds the ids of several rows of a register, separated by semicolons, such as the trainers of a training.

snippet
    The words of a {term}`source` that support a citation or an identity, verbatim from the excerpt of the source, where `make check` finds them.

source
    A page, profile, commit, video or decision in the source register `curated/sources/sources.csv`, captured once with the passages we cite in its excerpt file.

Unmapped
    The group of contributors without an {term}`affiliation` for the year.
    Their work counts for no organisation.
    Unmapped is not an organisation and is not ranked among organisations.
```
