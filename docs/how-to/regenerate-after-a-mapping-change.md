(how-to-regenerate-after-a-mapping-change)=

# Regenerate the statistics after a mapping change

This guide shows you how to update the organisation statistics and reports after a change to the registers.
You don't need a GitHub token, because nothing is collected from GitHub again.
The organisation of a person in a year is computed from the affiliations, their citations and the sources they cite, see {ref}`explanation-attribution-rules`.
So a change to `curated/mappings/citations.csv` or to the source register can change the organisation statistics as much as a change to `curated/mappings/affiliations.csv`.
The collected commit domains in `collected/commit-domains/` feed the tie-break by commits (rule 6b) as well, so a new `make run-commit-domains` can change them too.
`python -m scripts.tools.affiliation jane-doe` shows the organisations of a person before you regenerate.
`python -m scripts.tools.attribution_changes` lists every person and year that counts for another organisation than at a base commit (`--base`, by default where your branch left `origin/main`), with the rule and what was credited in the year: run it to see the effect of a mapping change.

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
