(explanation-known-limitations)=

# Known limitations

Every statistic simplifies, and these are no exception.
This page collects the known limits in one place, with what each one means for reading the numbers.
Most of them have an open issue, and each fix will update this page.

## Coverage

Only GitHub activity of linked accounts counts
:   Commits whose author email belongs to no GitHub account are left out.
    This hits the CVS and Subversion years hardest ([#69](https://github.com/plone/plone-contributor-statistics/issues/69)).
    Early years undercount people, and especially the early core developers.

The early commit history is uneven
:   CVS commits were grouped into changesets during the conversion, and initial imports count as single commits ([#67](https://github.com/plone/plone-contributor-statistics/issues/67)).
    Compare commit counts of the early years with care.

No pull requests before about 2011
:   Plone worked without pull requests before it moved to GitHub.
    Pull request counts and interactions of the early years are zero by method, not by lack of activity ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).

Organisations of the early years are mostly unknown
:   The mapping records today's organisations, with few known exceptions before 2010 ([#70](https://github.com/plone/plone-contributor-statistics/issues/70)).
    Early organisation statistics reflect where people are today.

Zope and other Foundation projects are not counted
:   Their repositories are outside the `plone` organisation, and how to count them is open ([#58](https://github.com/plone/plone-contributor-statistics/issues/58)).

Work outside GitHub is counted only where curated data exists
:   Documentation outside GitHub, marketing, and help in the forum are not recorded ([#35](https://github.com/plone/plone-contributor-statistics/issues/35)).
    Curated community data starts in 2020, except for conference organisers ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).

## Counting

Only the opener of a pull request gets the credit
:   Co-authors and reviewers of a pull request get none.
    Review and merge work is collected per pull request, but not credited to people ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

The committer date decides the year
:   A rebased or cherry-picked commit can count for a later year than the one in which it was written.

Multi-year summaries split people who moved
:   A person who changed organisations appears under each organisation, for the years they were there.

Login lookup is case-sensitive
:   A login with the wrong case in `organisations.csv` leaves its owner Unmapped.

## Parts that use an older method

Volto statistics
:   `volto_stats.py` uses another method than the core collector: the contributor list of the API, which stops after 500 people, a search request per person, and the branch `main`.
    Its data and `reports/volto.md` were last generated before the fixes for merge dates and merge commits, and before the split of Unmapped and independent contributors.

PLIPs
:   PLIPs are read from three repositories only.
    A closed PLIP stands in for a merged and released one, although most PLIPs are closed as completed ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).
    `plone_plips.py` doesn't use the GitHub token, and `plip_stats.py --year` fails ([#44](https://github.com/plone/plone-contributor-statistics/issues/44)).
    The generator of `plone-plip-organisations.csv` is not in the repository, and the file still uses old organisation names.

Community recognition
:   The published levels can't be reproduced from the repository, and the script and the points file disagree ({doc}`community-recognition`).
    `reports/community-recognition.md` was generated before the split of Unmapped and independent contributors.

Board of Directors
:   The organisations come from heuristics on the board members' biographies on plone.org, and the files have no source column.

Packages on npm and PyPI
:   They are one-off snapshots, and the organisations are guessed from scopes, search terms and author fields.

Yearly activity and charts
:   `yearly_activity_analysis.py` counts Unmapped as an organisation.
    The Flourish charts use commits instead of pull requests, a fixed range of years, and old spellings of some organisation names.

## Broken Make targets

`make run-plip-organisations`, `make generate-plip-report` and `make pypi-packages` call scripts that are not in the repository: `plip_organisation_stats.py`, `generate_plip_report.py` and `pypi_package_stats.py`.
`make run-all` depends on a target that doesn't exist.
{doc}`/reference/make-targets` lists their status.
