(how-to-add-curated-community-data)=

# Add or correct curated community data

This guide shows you how to add or correct a row of curated community data, such as a sprint, a training or a release manager.
You need a public source for the row.

1.  Find or add every person the row names:

    ```shell
    python -m scripts.tools.person "Jane Doe"
    ```

    If the person is not in the register, add them first, see {doc}`add-a-person`.

2.  Open the file for the year and kind of contribution in `curated/community-contributions/`, for example `curated/community-contributions/YYYY-sprints.csv`.
    {ref}`reference-curated-files` lists the columns of each kind.

3.  Add or correct the row, with ids instead of names.
    In a set column, such as the trainers of a training, separate several ids with semicolons.
    An organisation column holds the id of an organising entity that the source names, not the employer of a person.
    Do not write the organisation of a person in the row: the statistics take it from `curated/mappings/affiliations.csv`.
    If the source names it and no affiliation row exists for the year, add one, see {doc}`add-an-affiliation`.

4.  Put a link to the record for the row in the `source` column, and use `notes` for remarks.

5.  Validate the files and run the tests:

    ```shell
    make check
    make test
    ```

    The checks name the file, the row and the column of every error, and suggest the nearest ids for one that does not exist.

6.  Open a pull request and name the source in its description.

{doc}`/explanation/curated-community-data` explains why every row needs a source and why the data refers to people by id.
