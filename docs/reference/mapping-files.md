(reference-mapping-files)=

# Registers and lists

The folder `curated/mappings/` holds five registers and two lists.
The registers say who people and organisations are:

- `curated/mappings/people.csv` has one row per person, with an opaque id and a name.
- `curated/mappings/identities.csv` has the GitHub logins, further GitHub accounts, commit addresses and spellings of the name that denote a person, each citing a source.
- `curated/mappings/affiliations.csv` has the organisation a person belonged to in which years, with a status: `stated`, `assumed`, `denied` or `proposed`.
- `curated/mappings/citations.csv` has the sources each affiliation rests on, one row per source and passage, with the passage as a snippet.
  A citation whose source was not read yet has an empty snippet; once the source is captured, `python -m scripts.tools.cite_snippets --write` fills it from the quotes in its `notes`, see {ref}`how-to-capture-a-source-not-read`.
- `curated/mappings/organisations.csv` has one row per organisation.

The sources that identities and citations name by id are in the source register, `curated/sources/sources.csv`, with an excerpt file of the cited passages per source.
Affiliations that a tool proposes and nobody has reviewed yet are rows with the status `proposed`; proposals a reviewer turned down are `denied` rows.
Every other file refers to people and organisations by their ids.

The lists are `curated/mappings/bot_accounts.csv` and `curated/mappings/excluded_repositories.csv`.
A script that reads one of these files stops with an error if the file is missing.
{ref}`reference-curated-files` describes the fields, constraints and checks of every file, generated from the Table Schemas, and {doc}`/explanation/attribution` explains why the registers work the way they do and how the organisation of a year is computed from them.
