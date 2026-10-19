# Instructions for agents

This file is for AI coding agents of any vendor working on this repository.
People are welcome to read it too.

The repository collects statistics about contributions to Plone: commits, pull requests, PLIPs and curated community data, attributed to people and organisations.
The method and its reasons are documented in `docs/`, published at https://plone.github.io/plone-contributor-statistics/docs/.
Read the documentation before you change data or method, and link to it instead of repeating it.

## Commands

- `make setup`: install the dependencies and create `.env` for the GitHub token.
- `make test`: run the offline test suite.
- `make check`: compile all scripts and check the requirements.
- `make docs-install` and `make docs`: build the documentation, warnings are errors.
- `make site` and `make site-serve`: build and preview the published site: the community page at the root, the documentation below `docs/`.
- `make help`: list all targets, see also `docs/reference/make-targets.md`.

## Layout

Each top-level folder has a README that says what it holds and whether to edit it by hand.

- `scripts/`: the code, one folder per pipeline stage (`collect/`, `derive/`, `report/`, `tools/`) and shared code in `lib/`; run as `python -m scripts.<stage>.<name>` from the root, normally through `make`. `scripts/lib/paths.py` says where every file lives.
- `curated/`: input edited by hand. `curated/mappings/` holds the mapping files (`organisations.csv`, `organisation_mapping_overrides.csv`, `organisation_mapping_sources.csv`, `organisation_mapping_proposals.csv`, `commit_authors.csv`, `account_aliases.csv`, `bot_accounts.csv`, `excluded_repositories.csv`, `mapping-github-username-to-fullname.csv`); `curated/community-contributions/` holds curated community data, one file per year and kind.
- `collected/`: data the collectors fetch from GitHub, one file per year. Never edit by hand.
- `derived/`: data computed from curated and collected data. Never edit by hand.
- `reports/`: generated reports, text summaries and graphs. Never edit by hand.
- `scripts/report/site/`: templates and static files of the community page, which `make site` renders into the gitignored `_site/`, with the documentation below `_site/docs/`; GitHub Pages publishes `_site/`.
- `tests/`: pytest tests.
- `docs/`: the documentation, Sphinx with MyST markdown.
- `archive/`: historical material. Never edit it, and never rely on it as a description of the current method.
- Root: only the `Makefile`, the READMEs, requirements and configuration. A test keeps other files out.

## Rules

- **Worktrees.** Other agents may be working in the same checkout. Do your work in a git worktree on its own branch.
- **Documentation.** A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request.
- **Specs and plans.** Draft specs and plans outside `docs/`. As the last step before opening the pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename, for transparency.
- **Tests.** Code changes get offline pytest tests; the GitHub API is replaced by fakes. Data changes get format checks, not tests of their content.
- **A public record for every piece of evidence.** Every row of curated data and every entry of the mapping files needs a public record, linked in its source: a web page, an archived page, a register entry, a public commit, or a confirmation in public, such as a comment by the person on a GitHub issue or pull request. A confirmation that exists only in a chat or in someone's memory is not a public record. Remove what no public record supports, or leave the contributor Unmapped, instead of guessing.
- **Exception: early commit authors.** Identifying the people behind CVS and Subversion commit addresses in `curated/mappings/commit_authors.csv` often has no public record. There, say in `source` what the identification rests on.
- **Mappings need evidence.** A change to the organisation mapping needs a public record, see above. When in doubt, a contributor stays Unmapped. See `docs/explanation/attribution.md`.
- **Mapping files.** Keep `curated/mappings/organisations.csv` sorted alphabetically by organisation, ignoring case. List each GitHub login once, with the case it has on GitHub. Record past organisations in `curated/mappings/organisation_mapping_overrides.csv`, not by editing the current entry.
- **CSV conventions.** Separate several values in one cell with semicolons, never `&`. Quote values that contain commas. Spell organisation names exactly as in `curated/mappings/organisations.csv`.
- **Secrets.** Never commit `.env` or a token.
- **Statistics in prose.** Don't write rankings or numbers into the documentation; they go stale with the next run.
- **Attribution.** End commit messages, pull request descriptions, issues and comments with `Assisted-by: <model name>`, without an email address.

## Looking up names

`curated/mappings/mapping-github-username-to-fullname.csv` links names in the community data to GitHub logins, each with its public record (the GitHub profile, or a record that connects a different spelling).
`python -m scripts.tools.unmatched_names` lists community names without a login, and `--propose` suggests rows from GitHub profile names; check each before adding it.
For a single login, `python -m scripts.tools.get_github_name <login>` asks the GitHub API for the profile name.
