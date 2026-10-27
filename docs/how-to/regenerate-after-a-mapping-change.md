(how-to-regenerate-after-a-mapping-change)=

# Regenerate the statistics after a mapping change

This guide shows you how to update the organisation statistics and reports after a change to the registers.
For a change to the affiliations, the citations or the sources you don't need a GitHub token, because nothing is collected from GitHub again.
The organisation of a person in a year is computed from the affiliations, their citations and the sources they cite, see {ref}`explanation-attribution-rules`.
So a change to `curated/mappings/citations.csv` or to the source register can change the organisation statistics as much as a change to `curated/mappings/affiliations.csv`.
The collected commit domains in `collected/commit-domains/` feed the tie-breaks by commits and by own statement (rules 6b and 6c) as well, so a new `make run-commit-domains` can change them too.
`python -m scripts.tools.affiliation jane-doe` shows the organisations of a person before you regenerate.
`python -m scripts.tools.attribution_changes` lists every person and year with credited work that counts for another organisation than at a base commit (`--base`, by default where your branch left `origin/main`), with the rule and what was credited in the year (`--all-years` adds the years without): run it to see the effect of a mapping change.

1.  Install the dependencies, if you haven't yet:

    ```shell
    make install
    ```

    A change to the identities in `curated/mappings/identities.csv` needs the collected files that map identities to be made again first, because the collectors map them at collection time: `make run-changelogs` for the names and `make run-commit-domains` for the commit domains, neither of which needs a token.
    For an `email` or a `github-alias` identity, the commits need to be collected again as well, with `make run-stats-all-years`, which needs a token, see {doc}`collect-data-again`.

2.  Regenerate the organisation statistics of all years, and the PLIPs per organisation:

    ```shell
    make run-organisation-stats
    make run-plip-organisations
    ```

    If the change affects only one year, run `make run-organisation-stats-year YEAR=2025` with that year instead of `make run-organisation-stats`.

3.  Regenerate the summaries and the reports:

    ```shell
    make three-year-summary
    make five-year-summary
    make ten-year-summary
    make yearly-graphs
    make generate-report
    ```

    `make yearly-graphs` writes the yearly totals with `make yearly-activity` first.

4.  Regenerate the community recognition and the data of the community page, which credit work to the organisation of each person in the year:

    ```shell
    make community-recognition
    make community-page
    ```

5.  Run the tests and review the changed files:

    ```shell
    make test
    git diff --stat
    ```

    `tests/test_reproducible_outputs.py` regenerates the derived data and reports in a temporary copy and compares them with the committed files.
    It fails if an input changed and a file wasn't regenerated, and names the file.

{doc}`/reference/make-targets` lists all targets.
