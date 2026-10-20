(explanation-history-and-coverage)=

# Thirty years of history

Plone's first commits date from 2002.
Its history moved through three version control systems and several ways of working before it reached today's pull requests on GitHub.
Each step left marks in the data.
This page explains what the data can and can't show for each era, so that you can compare years with care.

## From CVS through Subversion to Git

Plone started in CVS.
The CVS history was imported into Subversion, and in 2011 Subversion was migrated to Git with [svn-migrate](https://github.com/plone/svn-migrate).
The Git history therefore goes back to February 2002.
2001 is not in Git: the original CVS repository was on SourceForge and is no longer accessible.

CVS recorded commits per file.
The conversion grouped them into changesets, and initial imports and mass commits, such as translations, appear as single large commits.
Commit counts of the early years are therefore less comparable to later years than they look ([#67](https://github.com/plone/plone-contributor-statistics/issues/67)).

## History on release branches

When Plone moved to the egg structure around 2008, many packages got a new default branch.
In some repositories, the history from before that move exists only on the old release branches, such as `2.5` or `3.0`.
The default branch of `Products.CMFPlone`, for example, starts in 2008, while its branch `3.0` reaches back to 2002.

The collector therefore reads local clones of all repositories, with all their branches ([#75](https://github.com/plone/plone-contributor-statistics/pull/75)).
It counts the commits of the default branch, plus the commits of release branches that are older than the first commit of the default branch.
Later commits on release branches are mostly backports: the same change as on the default branch, with another commit ID.
They are not counted twice ([#68](https://github.com/plone/plone-contributor-statistics/issues/68)).

## Authors without a GitHub account

GitHub links a commit to an account by the author's email address.
The Subversion migration had no file that mapped Subversion users to email addresses.
Their commits carry addresses like `name@localhost`, which no GitHub account has.

Identities of the kind `email` in `curated/mappings/identities.csv` name the people behind these addresses, where a source says who they are.
Sources are the same name in commits that are linked to an account, the nicknames in the [credits of Plone 2.0](https://github.com/plone/Products.CMFPlone/blob/2.0/CREDITS.txt), account profiles, and confirmations by people who were there.
People without a GitHub account are counted under `person:<id>` and shown by their name ([#77](https://github.com/plone/plone-contributor-statistics/pull/77)).

Commits whose address nobody could identify yet are left out.
In the early years, they are still a noticeable share of the commits ([#69](https://github.com/plone/plone-contributor-statistics/issues/69)).

## Before pull requests

Pull requests on GitHub started for Plone around 2011.
Before that, developers committed directly to trunk, and changes were discussed on mailing lists and in the Trac ticket system.
For the years before 2011, the data therefore has commits but no pull requests, reviews or comments.

## Changelog entries before pull requests

The changelogs of the packages are a second record of those years ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).
The convention of ending an entry with the name of the person in brackets started in `Products.CMFPlone` in mid-2003, and from 2004 on almost every entry names a person.
The entries are collected for all years, but they say something of their own only from 2004 to 2012.

- **Before 2004**, few entries have a name, and big releases such as Plone 2.0 in March 2004 carry the work of the year before.
- **From 2004 to 2012**, the entries are the only record of who made a change besides the commits, and they credit people whose patches others committed.
- **From 2013 to 2015**, pull requests take over, and the entries begin to repeat them.
- **From 2016 on**, towncrier writes the entries from pull requests, mostly with the login of the pull request's author, so the entries repeat the pull request counts.

The contributor report therefore shows the changelog entries of 2004 to 2012.
The yearly files and the organisation statistics have them for all years.

Old changelogs often live in subfolders and on old release branches: the changelog of `Products.CMFPlone` moved between several files and folders over the years, and each release branch keeps the file of its time.
Many early entries exist only on release branches, so the collector reads them as well, and counts each entry once.

An entry is dated by its release, not by the day the work was done.
For entries that could be matched to the commit that added them, the release usually came a few weeks later, and some entries fall into a later calendar year than their commit.
Long release cycles, such as Plone 4.0, move more work into the next year.
Compare the entries of neighbouring years with this in mind.

PLIPs are older than GitHub, too.
From 2004 they were pages on plone.org, first in a wiki and then on the roadmap, and from 2008 tickets in Trac; they moved to GitHub issues at the end of 2013.
`curated/plips/plone-plips-before-github.csv` records the PLIPs of that time from archived copies of these pages.
The two numberings overlap, so some PLIPs appear twice, once as a roadmap PLIP and once as a Trac ticket.
Many records lack a date or the names of the implementers, and the Trac list is incomplete, so the PLIP statistics and the recognition don't use the file.

## Organisations in the early years

The {doc}`affiliations <attribution>` record where people worked, and for which years.
For the years before 2010, few affiliations are known with a source ([#70](https://github.com/plone/plone-contributor-statistics/issues/70)).
The commits and pull requests of a person in a year that no affiliation covers are Unmapped, so the early years show many Unmapped contributors.

The email addresses in commits from the Subversion period don't help here.
The conversion to Git assigned them, not the developers at the time of the commit.
Commits from 2002 already carry addresses at `jarn.com`, although Plone Solutions only announced its new name Jarn at the Plone Conference 2007 ([archived announcement](http://web.archive.org/web/20080124030609/http://www.jarn.com:80/)).
A company address therefore counts as evidence for an organisation only in commits that developers made in Git.

The curated data reaches back further for some kinds of work.
The organising organisations of every Plone Conference since 2003 are recorded; the rows from 2003 to 2019 also name the organisers and a public source.
Board members, release managers and team leaders are recorded with sources from 2004 on.
Sprints are recorded from 2003, and World Plone Day from its first edition in 2008.
Trainings are recorded from 2003, and podcasts start in 2020 ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).

## Best effort, and how you can help

The statistics reconstruct the history before GitHub from incomplete sources: the commits, the credits files, archived web pages, and the memory of people who were there.
It is a best effort.
Some of it is uncertain: who is behind an old Subversion name, and where someone worked in a given year.
Where no source supports an entry, it stays out, and the data misses that part of the history.

The people best placed to fill the gaps are the ones the data describes, and those who worked with them.
Their knowledge turns an unknown address into a person, and a guess about an employer into a fact with a source.
{doc}`/how-to/find-a-contributor` shows how to look someone up.
{doc}`/how-to/link-old-commits-to-a-person` and {doc}`/how-to/add-an-affiliation` show how to send a correction.
Comments in [#69](https://github.com/plone/plone-contributor-statistics/issues/69), about who is behind an address, and in [#70](https://github.com/plone/plone-contributor-statistics/issues/70), about organisations in the early years, help just as much.

## What this means for comparisons

Comparisons between recent years are on firm ground: the same sources, the same rules, and accounts for almost everyone.
Comparisons that reach back before 2011 compare commits only.
Comparisons that reach back before 2006 may still miss some authors.
And organisation statistics of the early years rest on few known affiliations, and the work of everyone else is Unmapped; until a follow-up trims them, some early affiliation rows only repeat today's organisation, and `notes` marks them.

```{seealso}
{doc}`method-history` shows when each of these limits was found and addressed.
```
