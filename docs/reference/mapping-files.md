(reference-mapping-files)=

# Registers and lists

The folder `curated/mappings/` holds five registers and two lists.
The registers say who people and organisations are: `curated/mappings/people.csv` has one row per person, `curated/mappings/identities.csv` the GitHub logins, names and commit addresses that denote a person, `curated/mappings/affiliations.csv` the organisation a person belonged to in which years, with a status, `curated/mappings/citations.csv` the sources each affiliation rests on, and `curated/mappings/organisations.csv` one row per organisation.
Affiliations that a tool proposes and nobody has reviewed yet are rows with the status `proposed`; proposals a reviewer turned down are `denied` rows.
Every other file refers to people and organisations by their ids.

The lists are `curated/mappings/bot_accounts.csv` and `curated/mappings/excluded_repositories.csv`.
A script that reads one of these files stops with an error if the file is missing.
{ref}`reference-curated-files` describes the fields, constraints and checks of every file, generated from the Table Schemas, and {doc}`/explanation/attribution` explains why the registers work the way they do.
