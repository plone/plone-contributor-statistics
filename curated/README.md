# Curated input

Edited by hand.
Every row and every mapping entry needs a public record, linked in its source column: a web page, an archived page, a register entry, a public commit, or a public confirmation by the person.
Without one, an entry stays out, and a contributor stays Unmapped.

| Folder | Holds |
|---|---|
| `mappings/` | Which accounts, repositories and organisations the statistics use: `organisations.csv`, the overrides, sources and proposals, bots, excluded repositories, commit authors and account aliases. See [Mapping and configuration files](https://plone.github.io/plone-contributor-statistics/docs/reference/mapping-files.html). |
| `community-contributions/` | Community work per year and kind, such as conferences, trainings, sprints, release managers and the Board, plus the recognition points and levels. See [Add curated community data](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-curated-community-data.html). |

The scripts stop with an error if a mapping file is missing.
