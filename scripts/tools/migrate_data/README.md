# migrate_data

This folder holds the inputs, legacy copies and helper code that the migration script `scripts/tools/migrate_data_structure.py` needs (#139). Edit nothing by hand. The folder is removed after the migration lands.

- `profile_names.csv`: the GitHub profile names of the logins that no curated file names, fetched once by `python -m scripts.tools.migrate_data_structure fetch-names --out scripts/tools/migrate_data/profile_names.csv`.
- `override_dates.csv`: the date of the last commit up to the base revision `499a4af` that recorded each row of the old `organisation_mapping_overrides.csv`, written once by `python -m scripts.tools.migrate_data_structure override-dates` in a checkout with its history; the migration takes the `checked` date of an affiliation up to the present that comes from an override from it.
- `organisation_aliases.py`: a frozen copy of the alias table of the recognition script; the migration turns it into the `aliases` column of `organisations.csv`.
- `community.py`: the community part of the migration, which reads the old community files and rewrites them to ids.
- `audit.py`: `python -m scripts.tools.migrate_data_structure audit [--from REV] [--to REV]` gives every line that differs in `derived/` and `reports/` between the two revisions (by default the merge base with `main` and the work tree) the cause it can prove, recomputed from the old community files and the old mapping of `main` and the registers of the new revision; it exits 1 on an unexplained line and when nothing differs.
