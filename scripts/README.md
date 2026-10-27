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
| `collect/` | Collectors: fetch commits, pull requests, pull request interactions, PLIPs and changelog entries from GitHub, and read the mail domains of the commit authors from the cached clones; the commit and pull request collectors need a GitHub token. |
| `derive/` | Compute organisation statistics, summaries, yearly totals, PLIPs per organisation and the data of the community page from the collected data and the registers. |
| `report/` | Write the human-facing reports and graphs, and render the community page (`site/` holds its templates and static files). |
| `tools/` | Helpers for maintainers, for example to find a person in the registers, check the curated data, generate the reference of the curated files, list unmapped contributors, propose affiliations from company addresses in commits (`address_proposals`) or from the GitHub commit search (`github_evidence`, needs a token), fill empty snippets from the quotes in the notes after a capture (`cite_snippets`), list the person-years whose organisation differs from a base commit (`attribution_changes`), or list the decisions for review (`decisions_review`). |
| `lib/` | Shared code: `paths.py` (where every file lives), `model/` (the only reader of `curated/`: the registers and the community data), `years.py` (default years), `github_api.py`, `git_history.py`, `changelogs.py` (reading changelog entries), `commit_authors.py` (the person and the mail domain of a commit author), `commit_domains.py` (reading the collected commit domains), and `capture/` (fetching a source and cutting the passages for the source register). |

Exceptions to the stages: `collect/plone_pr_interactions.py` also writes the pull request interaction reports, because they rank participants and reviewers by name, and the collected CSV files hold only counts per pull request; `derive/multi_year_summary.py` writes the text summaries in `reports/summaries/` next to its CSV files; `report/generate_community_recognition_report.py` writes its CSV file to `derived/community-recognition/`.

Code changes get offline tests in `tests/`; the GitHub API is replaced by fakes.
