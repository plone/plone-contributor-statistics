(how-to-collect-data-again)=

# Collect the data again

This guide shows you how to collect commits, pull requests, pull request interactions and changelog entries from GitHub again.
You need a GitHub personal access token, git, and a few hundred megabytes of disk space.

## Set up the token

1.  Create the `.env` file:

    ```shell
    make setup
    ```

2.  Replace the placeholder in `.env` with your token:

    ```text
    GITHUB_TOKEN=your_token
    ```

    Never commit `.env`.
    Instead of the file, you can also set `GITHUB_TOKEN` in the environment.

The `make` targets run the scripts as modules from the repository root, for example `python -m scripts.collect.plone_contributors --year 2025`.
Run a script yourself the same way; `python scripts/collect/plone_contributors.py` fails with `ModuleNotFoundError: No module named 'scripts'`.
Every script answers `--help`.

## Collect commits and pull requests

To collect all years from 2003 to the current year in one run:

```shell
make run-stats-all-years
```

To collect one year, run `make run-stats YEAR=2025` with that year instead.

The first run clones all repositories into `.cache/repositories/`.
The clones hold only the commit history, and later runs update them.

## Collect pull request interactions

To collect all years from 2010 to the current year in one run:

```shell
make pr-interactions-all-years
```

To collect one year, run `make pr-interactions YEAR=2025` with that year instead.

## Collect changelog entries

To collect the changelog entries of all years in one run:

```shell
make run-changelogs
```

The collector reads the changelog files from the clones in `.cache/repositories/`, and fetches only the files it needs into them.
It uses the token only to list the repositories, so it also works without one.

## Collect commit mail domains

To collect the mail domains of the commit authors of all years from the clones, which `make run-changelogs` fills:

```shell
make run-commit-domains
```

It needs no token and no network.
It stores only the domains, never the local part of an address.

## If a run stops

When GitHub's rate limit is reached, the collectors wait until it resets and then go on.
On any other error, they stop with exit status 1.

A stopped or interrupted run of the commit collector writes its progress to `collected/contributors/<label>_checkpoint.csv` and never replaces the regular data files.
Fix the cause, for example an expired token, and start the run again.
Delete the checkpoint files when the run succeeded.

## Update everything else

After a new collection, regenerate the organisation statistics and reports as described in {doc}`regenerate-after-a-mapping-change`.

{doc}`/explanation/counting-rules` explains what the collectors count.
