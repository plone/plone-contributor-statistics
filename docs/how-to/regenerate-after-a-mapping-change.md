(how-to-regenerate-after-a-mapping-change)=

# Regenerate the statistics after a mapping change

This guide shows you how to update the organisation statistics and reports after a change to the mapping files.
You don't need a GitHub token, because nothing is collected from GitHub again.

1.  Install the dependencies, if you haven't yet:

    ```shell
    make install
    ```

2.  Regenerate the organisation statistics of all years:

    ```shell
    make run-organisation-stats
    ```

    If the change affects only one year, run `make run-organisation-stats-YYYY` with that year instead.

3.  Regenerate the summaries and the reports:

    ```shell
    make three-year-summary
    make five-year-summary
    make ten-year-summary
    make generate-report
    make generate-volto-report
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

{doc}`/reference/make-targets` lists all targets.
