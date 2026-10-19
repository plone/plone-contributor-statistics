(reference-mapping-files)=

# Registers and lists

The folder `curated/mappings/` holds four registers and three lists.
The registers say who people and organisations are: `curated/mappings/people.csv` has one row per person, `curated/mappings/identities.csv` the names, commit addresses and second logins that denote a person in a source, `curated/mappings/affiliations.csv` the organisation a person belonged to in which years, and `curated/mappings/organisations.csv` one row per organisation.
`curated/mappings/affiliation_proposals.csv` holds affiliations that a source states and that no accepted record confirms yet; no script reads it.
Every other file refers to people and organisations by their ids.

The lists are `curated/mappings/bot_accounts.csv`, `curated/mappings/excluded_repositories.csv` and the proposals.
A script that reads one of these files stops with an error if the file is missing.
{ref}`reference-curated-files` describes the fields, constraints and checks of every file, generated from the Table Schemas, and {doc}`/explanation/attribution` explains why the registers work the way they do.
