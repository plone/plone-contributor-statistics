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
    A row of `curated/mappings/affiliations.csv`: a person belonged to an organisation from one year to another, shown by a public record.
    A year that no affiliation covers is {term}`Unmapped`.

bot account
    A GitHub account that is not a person, such as a continuous integration bot or a GitHub App.
    GitHub Apps have a `[bot]` suffix.
    Bots that GitHub lists as users are named in `curated/mappings/bot_accounts.csv`.
    The statistics leave bot accounts out.

curated data
    Data that people collect and check by hand against a public source, as opposed to data that a script collects from an API.
    Curated data lives in `curated/`.

default branch
    The main branch of a repository on GitHub, for example `main` or `master`.

excluded repository
    A repository of the `plone` GitHub organisation that the statistics skip.
    Each one is listed with a reason in `curated/mappings/excluded_repositories.csv`.

identity
    A string that denotes a person in a source: a name, a commit email address or a second GitHub login.
    Identities are listed in `curated/mappings/identities.csv`, each with the id of its person.

independent contributor
    A self-employed person or volunteer whose organisation has the kind `independent` in `curated/mappings/organisations.csv`, for example `Name (independent)`.
    An independent contributor is mapped, unlike an {term}`Unmapped` one.

merge commit
    A commit with more than one parent, created when a branch or pull request is merged.
    The statistics don't count merge commits.

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
    One of the files `curated/mappings/people.csv`, `curated/mappings/identities.csv`, `curated/mappings/affiliations.csv` and `curated/mappings/organisations.csv`.
    They hold every person, name, affiliation and organisation once.

release branch
    A branch for a release line of a package, named like `2.5`, `3.0` or `4.3.x`.

set column
    A column of a curated file that holds the ids of several rows of a register, separated by semicolons, such as the trainers of a training.

Unmapped
    The group of contributors without an {term}`affiliation` for the year.
    Their work counts for no organisation.
    Unmapped is not an organisation and is not ranked among organisations.
```
