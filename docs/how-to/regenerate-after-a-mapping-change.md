(how-to-regenerate-after-a-mapping-change)=

# Regenerate the statistics after a mapping change

This guide shows you how to update the organisation statistics and reports after a change to the registers.
You don't need a GitHub token, because nothing is collected from GitHub again.

1.  Install the dependencies, if you haven't yet:

    ```shell
    make install
    ```

    A change to the identities in `curated/mappings/identities.csv` needs `make run-changelogs` first, because the changelog collector maps the names, as the commit collector does with the email addresses.

2.  Regenerate the organisation statistics of all years:

    ```shell
    make run-organisation-stats
    ```

    If the change affects only one year, run `make run-organisation-stats-year YEAR=2025` with that year instead.

3.  Regenerate the summaries and the reports:

    ```shell
    make three-year-summary
    make five-year-summary
    make ten-year-summary
    make generate-report
    make yearly-activity
    ```

4.  If the change affects community recognition, regenerate it too:

    ```shell
    make community-recognition
    ```

5.  Run the tests and review the changed files:

    ```shell
    make test
    git diff --stat
    ```

    `tests/test_reproducible_outputs.py` regenerates the derived data and reports in a temporary copy and compares them with the committed files.
    It fails if an input changed and a file wasn't regenerated, and names the file.

{doc}`/reference/make-targets` lists all targets.
