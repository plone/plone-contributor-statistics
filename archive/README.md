# Archive

Historical material: one-off analyses, proposals, snapshots and agent notes, mostly written with AI agents in 2025 and 2026.
The files are kept unchanged, at their original paths below `archive/` or, since 2026-10-18, in one folder per topic with their code, data and output together.
They are not maintained and do not describe the current method.
For the current method, see the documentation at https://plone.github.io/plone-contributor-statistics/ or in `docs/`.

| Original path | Added | Summary |
|---|---|---|
| `DATA-TRENDS.md` | 2025-08-24 | AI commentary on commit and pull request trends 2014–2024. |
| `FINAL-3-tier-plip-levels.md` | 2026-03-13 | Proposal for three PLIP contributor tiers, marked approved on 2025-11-03; superseded, the implemented PLIP levels differ. |
| `comparison-plone-vs-volto.md` | 2025-10-21 | One-off comparison of Plone core and Volto pull request metrics 2020–2025. |
| `contributor-levels.md` | 2025-10-21 | One-off classification of contributors by pull requests per year 2020–2025, with frozen lists. |
| `plone-core-team.md` | 2025-10-21 | One-off analysis of Plone core team contributions 2017–2025. |
| `plip-contributor-level-analysis/` | 2025-11-10 | Proposal bundle on PLIP and pull request contributor levels, with a snapshot of `plip-contributor-levels.md`. |
| `volto.md` | 2026-03-13 | Stale copy of the Volto report; the current one is `reports/volto.md`. |
| `team-volto.md` | 2025-10-21 | List of Volto team GitHub usernames; read by `volto_stats.py` until 2026-03-12. |
| `individual_contributors.txt` | 2025-08-22 | List of individual contributors, never read by a script; replaced by `Name (independent)` entries in `organisations.csv`. |
| `.claude/README.md` | 2026-03-07 | Conventions for AI agents; replaced by `AGENTS.md` and the documentation. |
| `specs-and-plans/` | 2026-10-18 | Design specs and implementation plans of past work, kept unchanged for transparency. |
| `legacy-collectors/` | 2026-10-18 | `plone_contributor_statistics.py` (GitHub contributor statistics API) and `plone_companies.py` (guessed organisations from profiles and email domains); replaced by the current collectors and the mapping files, Make targets `run-contributors` and `run-organisations`. |
| `plip-levels/` | 2026-10-18 | `analyze_plip_contributor_levels.py`, `generate_plip_3tier_levels.py` and the older PLIP counter `plip_stats.py`; PLIP level experiments that are not part of the method, see [#18](https://github.com/plone/plone-contributor-statistics/issues/18) and [#44](https://github.com/plone/plone-contributor-statistics/issues/44). |
| `package-statistics/` | 2026-10-18 | `npm_package_stats.py`, `volto_addon_discovery.py`, `pypi_package_statistics.py`, `npm_mapping.txt`, and the `npm-packages-*` files of a single run on 2025-08-20; the PyPI target was broken. |
| `cmfplone-releases/` | 2026-10-18 | `fetch_cmfplone_releases.py`, `filter_releases.py` and `cmfplone-releases.csv`; a list of Products.CMFPlone releases that no statistic used. |
| `flourish/` | 2026-10-18 | The two scripts that wrote chart data for Flourish, the chart data from `data/` (prefixed `data-`), and older copies and variants from the repository root. |
| `orphan-outputs/` | 2026-10-18 | `reports/plips.md`, whose generator was never in the repository, and `graphs/commits_prs_trend.png`, which the graph script no longer draws. |
