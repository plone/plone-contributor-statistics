# Curated input

Edited by hand.
Every row needs a public record, linked in its source column: a web page, an archived page, a register entry, a public commit, or a public confirmation by the person.
Without one, an entry stays out, and a contributor stays Unmapped.

Every file is described by a Frictionless Table Schema in `schemas/`, listed in `datapackage.json` (`python -m scripts.tools.datapackage` writes it).
`python -m scripts.tools.check`, or `make check`, validates the files and names the file, row and column of every error.
The [Curated files reference](https://plone.github.io/plone-contributor-statistics/docs/reference/curated-files.html) is generated from the schemas.

| Folder | Holds |
|---|---|
| `mappings/` | The registers `people.csv`, `identities.csv`, `affiliations.csv` and `organisations.csv`, the `affiliation_proposals.csv` that no script reads, and the lists `bot_accounts.csv` and `excluded_repositories.csv`. See [Registers and lists](https://plone.github.io/plone-contributor-statistics/docs/reference/mapping-files.html). |
| `community-contributions/` | Community work per year and kind, such as conferences, trainings, sprints, release managers and the Board, plus the recognition points and levels. People are ids of `people.csv`. See [Add curated community data](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-curated-community-data.html). |
| `plips/` | The PLIPs from before GitHub, on the plone.org roadmap and in Trac. See [Data files](https://plone.github.io/plone-contributor-statistics/docs/reference/data-files.html). |
| `sources/` | The source register `sources.csv` and one excerpt file per source, with the passages we cite. Written by `python -m scripts.tools.capture`, never whole pages. See [Capture a source](https://plone.github.io/plone-contributor-statistics/docs/how-to/capture-a-source.html). |
| `schemas/` | One Table Schema per kind of file. Edit one when a format changes, then regenerate the reference with `python -m scripts.tools.schema_docs`. |

`scripts/lib/model/` is the only code that reads this folder.
The scripts stop with an error if a register is missing.
