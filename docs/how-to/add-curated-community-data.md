(how-to-add-curated-community-data)=

# Add or correct curated community data

This guide shows you how to add or correct a row of curated community data, such as a sprint, a training or a release manager.
You need a public source for the row.

1.  Open the file for the year and kind of contribution in `curated/community-contributions/`, for example `curated/community-contributions/YYYY-strategic-sprints.csv`.

2.  Add or correct the row.
    Separate several people or organisations in one cell with semicolons.

3.  Fill in the `Organisation` with the organisation as it is named in `curated/mappings/organisations.csv`.
    If the source names only people, take the organisation that `curated/mappings/organisations.csv` and `curated/mappings/organisation_mapping_overrides.csv` give for that year.
    If the organisation is unknown, write `Unmapped` instead of guessing.

4.  Put a link to the source in the `Source` column.
    If the file has no `Source` column, put the link in the pull request description.

5.  Run the format tests:

    ```shell
    make test
    ```

6.  Open a pull request and name the source in its description.

{doc}`/explanation/curated-community-data` explains why every row needs a source, and {doc}`/reference/data-files` lists the columns of each file.
