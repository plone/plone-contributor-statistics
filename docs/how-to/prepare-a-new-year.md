(how-to-prepare-a-new-year)=

# Prepare the numbers for a new year

This guide shows you how to add a completed year to the statistics.
You need a GitHub personal access token, see {doc}`collect-data-again` for how to set it up.

1.  Add the curated community data of the year, each row with a public record, as described in {doc}`add-curated-community-data`.

2.  Collect, derive and report the year in one run:

    ```shell
    make year YEAR=2025
    ```

    Without `YEAR`, the target uses the last completed year.
    It runs the steps in pipeline order:

    -   collect commits, merged pull requests, pull request interactions, Volto statistics and PLIPs;
    -   write the organisation statistics of the year and the PLIPs per organisation;
    -   write the three-, five- and ten-year summaries that end with the year, and the yearly totals and graphs;
    -   write the contributor report, the Volto report and the community recognition report of the year.

    Most steps stop with an error if a file they need is missing.
    To repeat a single step, run its target, listed in {doc}`/reference/make-targets`.

3.  List the unmapped contributors worth researching, of all years:

    ```shell
    make analyze-independent
    ```

    Map those you can support with a public record, as described in {doc}`correct-an-organisation-mapping`.
    Then regenerate as described in {doc}`regenerate-after-a-mapping-change`.

4.  Run the tests and review the changed files:

    ```shell
    make test
    git status
    ```

    The summaries of the new year are new files, because their names contain the years they cover.

5.  Commit the collected data, the derived data and the reports together, and open a pull request.
