(reference-mapping-files)=

# Mapping and configuration files

This page describes the hand-maintained files that decide which repositories, accounts and organisations the statistics use.
All of them are in `curated/mappings/`; `scripts/lib/paths.py` lists where the scripts look for them.
A script that reads one of these files stops with an error if the file is missing, instead of running without it.

See {doc}`/explanation/attribution` for why the mapping works the way it does.

## `curated/mappings/organisations.csv`

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

## `curated/mappings/organisation_mapping_sources.csv`

Public records for the current organisation of the logins in `curated/mappings/organisations.csv`.

Columns
:   `github_username`, `organisation`, `source`, `checked`.

`source`
:   A link to the public record, such as the GitHub profile with its company field, a conference biography, or a company team page.

`checked`
:   The date on which the record said so, as `YYYY-MM-DD`.

Rules
:   Each login appears once, with the organisation that `curated/mappings/organisations.csv` lists for it.
    Every row must have a link.
    Every login in `curated/mappings/organisations.csv` must have a row; a login without a public record stays Unmapped ([#86](https://github.com/plone/plone-contributor-statistics/issues/86)).
    `tests/test_unmapped_and_mapping.py` checks the format.

## `curated/mappings/organisation_mapping_overrides.csv`

Past organisations of GitHub accounts, for the years in which they differ from `curated/mappings/organisations.csv`.

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
:   For a given year, a matching override replaces the entry of `curated/mappings/organisations.csv`.
    `from_year` must not be later than `to_year`.
    Every row must have a source.
    `organisation` must be listed in `curated/mappings/organisations.csv`, or be `Unmapped` for years in which the affiliation isn't documented.
    The overrides of one login must not overlap.
    `tests/test_unmapped_and_mapping.py` checks the format.

## `curated/mappings/organisation_mapping_proposals.csv`

Past organisations that a company email address in the commits suggests, but that nobody has confirmed yet.
The statistics don't read this file.

Columns
:   `contributor`, `organisation`, `from_year`, `to_year`, `evidence`.

`contributor`
:   The GitHub login, or the name of a person without a GitHub account.

`evidence`
:   The company address and the years of the commits that use it.

Rules
:   A confirmed row moves to `curated/mappings/organisation_mapping_overrides.csv`, with the confirmation as its source.
    The organisation also has to be added to `curated/mappings/organisations.csv` if it isn't listed yet.
    `tests/test_unmapped_and_mapping.py` checks the format.

## `curated/mappings/bot_accounts.csv`

GitHub accounts that are bots, although the GitHub API lists them as users.

Columns
:   `login`, `reason`.

Accounts with a `[bot]` suffix, and accounts that the GitHub API marks as `Bot`, are recognized without an entry.

## `curated/mappings/excluded_repositories.csv`

Repositories of the `plone` organisation that the statistics skip.

Columns
:   `repository`, `reason`.

All other repositories of the organisation are collected, including archived repositories and forks.
The commit and the pull request interaction collectors use the same list.

## `curated/mappings/commit_authors.csv`

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

## `curated/mappings/account_aliases.csv`

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

## `curated/mappings/mapping-github-username-to-fullname.csv`

Names of people in the curated community data, linked to their GitHub login.
Community roles mostly name a person; this file lets the scripts count a person who did both code and community work once, see {doc}`/explanation/community-page`.
`scripts/lib/people.py` reads it.

Columns
:   `github username`, `fullname`, `source`.

`fullname`
:   The name as the community data spells it.
    A person can have several rows, one per spelling, for example with and without a middle name.

`source`
:   The public record that links the name to the login, usually the GitHub profile, whose public name is the same.
    A spelling that differs from the profile name needs a record that connects the two, such as the login itself or the same organisation.

Rules
:   The file is sorted by login.
    Each name maps to one login.
    `tests/test_person_names_format.py` checks the format.
    `python -m scripts.tools.unmatched_names` lists the names in the community data without a login; with `--propose`, it proposes rows from exact matches with GitHub profile names, to check before adding them.

## Conventions for all CSV files

- Separate several values in one cell with semicolons, never with `&`.
- Put double quotes around values that contain commas.
- Spell organisation names exactly as in `curated/mappings/organisations.csv`, for example `kitconcept GmbH`, `RedTurtle`, `Klein & Partner KG`, `CMS Communications Inc.`, `Codesyntax`, `PY76`, `UNAM` and `University of Jyväskylä`.
  An organisation without GitHub contributors gets a row with an empty `Team`.
- Write `Unmapped` when the organisation isn't known; never leave the organisation empty.
- Save the files as UTF-8 without a byte order mark, with Unix line endings.
- `tests/test_curated_community_format.py` and `tests/test_curated_organisation_names.py` check these conventions for the curated community data.
