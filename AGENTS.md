# Instructions for agents

This file is for AI coding agents of any vendor working on this repository.
People are welcome to read it too.

The repository collects statistics about contributions to Plone: commits, pull requests, PLIPs and curated community data, attributed to people and organisations.
The method and its reasons are documented in `docs/`, published at https://plone.github.io/plone-contributor-statistics/docs/.
Read the documentation before you change data or method, and link to it instead of repeating it.

## Commands

- `make setup`: install the dependencies and create `.env` for the GitHub token.
- `make test`: run the offline test suite.
- `make check`: compile all scripts, check the requirements and validate the curated data against its schemas.
- `make docs-install` and `make docs`: build the documentation, warnings are errors.
- `make site` and `make site-serve`: build and preview the published site: the community page at the root, the documentation below `docs/`.
- `make help`: list all targets, see also `docs/reference/make-targets.md`.

## Layout

Each top-level folder has a README that says what it holds and whether to edit it by hand.

- `scripts/`: the code, one folder per pipeline stage (`collect/`, `derive/`, `report/`, `tools/`) and shared code in `lib/`; run as `python -m scripts.<stage>.<name>` from the root, normally through `make`. `scripts/lib/paths.py` says where every file lives.
- `curated/`: input edited by hand. `curated/mappings/` holds the registers (`people.csv`, `identities.csv`, `affiliations.csv`, `organisations.csv`), `affiliation_proposals.csv` (read by no script) and the lists `bot_accounts.csv` and `excluded_repositories.csv`; `curated/community-contributions/` holds curated community data, one file per year and kind, which refers to people and organisations by id. `curated/schemas/` holds a Table Schema for every kind of file, `curated/datapackage.json` lists the files (`python -m scripts.tools.datapackage` writes it). `scripts/lib/model/` is the only code that reads `curated/`.
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
- **A public record for every piece of evidence.** Every row of curated data and every row of a register needs a public record, linked in its source: a web page, an archived page, a register entry, a public commit, or a confirmation in public, such as a comment by the person on a GitHub issue or pull request. A confirmation that exists only in a chat or in someone's memory is not a public record. Remove what no public record supports, or leave the contributor Unmapped, instead of guessing.
- **Exception: early commit authors.** Identifying the people behind CVS and Subversion commit addresses as identities of the kind `email` in `curated/mappings/identities.csv` often has no public record. There, say in `source` what the identification rests on.
- **Mappings need evidence.** A change to an affiliation needs a public record, see above. When in doubt, a contributor stays Unmapped. See `docs/explanation/attribution.md`.
- **Registers.** Ids of people and organisations are opaque: never rename one, never derive one. Add a new person with `python -m scripts.tools.person --add`, not by hand. A login is spelled as on GitHub, with its case. An affiliation covers years, there is no default, and `Unmapped` is never written. Statements that no accepted record confirms yet go to `curated/mappings/affiliation_proposals.csv`, and a reviewer moves them into `affiliations.csv`. The schemas and checks enforce formats, sorting and references; run `make check` after every change to `curated/`, and read its messages.
- **CSV conventions.** Separate several ids or values in one cell with semicolons, never `&`. Quote values that contain commas. Save as UTF-8 with Unix line endings. The format of every file is its schema, see `docs/reference/curated-files.md`, which `python -m scripts.tools.schema_docs` generates.
- **Secrets.** Never commit `.env` or a token.
- **Statistics in prose.** Don't write rankings or numbers into the documentation; they go stale with the next run.
- **Attribution.** End commit messages, pull request descriptions, issues and comments with `Assisted-by: <model name>`, without an email address.

## Looking up people

`python -m scripts.tools.person <query>` finds people by id, name, login or email; `--add "<name>" [--github <login>] --source <url>` adds one.
`python -m scripts.tools.affiliation <person> <year>` says which organisation the data gives for a year and which row says so.
`python -m scripts.tools.unmatched_names` lists people of the register without a login who appear as a login, and `--propose` suggests the `github` value to set in `people.csv` from GitHub profile names; check each before setting it.
`python -m scripts.tools.address_proposals [--person <id>] [--since <year>] [--write]` proposes affiliations from company email addresses in the commits of the cached clones; `--write` appends them to `affiliation_proposals.csv`.
`GITHUB_TOKEN=... python -m scripts.tools.github_evidence [--person <id>] [--all-years] [--write] [--refresh]` proposes dated affiliations for years that "not verified" rows guess, from the GitHub commit search (company addresses, and commits in the GitHub organisation of an organisation); responses are cached in `.cache/github-search/`.
For a single login, `python -m scripts.tools.get_github_name <login>` asks the GitHub API for the profile name.
