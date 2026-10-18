(reference-mapping-files)=

# Mapping and configuration files

This page describes the hand-maintained files that decide which repositories, accounts and organisations the statistics use.
All of them are in the repository root.

See {doc}`/explanation/attribution` for why the mapping works the way it does.

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
:   `github_username`, `organisation`, `from_year`, `to_year`, `source`.

`from_year`
:   The first year the override applies to.

`to_year`
:   The last year the override applies to.
    Empty means up to the present.

`source`
:   How the past organisation is known: a link, a commit, or a confirmation, for example "Review in #70".

Rules
:   For a given year, a matching override replaces the entry of `organisations.csv`.
    `from_year` must not be later than `to_year`.
    Every row must have a source.
    `tests/test_unmapped_and_mapping.py` checks the format.

## `organisation_mapping_proposals.csv`

Past organisations that a company email address in the commits suggests, but that nobody has confirmed yet.
The statistics don't read this file.

Columns
:   `contributor`, `organisation`, `from_year`, `to_year`, `evidence`.

`contributor`
:   The GitHub login, or the name of a person without a GitHub account.

`evidence`
:   The company address and the years of the commits that use it.

Rules
:   A confirmed row moves to `organisation_mapping_overrides.csv`, with the confirmation as its source.
    The organisation also has to be added to `organisations.csv` if it isn't listed yet.
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

## `commit_authors.csv`

The people behind commit email addresses that GitHub doesn't link to an account.
The collector uses an entry only when GitHub links no account to the address.

Columns
:   `email`, `github_username`, `name`, `source`.

`email`
:   The author email address of the commits, in lower case.

`github_username`
:   The person's GitHub login, or empty if they have no GitHub account.

`name`
:   The person's name.
    Commits of a person without a GitHub account are counted under this name.

`source`
:   How the person was identified.

Rules
:   Each address appears only once.
    Every entry needs a source.
    `tests/test_commit_authors.py` checks the format.

## `account_aliases.csv`

Second GitHub accounts of a person, counted for their main account.

Columns
:   `alias`, `github_username`, `source`.

`alias`
:   The second account.

`github_username`
:   The main account.

Rules
:   A main account must not be an alias itself.
    Every entry needs a source.
    `tests/test_commit_authors.py` checks the format.

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
