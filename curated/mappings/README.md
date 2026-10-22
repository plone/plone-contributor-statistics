# Registers and lists

Edited by hand, with a public record for every row.
Ids are opaque and never renamed; add a person with `python -m scripts.tools.person --add`.

| File | Holds |
|---|---|
| `people.csv` | One row per person, with an id. |
| `identities.csv` | GitHub logins, names and commit email addresses that denote a person, each with its source. |
| `affiliations.csv` | The organisation of a person for a range of years, with a status: `stated`, `assumed`, `denied` (a proposal a reviewer turned down) or `proposed` (never counted). A year that no row decides is Unmapped. |
| `citations.csv` | The sources each affiliation rests on, with the passages they say it in. |
| `organisations.csv` | One row per organisation, with an id, a name and a kind. |
| `bot_accounts.csv` | GitHub accounts that are bots. |
| `excluded_repositories.csv` | Repositories that the statistics skip. |

The fields, constraints and checks are in the [Curated files reference](https://plone.github.io/plone-contributor-statistics/docs/reference/curated-files.html).
To change a row, see [Add an affiliation](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-an-affiliation.html) and [Add a person](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-a-person.html).
