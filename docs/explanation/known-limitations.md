(explanation-known-limitations)=

# Known limitations

Every statistic simplifies, and these are no exception.
This page collects the known limits in one place, with what each one means for reading the numbers.
Most of them have an open issue, and each fix will update this page.

## Coverage

Commits of unidentified authors don't count
:   Commits whose author email neither GitHub nor `curated/mappings/commit_authors.csv` links to a person are left out.
    This hits the CVS and Subversion years hardest ([#69](https://github.com/plone/plone-contributor-statistics/issues/69)).
    Early years may undercount people, especially the early core developers.

People without a GitHub account have no organisation
:   People counted under their name can't be listed in `curated/mappings/organisations.csv`, which holds GitHub logins, so they are Unmapped.

Duplicates are recognized by date and message
:   Two different commits in one repository with the same author date and message would count as one.

The early commit history is uneven
:   CVS commits were grouped into changesets during the conversion, and initial imports count as single commits ([#67](https://github.com/plone/plone-contributor-statistics/issues/67)).
    Compare commit counts of the early years with care.

No pull requests before about 2011
:   Plone worked without pull requests before it moved to GitHub.
    Pull request counts and interactions of the early years are zero by method, not by lack of activity ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).

Organisations of the early years are mostly unknown
:   The mapping records today's organisations, with few known exceptions before 2010 ([#70](https://github.com/plone/plone-contributor-statistics/issues/70)).
    Early organisation statistics reflect where people are today.
    The email addresses of the Subversion period don't help, because the conversion to Git assigned them ({doc}`history-and-coverage`).

Zope and other Foundation projects are not counted
:   Their repositories are outside the `plone` organisation, and how to count them is open ([#58](https://github.com/plone/plone-contributor-statistics/issues/58)).

Work outside GitHub is counted only where curated data exists
:   Documentation outside GitHub, marketing, and help in the forum are not recorded ([#35](https://github.com/plone/plone-contributor-statistics/issues/35)).
    Trainings and podcasts are recorded from 2020 on; conference organisers and sprints from 2003, Board members, release managers and team leaders from 2004, and World Plone Day from 2008 ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).
    Most World Plone Day events before 2020 are known only from their announcement.

## Counting

Only the opener of a pull request gets the credit
:   Co-authors and reviewers of a pull request get none.
    Review and merge work is collected per pull request, but not credited to people ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

The committer date decides the year
:   A rebased or cherry-picked commit can count for a later year than the one in which it was written.

Multi-year summaries split people who moved
:   A person who changed organisations appears under each organisation, for the years they were there.

Login lookup is case-sensitive
:   A login with the wrong case in `curated/mappings/organisations.csv` leaves its owner Unmapped.

## Parts with a different method

PLIPs
:   PLIPs are read from the four repositories where a PLIP can live: `Products.CMFPlone`, `volto`, `plone.restapi` and `aurora`, the new UI after Volto, where the PLIPs of Seven moved from Volto.
    Other repositories of the `plone` organisation use the PLIP label for issues related to a PLIP; those issues are not PLIPs themselves and are not counted.
    A closed PLIP stands in for a merged and released one, although most PLIPs are closed as completed ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).
    The PLIPs from before GitHub are recorded in `curated/plips/plone-plips-before-github.csv`, but not counted.

Community recognition
:   The levels published in August 2026 were calculated outside the repository, and they differ from the script's levels on the current data ({doc}`community-recognition`).

Yearly activity
:   `scripts/derive/yearly_activity_analysis.py` counts Unmapped as an organisation.
