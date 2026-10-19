# Scripts

The code of the statistics, one folder per pipeline stage.
Run the scripts through `make`, see `make help` and the [Make targets](https://plone.github.io/plone-contributor-statistics/docs/reference/make-targets.html).
To run one directly, run it as a module from the repository root, for example:

```shell
python -m scripts.collect.plone_contributors --year 2025
python -m scripts.tools.get_github_name <login>
```

Every script answers `--help`.
Running a file directly (`python scripts/collect/plone_contributors.py`) fails with `ModuleNotFoundError: No module named 'scripts'`.

| Folder | Holds |
|---|---|
| `collect/` | Collectors: fetch commits, pull requests, pull request interactions, PLIPs and changelog entries from GitHub; most of them need a GitHub token. |
| `derive/` | Compute organisation statistics, summaries, yearly totals and PLIPs per organisation from the collected data and the mapping files. |
| `report/` | Write the human-facing reports and graphs. |
| `tools/` | Helpers for maintainers, for example to find a person in the registers, check the curated data, generate the reference of the curated files, or list unmapped contributors. |
| `lib/` | Shared code: `paths.py` (where every file lives), `model/` (the only reader of `curated/`: the registers and the community data), `years.py` (default years), `github_api.py`, `git_history.py` and `changelogs.py` (reading changelog entries). |

One exception to the stages: `collect/plone_pr_interactions.py` also writes the pull request interaction reports, because they rank participants and reviewers by name, and the collected CSV files hold only counts per pull request.

Code changes get offline tests in `tests/`; the GitHub API is replaced by fakes.
