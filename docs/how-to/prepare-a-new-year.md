(how-to-prepare-a-new-year)=

# Prepare the numbers for a new year

This guide shows you how to add a completed year to the statistics.
You need a GitHub personal access token, see {doc}`collect-data-again` for how to set it up.

1.  Add or complete the curated community data of the year, each row with a public record, as described in {doc}`add-curated-community-data`.
    Some files of the year may have been started during the year; check them for events that were still missing or had not happened yet.
    After creating the files of the new year, run `python -m scripts.tools.datapackage`, so that `curated/datapackage.json` lists them; `make check` reports it as stale until then.

2.  Collect, derive and report the year in one run:

    ```shell
    make year YEAR=2025
    ```

    Without `YEAR`, the target uses the last completed year.
    It runs the steps in pipeline order:

    -   collect commits, merged pull requests, pull request interactions and PLIPs;
    -   write the organisation statistics of the year and the PLIPs per organisation;
    -   write the three-, five- and ten-year summaries that end with the year, and the yearly totals and graphs;
    -   write the contributor report and the community recognition report of the year.

    Most steps stop with an error if a file they need is missing.
    To repeat a single step, run its target, listed in {doc}`/reference/make-targets`.

3.  List the unmapped contributors worth researching, of all years:

    ```shell
    make analyze-independent
    ```

    Add an affiliation for those you can support with a public record, as described in {doc}`add-an-affiliation`.
    Then regenerate as described in {doc}`regenerate-after-a-mapping-change`.

4.  List the people of the register without a GitHub login who appear as a login, with proposals from GitHub profile names:

    ```shell
    python -m scripts.tools.unmatched_names --propose
    ```

    The tool prints rows for `curated/mappings/identities.csv`.
    Add the proposals you can confirm, see {doc}`link-old-commits-to-a-person`, and run `make community-page` again.

5.  Validate the curated files, run the tests and review the changed files:

    ```shell
    make check
    make test
    git status
    ```

    The summaries of the new year are new files, because their names contain the years they cover.

6.  Commit the collected data, the derived data and the reports together, and open a pull request.
