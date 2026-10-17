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
bot account
    A GitHub account that is not a person, such as a continuous integration bot or a GitHub App.
    GitHub Apps have a `[bot]` suffix.
    Bots that GitHub lists as users are named in `bot_accounts.csv`.
    The statistics leave bot accounts out.

curated data
    Data that people collect and check by hand against a public source, as opposed to data that a script collects from an API.
    Curated data lives in `data/community-contributions/`.

default branch
    The main branch of a repository on GitHub, for example `main` or `master`.

excluded repository
    A repository of the `plone` GitHub organisation that the statistics skip.
    Each one is listed with a reason in `excluded_repositories.csv`.

independent contributor
    A self-employed person or volunteer who has their own entry in `organisations.csv`, for example `Name (independent)`.
    An independent contributor is mapped, unlike an {term}`Unmapped` one.

merge commit
    A commit with more than one parent, created when a branch or pull request is merged.
    The statistics don't count merge commits.

organisation mapping
    The assignment of a GitHub account to the organisation that sponsors the person's time on Plone.
    It consists of `organisations.csv` and the {term}`overrides <override>`.

override
    A row in `organisation_mapping_overrides.csv` that maps a GitHub account to another organisation for a range of years.
    Overrides record past affiliations, while `organisations.csv` records the current one.

PLIP
    A Plone Improvement Proposal: a GitHub issue with the label `03 type: feature (plip)` that proposes a larger change to Plone.

PR interaction
    A comment or review on a pull request by someone other than a bot.

release branch
    A branch for a release line of a package, named like `2.5`, `3.0` or `4.3.x`.

Unmapped
    The group of contributors whose GitHub account has no entry in the {term}`organisation mapping`.
    Unmapped is not an organisation and is not ranked among organisations.
```
