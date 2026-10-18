# Instructions for agents

This file is for AI coding agents of any vendor working on this repository.
People are welcome to read it too.

The repository collects statistics about contributions to Plone: commits, pull requests, PLIPs and curated community data, attributed to people and organisations.
The method and its reasons are documented in `docs/`, published at https://plone.github.io/plone-contributor-statistics/.
Read the documentation before you change data or method, and link to it instead of repeating it.

## Commands

- `make setup`: install the dependencies and create `.env` for the GitHub token.
- `make test`: run the offline test suite.
- `make check`: compile all scripts and check the requirements.
- `make docs-install` and `make docs`: build the documentation, warnings are errors.
- `make help`: list all targets, see also `docs/reference/make-targets.md`.

## Layout

- Root: the scripts (`*.py`), the `Makefile`, and the mapping files (`organisations.csv`, `organisation_mapping_overrides.csv`, `organisation_mapping_sources.csv`, `organisation_mapping_proposals.csv`, `commit_authors.csv`, `account_aliases.csv`, `bot_accounts.csv`, `excluded_repositories.csv`).
- `data/`: collected and derived data, one file per year.
- `data/community-contributions/`: curated community data, one file per year and kind.
- `reports/`: generated reports.
- `tests/`: pytest tests.
- `docs/`: the documentation, Sphinx with MyST markdown.
- `archive/`: historical material. Never edit it, and never rely on it as a description of the current method.

## Rules

- **Worktrees.** Other agents may be working in the same checkout. Do your work in a git worktree on its own branch.
- **Documentation.** A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request.
- **Specs and plans.** Draft specs and plans outside `docs/`. As the last step before opening the pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename, for transparency.
- **Tests.** Code changes get offline pytest tests; the GitHub API is replaced by fakes. Data changes get format checks, not tests of their content.
- **A public record for every piece of evidence.** Every row of curated data and every entry of the mapping files needs a public record, linked in its source: a web page, an archived page, a register entry, a public commit, or a confirmation in public, such as a comment by the person on a GitHub issue or pull request. A confirmation that exists only in a chat or in someone's memory is not a public record. Remove what no public record supports, or leave the contributor Unmapped, instead of guessing.
- **Exception: early commit authors.** Identifying the people behind CVS and Subversion commit addresses in `commit_authors.csv` often has no public record. There, say in `source` what the identification rests on.
- **Mappings need evidence.** A change to the organisation mapping needs a public record, see above. When in doubt, a contributor stays Unmapped. See `docs/explanation/attribution.md`.
- **Mapping files.** Keep `organisations.csv` sorted alphabetically by organisation, ignoring case. List each GitHub login once, with the case it has on GitHub. Record past organisations in `organisation_mapping_overrides.csv`, not by editing the current entry.
- **CSV conventions.** Separate several values in one cell with semicolons, never `&`. Quote values that contain commas. Spell organisation names exactly as in `organisations.csv`.
- **Secrets.** Never commit `.env` or a token.
- **Statistics in prose.** Don't write rankings or numbers into the documentation; they go stale with the next run.
- **Attribution.** End commit messages, pull request descriptions, issues and comments with `Assisted-by: <model name>`, without an email address.

## Looking up names

`mapping-github-username-to-fullname.csv` maps some GitHub logins to full names.
For other logins, `python get_github_name.py <login>` asks the GitHub API; add new results to the mapping file.
