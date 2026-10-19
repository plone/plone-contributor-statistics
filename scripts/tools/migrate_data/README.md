# migrate_data

This folder holds the inputs, legacy copies and helper code that the migration script `scripts/tools/migrate_data_structure.py` needs (#139). Edit nothing by hand. The folder is archived after the migration lands.

- `profile_names.csv`: the GitHub profile names of the logins that no curated file names, fetched once by `python -m scripts.tools.migrate_data_structure fetch-names --out scripts/tools/migrate_data/profile_names.csv`.
- `organisation_aliases.py`: a frozen copy of the alias table of the recognition script; the migration turns it into the `aliases` column of `organisations.csv`.
- `community.py`: the community part of the migration, which reads the old community files and rewrites them to ids.
