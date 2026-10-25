(how-to-add-curated-community-data)=

# Add or correct curated community data

This guide shows you how to add or correct a row of curated community data: an event, a talk, a training, an organiser, or a role such as a release manager.
You need a public source for the row.
The files are in `curated/community/`, and {ref}`reference-curated-files` lists the columns of each.

## Capture the source and find the people

1.  Capture the source first, as described in {doc}`capture-a-source`:

    ```shell
    python -m scripts.tools.capture "https://plone.org/news-and-events/news/news-for-2026/beethoven-sprint-report-2026" \
        --quote "Beethoven Sprint"
    ```

    The tool prints the id of the source, such as `6ecac2f04876`.
    A source that is already in the register keeps its id; look it up in `curated/sources/sources.csv`.

2.  Find or add every person the row names:

    ```shell
    python -m scripts.tools.person "Jane Doe"
    ```

    If the person is not in the register, add them first, see {doc}`add-a-person`.

Every row cites its sources the same way:

-   `sources` holds the ids of the sources, separated by semicolons.
-   `cited_as` holds the sources in words: the address of each source in `sources`, and a label or quote where it helps, such as `https://plone.org/…/beethoven-sprint-report-2026; Board: https://plone.org/…/minutes-january-8-2026`.
    The community page shows it as the record of the row and links its addresses.
    No check compares the addresses with `sources` yet, so make sure yourself that they are the same sources.
-   `notes` holds remarks.

Use ids instead of names.
In a set column, such as the speakers of a talk or the trainers of a training, separate several ids with semicolons.
Do not write the organisation of a person in the row: the statistics take it from `curated/mappings/affiliations.csv`.
If the source names it and no affiliation row exists for the year, add one, see {doc}`add-an-affiliation`.

Add a new row after the rows of its year, a talk, a training or an organiser after the rows of the events of its year, and don't reorder the rows of a year: the order decides which sprint and which talks count, see {doc}`/explanation/curated-community-data`.

## Add an event

Add a row to `curated/community/events.csv` with the `kind` `conference`, `symposium`, `wpd` or `sprint`, its `name` and `year`, and, where the source gives them, `start`, `end` and `location`.

-   A World Plone Day event needs its day as `start`, `YYYY-MM-DD`, and its `format`: `in person`, `hybrid` or `online`.
-   A sprint has a `level`, `strategic` or `community`, when the Board gave it one, see {doc}`/explanation/curated-community-data`.

The id is chosen once and never renamed:

-   the Plone Conference of a year: `plone-conference-<year>`;
-   a World Plone Day event: `wpd-<date>-` and the slug of its place, such as `wpd-2025-04-10-bologna-italy`, and the online edition of a year `wpd-<year>-online`;
-   a sprint or a symposium: the slug of its name.

The slug is the name in lower-case ASCII letters, digits and hyphens:

```shell
python -c "from scripts.lib.model.names import slugify; print(slugify('Beethoven Sprint 2027'))"
```

If the id is taken, add `-2`, `-3`.
Two sprints of a year can't have the same name.

## Add a talk

Add a row to `curated/community/talks.csv` with the `event` it was given at, its `type`, `title` and `speakers`, and the `video` where a recording exists.
A talk of the Plone Conference or a symposium has the `type` `Keynote`, `Talk` or `Panel`.
A World Plone Day video points to the event of its place, or to `wpd-<year>-online` when it was given online, and gives the place in `location`.
A talk that the source attributes to a team instead of people has the team in `organisations`.

The id is `t` and eight hex digits of the SHA-1 of the event, the title and the type, separated by `|`:

```shell
python -c "import hashlib; print('t' + hashlib.sha1('plone-conference-2026|My talk|Talk'.encode()).hexdigest()[:8])"
```

## Add a training

Add a row to `curated/community/trainings.csv` with the `event`, the `title` and the `trainers`.
The id is `r` and eight hex digits of the SHA-1 of the event and the title:

```shell
python -c "import hashlib; print('r' + hashlib.sha1('plone-conference-2026|My training'.encode()).hexdigest()[:8])"
```

A title appears once per event; if the id is taken nevertheless, add `-2`.

## Add an organiser

Add one row to `curated/community/organisers.csv` per organiser, with the `event` and either a `person` or an `organisation`, never both.
An organisation is an organising entity that the source names, not the employer of a person.
Add the rows of an event next to each other.

## Add a role

The roles have one row per person and year:

-   `curated/community/board-of-directors.csv`: the `person` and the `role`, `voting` or `non-voting`, with the year in which the term ends as `year`;
-   `curated/community/team-leaders.csv`: the `person` and the `team`;
-   `curated/community/release-managers.csv`: the `person`;
-   `curated/community/podcasts.csv`: the `series`, the `person` who hosted it and the number of `episodes` in the year.

## Check and propose the change

1.  Validate the files and run the tests:

    ```shell
    make check
    make test
    ```

    The checks name the file, the row and the column of every error, and suggest the nearest ids for one that does not exist.
    They find an event, a person, an organisation or a source that does not exist, an organiser row with both or neither of person and organisation, a talk or a training at an event of the wrong kind, and an id that is taken.

2.  Open a pull request and name the source in its description.

{doc}`/explanation/curated-community-data` explains why every row needs a source and why the data refers to people by id.
