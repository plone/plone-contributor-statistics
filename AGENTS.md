# Instructions for agents

This file is for AI coding agents of any vendor working on this repository.
People are welcome to read it too.

The repository collects statistics about contributions to Plone: commits, pull requests, PLIPs and curated community data, attributed to people and organisations.
The method and its reasons are documented in `docs/`, published at https://plone.github.io/plone-contributor-statistics/docs/.
Read the documentation before you change data or method, and link to it instead of repeating it.

## Commands

- `make setup`: install the dependencies and create `.env` for the GitHub token.
- `make test`: run the offline test suite.
- `make check`: run flake8, compile all scripts, check the requirements, and validate the curated data: the schemas and the checks beyond them (references, sorting, snippets in their excerpts, open cases).
- `make docs-install` and `make docs`: build the documentation, warnings are errors.
- `make site` and `make site-serve`: build and preview the published site: the community page at the root, the documentation below `docs/`.
- `make help`: list all targets, see also `docs/reference/make-targets.md`.

## Layout

Each data and code folder has a README that says what it holds and whether to edit it by hand.

- `scripts/`: the code, one folder per pipeline stage (`collect/`, `derive/`, `report/`, `tools/`) and shared code in `lib/`; run as `python -m scripts.<stage>.<name>` from the root, normally through `make`. `scripts/lib/paths.py` says where every file lives.
- `curated/`: input edited by hand. `curated/mappings/` holds the registers (`people.csv`, `identities.csv`, `affiliations.csv` with a status per row, `citations.csv`, `organisations.csv`) and the lists `bot_accounts.csv` and `excluded_repositories.csv`; `curated/community/` holds curated community data, one file per kind with the rows of every year: the events (`events.csv`), the talks, trainings and organisers that point to an event by its id, the roles with a `year` column, and the recognition levels and points; it refers to people and organisations by id, and every row cites the source register, except the recognition tables and the events `plone-conference-<year>` and `wpd-<year>-online` that hold the rows pointing to them. `curated/plips/` holds the PLIPs from before GitHub. `curated/sources/` holds the source register and the excerpt files of the passages we cite, written through `python -m scripts.tools.capture`, never whole pages. `curated/schemas/` holds a Table Schema for every kind of file, `curated/datapackage.json` lists the files (`python -m scripts.tools.datapackage` writes it). `scripts/lib/model/` is the only code that reads `curated/`.
- `collected/`: data the collectors fetch from GitHub, one file per year. Never edit by hand.
- `derived/`: data computed from curated and collected data. Never edit by hand.
- `reports/`: generated reports, text summaries and graphs. Never edit by hand.
- `scripts/report/site/`: templates and static files of the community page, which `make site` renders into the gitignored `_site/`, with the documentation below `_site/docs/`; GitHub Pages publishes `_site/`.
- `tests/`: pytest tests.
- `docs/`: the documentation, Sphinx with MyST markdown.
- `archive/`: historical material. Never change the archived files, and never rely on them as a description of the current method; add new material only as a new file or folder with its row in `archive/README.md`.
- Root: only the `Makefile`, the READMEs, requirements and configuration. A test keeps other files out.

## Rules

- **Worktrees.** Other agents may be working in the same checkout. Do your work in a git worktree on its own branch.
- **Documentation.** A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request.
- **Specs and plans.** Draft specs and plans outside `docs/`. As the last step before opening the pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename, for transparency.
- **Tests.** Code changes get offline pytest tests; the GitHub API is replaced by fakes. Data changes get format checks, not tests of their content.
- **A public record for every piece of evidence.** Every row of curated data and every row of a register needs a public record, captured into the source register and cited by its id (an affiliation through `citations.csv`, a person through the `source` of their identities; the community rows in `sources`, with the record in words in `cited_as`): a web page, an archived page, a register entry, a public commit, or a confirmation in public, such as a comment by the person on a GitHub issue or pull request. A confirmation that exists only in a chat or in someone's memory is not a public record. Remove what no public record supports, or leave the contributor Unmapped, instead of guessing.
- **Exception: early commit authors.** Identifying the people behind CVS and Subversion commit addresses as identities of the kind `email` in `curated/mappings/identities.csv` often has no public record. There, leave `source` empty and say in `notes` what the identification rests on. An identity of the kind `svn`, a Subversion user name, cites a source like any other.
- **Mappings need evidence.** A change to an affiliation needs a public record, see above. When in doubt, a contributor stays Unmapped. See `docs/explanation/attribution.md`.
- **Registers.** Ids of people and organisations are opaque: never rename one, never derive one. Add a new person with `python -m scripts.tools.person --add`, not by hand. An affiliation's id is made once with `scripts.lib.model.affiliation_id` when the row is created, and never changed. A login is spelled as on GitHub, with its case. An affiliation covers years, there is no default, and `Unmapped` is never written. Its status is `stated` when its records say so, `assumed` when it extends a range beyond its records (say in `notes` what it rests on), `denied` for a proposal a reviewer turned down, and `proposed` for a statement that no accepted record confirms yet, which never counts. Capture a record with `python -m scripts.tools.capture` before you cite it; an affiliation cites its sources in `citations.csv`, one row per source and verbatim snippet, and never loses a citation. Rows of a person may overlap: the organisation of a year is computed by the rules of `docs/explanation/attribution.md`, and a year that no rule decides is an open case: `make check` warns, and it counts as Unmapped until a decision settles it. The schemas and checks enforce formats, sorting and references; run `make check` after every change to `curated/`, and read its messages.
- **CSV conventions.** Separate several ids or values in one cell with semicolons, never `&`. Quote values that contain commas. Save as UTF-8 with Unix line endings. The format of every file is its schema, see `docs/reference/curated-files.md`, which `python -m scripts.tools.schema_docs` generates.
- **Secrets.** Never commit `.env` or a token.
- **Statistics in prose.** Don't write rankings or numbers into the documentation; they go stale with the next run.
- **Attribution.** End commit messages, pull request descriptions, issues and comments with `Assisted-by: <model name>`, without an email address.

## Looking up people

`python -m scripts.tools.person <query>` finds people by id, name, login or email; `--add "<name>" [--github <login>] --source <id or url>` adds one, citing a source that is in the source register already.
`python -m scripts.tools.capture <url> --quote "<text>"` puts a record into the source register and prints its id, see `docs/how-to/capture-a-source.md`; a GitHub profile, commit, issue or comment needs `GITHUB_TOKEN` in the environment, which the tool reads, not `.env`.
`python -m scripts.tools.affiliation <person> [<year> ...]` prints the organisation the attribution rules compute for each year, and every affiliation of the person with the sources it cites.
`python -m scripts.tools.unmatched_names` lists people of the register without a login who appear as a login, and `--propose` prints a `github` identity row for each from GitHub profile names, with the command that captures the profile; it writes nothing, so check each, capture the profile and add the row.
`python -m scripts.tools.address_proposals [--person <id>] [--since <year>] [--write]` proposes affiliations from company email addresses in the commits of the cached clones; `--write` captures the example commits as sources and adds the proposals to `affiliations.csv` as `proposed` rows citing them.
`GITHUB_TOKEN=... python -m scripts.tools.github_evidence [--person <id>] [--all-years] [--write] [--refresh]` proposes dated affiliations for the years that `assumed` rows guess, from the GitHub commit search (company addresses, and commits in the GitHub organisation of an organisation); responses are cached in `.cache/github-search/`, and `--write` captures and cites the commits as `address_proposals` does.
For a single login, `python -m scripts.tools.get_github_name <login>` asks the GitHub API for the profile name.
