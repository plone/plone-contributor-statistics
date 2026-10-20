# Registers and lists

Edited by hand, with a public record for every row.
Ids are opaque and never renamed; add a person with `python -m scripts.tools.person --add`.

| File | Holds |
|---|---|
| `people.csv` | One row per person, with an id. |
| `identities.csv` | Names, commit email addresses and second logins that denote a person in a source. |
| `affiliations.csv` | The organisation of a person for a range of years. A year that no row covers is Unmapped. |
| `organisations.csv` | One row per organisation, with an id, a name and a kind. |
| `affiliation_proposals.csv` | Affiliations that a source states and that no accepted record confirms yet. No script reads it. |
| `bot_accounts.csv` | GitHub accounts that are bots. |
| `excluded_repositories.csv` | Repositories that the statistics skip. |

The fields, constraints and checks are in the [Curated files reference](https://plone.github.io/plone-contributor-statistics/docs/reference/curated-files.html).
To change a row, see [Add an affiliation](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-an-affiliation.html) and [Add a person](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-a-person.html).
