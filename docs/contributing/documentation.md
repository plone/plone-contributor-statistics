(contributing-documentation)=

# Contribute to the documentation

This documentation describes the method of the statistics, so it must change together with the method.

## The documentation rule

A pull request that changes anything the documentation describes — a data source, a collection or counting rule, the attribution rules, a mapping or exclusion convention, a file's format or location, or a Make target — must update `docs/` in the same pull request.

The pull request template asks for this.
A reviewer should not merge a pull request that changes the method without changing the documentation.

## Build the documentation

1.  Install the documentation dependencies:

    ```shell
    make docs-install
    ```

2.  Build the HTML:

    ```shell
    make docs
    ```

    The build treats warnings as errors.
    Open `docs/_build/html/index.html` in a browser to read the result.

3.  Run the tests, which also check that every file and Make target the documentation names exists:

    ```shell
    make test
    ```

Every pull request builds the documentation in GitHub Actions.
Every change on `main` publishes it to https://plone.github.io/plone-contributor-statistics/docs/, below the community page at https://plone.github.io/plone-contributor-statistics/.
To preview both together, run `make site site-serve`.

## Style

The documentation follows the [Plone documentation style guide](https://6.docs.plone.org/contributing/documentation/index.html).
In short:

- Write one sentence per line.
- Use American English, the active voice, and sentence case in headings.
- Give each page one purpose: explanation, reference or how-to guide.
- Explain the method and its reasons, not the numbers it produces.
- Describe the current state in explanation, reference and how-to pages.
  What changed over time, and what didn't work before, belongs in {doc}`/explanation/method-history`.

## Specs and plans

Draft specs and plans for larger changes outside `docs/`.
As the last step before opening the pull request, add them unchanged to `archive/specs-and-plans/` with a dated filename, for transparency.
