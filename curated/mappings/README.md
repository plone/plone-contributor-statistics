# Registers and lists

Edited by hand, with a public record for every row, captured into the source register `../sources/` and cited by its id.
Ids are opaque and never renamed; add a person with `python -m scripts.tools.person --add`.

| File | Holds |
|---|---|
| `people.csv` | One row per person, with an id. |
| `identities.csv` | The GitHub login a person is counted under, further GitHub accounts, commit email addresses, spellings of the name and further handles (`svn`, `irc`, `discourse`), each citing its source; an early commit address may instead say in `notes` what it rests on. |
| `affiliations.csv` | The organisation of a person for a range of years, with a status: `stated`, `assumed` (a range beyond its records), `denied` (a proposal a reviewer turned down) or `proposed` (never counted). Rows may overlap; the attribution rules compute the organisation of each year, and a year that the rules give no organisation, because no row covers it and no bridge fills it, or because no rule decides it (an open case), counts as Unmapped. |
| `citations.csv` | The sources each affiliation rests on, one row per source and passage, with the passage verbatim as the snippet. |
| `organisations.csv` | One row per organisation, with an id, a name and a kind. |
| `bot_accounts.csv` | GitHub accounts that are bots. |
| `excluded_repositories.csv` | Repositories that the statistics skip. |

The fields, constraints and checks are in the [Curated files reference](https://plone.github.io/plone-contributor-statistics/docs/reference/curated-files.html).
How the organisation of a year is computed is in [From a GitHub account to an organisation](https://plone.github.io/plone-contributor-statistics/docs/explanation/attribution.html).
To change a row, see [Add an affiliation](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-an-affiliation.html) and [Add a person](https://plone.github.io/plone-contributor-statistics/docs/how-to/add-a-person.html).
