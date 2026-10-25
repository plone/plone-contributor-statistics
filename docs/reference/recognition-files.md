(reference-recognition-files)=

# Community recognition files

This page describes the files of the Community Recognition Program in the repository.
They are in `curated/community/`, next to the community data.

See {doc}`/explanation/community-recognition` for what these files can and can't explain.

`scripts/report/generate_community_recognition_report.py` stops with an error if the curated community data has no event and no role of the year, or if a yearly organisation file, `collected/plips/plone-plips-detailed.csv` or the levels file is missing.
If the year has no rows of one kind, it prints a warning and goes on, because not every kind exists in every year.

## `curated/community/community-recognition-points.csv`

The points per kind of contribution.

Columns
:   `Category`, `Criteria`, `Comment`, `Period`, `Number of points`.

`Category`
:   `Code`, `Community` or `Marketing`.

`Comment`
:   How the points are split, for example among the organisers of one event.

`Period`
:   The time window the contribution counts in.

No script reads this file.
`scripts/report/generate_community_recognition_report.py` has its own points in the code.

## `curated/community/community-recognition-levels.csv`

The recognition levels and their point ranges.

Columns
:   `Level`, `Min Points`, `Max Points`, `Description`.

Rules
:   The ranges follow each other without gaps; the last level has no `Max Points`.
    A level applies from its `Min Points` until the next level's minimum is reached, because points can be fractions: 9.5 points are still in the level that ends at 9.

`scripts/report/generate_community_recognition_report.py` reads this file.

## `derived/community-recognition/YYYY-community-recognition-report.csv`

The result per organisation, written by `scripts/report/generate_community_recognition_report.py`.

Columns
:   `Organisation`, `Recognition Level`, one column per category of contribution, `Total Points`.

## `reports/community-recognition.md`

The same result as a report, written by `scripts/report/generate_community_recognition_report.py`.
