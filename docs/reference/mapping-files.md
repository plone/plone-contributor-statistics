(reference-mapping-files)=

# Mapping and configuration files

This page describes the hand-maintained files that decide which repositories, accounts and organisations the statistics use.
All of them are in the repository root.

## `organisations.csv`

The current organisation of each GitHub account.

Columns
:   `Organisation`, `Team`.

`Organisation`
:   The organisation name, without leading or trailing spaces.
    Self-employed people and volunteers have their own entry, for example `Name (independent)`.

`Team`
:   The GitHub logins of the organisation's contributors, separated by semicolons.

Rules
:   The file is sorted alphabetically by organisation, ignoring case.
    Each login appears only once in the whole file, ignoring case.
    Logins must be valid GitHub logins, spelled with the same case as on GitHub, because the lookup is case-sensitive.
    `tests/test_unmapped_and_mapping.py` checks the format.

## `organisation_mapping_overrides.csv`

Past organisations of GitHub accounts, for the years in which they differ from `organisations.csv`.

Columns
:   `github_username`, `organisation`, `from_year`, `to_year`.

`from_year`
:   The first year the override applies to.

`to_year`
:   The last year the override applies to.
    Empty means up to the present.

Rules
:   For a given year, a matching override replaces the entry of `organisations.csv`.
    `from_year` must not be later than `to_year`.
    `tests/test_unmapped_and_mapping.py` checks the format.

## `bot_accounts.csv`

GitHub accounts that are bots, although the GitHub API lists them as users.

Columns
:   `login`, `reason`.

Accounts with a `[bot]` suffix, and accounts that the GitHub API marks as `Bot`, are recognized without an entry.

## `excluded_repositories.csv`

Repositories of the `plone` organisation that the statistics skip.

Columns
:   `repository`, `reason`.

All other repositories of the organisation are collected, including archived repositories and forks.
The commit and the pull request interaction collectors use the same list.

## `mapping-github-username-to-fullname.csv`

Full names for some GitHub logins, used by hand when filling in curated data.
No script reads it.

Columns
:   `github username`, `fullname`.

## `npm_mapping.txt`

The npm scopes and search terms per organisation, read by `npm_package_stats.py` and `volto_addon_discovery.py`.
One line per organisation: the organisation, a colon, and comma-separated scopes or search terms.

## Conventions for all CSV files

- Separate several values in one cell with semicolons, never with `&`.
- Put double quotes around values that contain commas.
- Spell organisation names exactly as in `organisations.csv`, for example `kitconcept GmbH`, `RedTurtle`, `Klein & Partner KG`, `CMS Communications Inc.`, `Codesyntax`, `PY76`, `UNAM` and `University of Jyväskylä`.
