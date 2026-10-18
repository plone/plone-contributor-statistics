# Plone Contributor Statistics

Statistics about who contributes to Plone and which organisations sponsor that work, from 2003 to today.
They count commits and merged pull requests in the repositories of the [`plone` GitHub organisation](https://github.com/plone), pull request reviews and comments, PLIPs, and curated community work such as conferences, sprints, trainings and release management.

**Documentation: https://plone.github.io/plone-contributor-statistics/** (source in [`docs/`](docs/))

**All data comes from public records, with linked sources.**
The commits and pull requests are public on GitHub.
Every attribution to a person or an organisation, and every row of curated community data, needs a public record: a web page, an archived page, a register entry, a conference biography, a public commit, or a public confirmation by the person.
A memory alone is not enough; without a public record, an entry stays out, and a contributor stays Unmapped.
The one exception is identifying the people behind early CVS and Subversion commit addresses, where public records are often impossible; there, the source says what the identification rests on.
Some older files still lack linked sources, and [#86](https://github.com/plone/plone-contributor-statistics/issues/86) tracks them.

The documentation explains where the data comes from, how it is counted, and why.
It is for:

- members of the Plone Foundation who want to understand how the numbers for their organisation come together,
- people who study Plone as an example of a long-lived free software community,
- everyone who looks for the people they once worked with on Plone,
- contributors who correct data or change the method.

## Quick start

```shell
make setup        # install the dependencies, create .env for the GitHub token
make test         # run the offline tests
make docs-install # install the documentation dependencies
make docs         # build the documentation to docs/_build/html
make help         # list all targets
make year YEAR=2025 # collect, derive and report a completed year
```

Collecting data from GitHub needs a token in `.env`.
See [Prepare the numbers for a new year](https://plone.github.io/plone-contributor-statistics/how-to/prepare-a-new-year.html) and [Collect the data again](https://plone.github.io/plone-contributor-statistics/how-to/collect-data-again.html).

## Data and reports

- `scripts/`: the code, one folder per pipeline stage, see [`scripts/README.md`](scripts/README.md).
- `data/`: contributor, organisation and pull request interaction files, one per year.
- `curated/community-contributions/`: curated community data, one file per year and kind.
- `reports/`: generated reports.
- `archive/`: earlier analyses, proposals and notes, kept for reference.

Earlier charts on Flourish: [individual contributors](https://public.flourish.studio/visualisation/24775871/) and [organisations](https://public.flourish.studio/visualisation/24775561/).
They are no longer updated; their scripts are in `archive/flourish/`.

## Contributing

Corrections are welcome as pull requests, with a link to a public record, or with a confirmation by the person in the pull request.
See [Correct an organisation mapping](https://plone.github.io/plone-contributor-statistics/how-to/correct-an-organisation-mapping.html) and [Contribute to the documentation](https://plone.github.io/plone-contributor-statistics/contributing/documentation.html).

Code changes get tests; data files get format checks ([#52](https://github.com/plone/plone-contributor-statistics/issues/52)).
GitHub Actions runs the tests and builds the documentation on every pull request.
A pull request that changes the method must update the documentation in the same pull request.

Agents: read [`AGENTS.md`](AGENTS.md).
