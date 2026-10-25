(how-to-prepare-a-new-year)=

# Prepare the numbers for a new year

This guide shows you how to add a completed year to the statistics.
You need a GitHub personal access token, see {doc}`collect-data-again` for how to set it up.

1.  Add or complete the curated community data of the year in `curated/community/`, each row with a public record, as described in {doc}`add-curated-community-data`.
    Some rows of the year may have been added during the year; check the events of the year for those that were still missing or had not happened yet.
    The files hold the rows of every year, so a new year needs no new files, only rows: the events with their organisers, talks and trainings, and the roles with the year in their `year` column.
    The Plone Conference of the year is the event `plone-conference-<year>`: add its row to `curated/community/events.csv` first, then the organisers, talks and trainings that point to it.

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

    The tool prints, per person, a row for `curated/mappings/identities.csv`: an identity of the kind `github` with the login, citing the GitHub profile, with the profile name as the snippet.
    It writes nothing: above each row it prints the command that captures the profile, as `# capture first: …`.
    For the logins you can confirm, run the capture command, add the row in its place sorted by person, kind and value, and run `make community-page` again.

5.  Validate the curated files, run the tests and review the changed files:

    ```shell
    make check
    make test
    git status
    ```

    The summaries of the new year are new files, because their names contain the years they cover.

6.  Commit the collected data, the derived data and the reports together, and open a pull request.
