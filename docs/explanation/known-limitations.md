(explanation-known-limitations)=

# Known limitations

Every statistic simplifies, and these are no exception.
This page collects the known limits in one place, with what each one means for reading the numbers.
Most of them have an open issue, and each fix will update this page.

## Coverage

Commits of unidentified authors don't count
:   Commits whose author email neither GitHub nor an identity in `curated/mappings/identities.csv` links to a person are left out.
    This hits the CVS and Subversion years hardest ([#69](https://github.com/plone/plone-contributor-statistics/issues/69)).
    Early years may undercount people, especially the early core developers.

People without an affiliation are Unmapped
:   A person has an organisation only in the years that the attribution rules give one: years that an affiliation row covers, or that a bridge between two records of one organisation fills.
    People without any row, among them many people without a GitHub account, are Unmapped.

Open cases are Unmapped
:   A year in which the records name several organisations and no rule or decision decides is an open case, and counts as Unmapped until a decision settles it; `make check` warns about each ({ref}`explanation-attribution-rules`).

Bridging credits years that no record names
:   Two records of one organisation cover the years between them, however many they are, when no record names another organisation in between.
    This is a convention of the yearly statistics, and a bridged year can count for an organisation that the person had left for a while without a public record of it ({doc}`attribution`).

Duplicates are recognised by date and message
:   Two different commits in one repository with the same author date and message would count as one.

The early commit history is uneven
:   CVS commits were grouped into changesets during the conversion, and initial imports count as single commits ([#67](https://github.com/plone/plone-contributor-statistics/issues/67)).
    Compare commit counts of the early years with care.

No pull requests before about 2011
:   Plone worked without pull requests before it moved to GitHub.
    Pull request counts and interactions of the early years are zero by method, not by lack of activity ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).

Organisations of the early years are mostly unknown
:   Few affiliations before 2010 are known with a source ([#70](https://github.com/plone/plone-contributor-statistics/issues/70)).
    A year that the attribution rules give no organisation is Unmapped, so early organisation statistics show many Unmapped contributors.
    The migration to the registers wrote the result of the old default, today's organisation for every year, as explicit rows; those that only the old default produced have the status `assumed`, cover only the years in which the person has commits, pull requests or a community role, count only in years that no stated row covers and no bridge fills, and stay until a record verifies or replaces them ([#139](https://github.com/plone/plone-contributor-statistics/issues/139)).
    The email addresses of the Subversion period don't help, because the conversion to Git assigned them ({doc}`history-and-coverage`).

Changelog names without a mapping
:   Many early changelog entries are signed with a nickname, such as `alecm` or `timo`, that no identity links to a person yet.
    They count under the name as written and belong to no organisation, so one person can appear twice, under a nickname and under a login ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).
    {doc}`/how-to/link-old-commits-to-a-person` shows how to link a name.

Commits can name the committer instead of the author
:   `python -m scripts.tools.unmatched_changelog_names --propose` proposes the person behind a changelog name from the commits that repeat its entries.
    When someone committed another person's patch, the commit names the committer, and the proposal names the wrong person.
    Each proposal is therefore checked before it is added, never applied automatically.

GNU-style ChangeLogs are not read
:   A few old products kept a ChangeLog of dated records with a name and an email address, instead of release sections.
    The collector skips these files, and with them their records from the early years.

Zope and other Foundation projects are not counted
:   Their repositories are outside the `plone` organisation, and how to count them is open ([#58](https://github.com/plone/plone-contributor-statistics/issues/58)).

Work outside GitHub is counted only where curated data exists
:   Documentation outside GitHub, marketing, and help in the forum are not recorded ([#35](https://github.com/plone/plone-contributor-statistics/issues/35)).
    How far back each kind of curated data reaches is described in {ref}`curated-data-coverage` ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).
    Most World Plone Day events before 2020 are known only from their announcement.

## Counting

Only the opener of a pull request gets the credit
:   Co-authors and reviewers of a pull request get none.
    Review and merge work is collected per pull request, but not credited to people ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

Changelog entries are dated by their release
:   An entry counts for the year of the release it is listed under, which is often weeks and sometimes more than a year after the work ({doc}`history-and-coverage`).

Changelog habits differ
:   Some people wrote one entry for many commits, others an entry for almost every commit, and some changes have no entry at all.
    That is why entries are shown next to commits and never added to them ({doc}`counting-rules`).

Changelog entries of organisations without code work in the year are not shown
:   The organisation statistics have one row per organisation with commits or pull requests in the year.
    An organisation whose people have changelog entries in a year, but no commits or pull requests, gets no row, and its entries are not shown, not even under Unmapped; they remain in the yearly changelog file ([#137](https://github.com/plone/plone-contributor-statistics/issues/137)).
    This affects few entries.

The collected changelog files are from before the registers
:   The files in `collected/changelogs/` were collected before the registers, and their `matched_by` column still carries the layer names of that time, `commit_authors` and `fullname`, where the collector now writes `identity` ([#137](https://github.com/plone/plone-contributor-statistics/issues/137)).
    The next `make run-changelogs` brings them to the current layers.

Pull requests of deleted accounts count as Unmapped
:   GitHub returns the author of a pull request whose account was deleted as the user `ghost`, and the collector counts these pull requests under the login `ghost`, as Unmapped ([#180](https://github.com/plone/plone-contributor-statistics/issues/180)).
    Commits of deleted accounts are left out, as {doc}`counting-rules` says.

The committer date decides the year
:   A rebased or cherry-picked commit can count for a later year than the one in which it was written.

Multi-year summaries split people who moved
:   A person who changed organisations appears under each organisation, for the years they were there.

A mistyped login leaves its owner Unmapped
:   Logins are compared ignoring case, but a typo in `curated/mappings/identities.csv` sends the person's work to Unmapped.
    The checks cannot catch a typo that is itself a valid login.

## Parts with a different method

PLIPs
:   PLIPs are read from the four repositories where a PLIP can live: `Products.CMFPlone`, `volto`, `plone.restapi` and `aurora`, the new UI after Volto, where the PLIPs of Seven moved from Volto.
    Other repositories of the `plone` organisation use the PLIP label for issues related to a PLIP; those issues are not PLIPs themselves and are not counted.
    A closed PLIP stands in for a merged and released one, although most PLIPs are closed as completed ([#14](https://github.com/plone/plone-contributor-statistics/issues/14)).
    The PLIPs from before GitHub are recorded in `curated/plips/plone-plips-before-github.csv`, but not counted.

Community recognition
:   The levels published in August 2026 were calculated outside the repository, and they differ from the script's levels on the current data ({doc}`community-recognition`).
    The script differs from the points file for community sprints, team leaders and podcasts, see {doc}`community-recognition` ([#56](https://github.com/plone/plone-contributor-statistics/issues/56)).

Yearly activity
:   `scripts/derive/yearly_activity_analysis.py` counts Unmapped as an organisation.

## Sources and tools

Source dates can lie in another year than the page
:   An archived copy is dated by the day of its capture, which can lie years after the date the page itself shows, and the capture takes a placeholder date such as 2000-01-01 that a page shows ([#183](https://github.com/plone/plone-contributor-statistics/issues/183)).
    Rules 6c and 6d of the attribution count the sources dated in a year, so such a date can move a source into another year.
    These dates are corrected by hand when there is evidence for the right one, see {doc}`/how-to/capture-a-source`.

The clones are those of the current directory
:   The collectors and the tools that read the Git clones use `.cache/repositories/` of the current directory, not the shared cache of the main checkout that the capture uses, and `PLONE_STATS_CACHE` doesn't move them ([#182](https://github.com/plone/plone-contributor-statistics/issues/182)).
    In a worktree, they find no clones: `python -m scripts.tools.address_proposals` stops with `No clones`, and `python -m scripts.tools.unmatched_changelog_names` reports no names without an error.
    Run them from the main checkout, or pass `--cache` where a tool takes it.

`make year` doesn't collect the changelog entries and the commit domains
:   `make year` runs neither `make run-changelogs` nor `make run-commit-domains` ([#181](https://github.com/plone/plone-contributor-statistics/issues/181)).
    Without them, the organisation file of the new year has no changelog entries, and rules 6b and 6c of the attribution have no commit domains for the year; {doc}`/how-to/prepare-a-new-year` names them as extra steps.
