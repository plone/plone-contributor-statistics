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

The collector counts only commits that are linked to a GitHub account, so these commits are left out.
In the early years, this is a considerable share of the commits, and it hits the early core developers most ([#69](https://github.com/plone/plone-contributor-statistics/issues/69)).
A mapping from these addresses to people would bring them back.

## Before pull requests

Pull requests on GitHub started for Plone around 2011.
Before that, developers committed directly to trunk, and changes were discussed on mailing lists and in the Trac ticket system.
For the years before 2011, the data therefore has commits but no pull requests, reviews or comments.
Changelog entries could serve as a measure for those years ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).

## Organisations in the early years

The {doc}`organisation mapping <attribution>` records where people work today, with exceptions for past years.
For the years before 2010, few of these past affiliations are known with a source ([#70](https://github.com/plone/plone-contributor-statistics/issues/70)).
Organisation statistics of the early years therefore show today's organisations of the people, unless an override says otherwise.

The curated data reaches back further in one place: the organising organisations of every Plone Conference since 2003.
The rows from 2003 to 2019 also name the organisers and a public source.
Other curated data, such as sprints, Board members and release managers, starts in 2020 ([#72](https://github.com/plone/plone-contributor-statistics/issues/72)).

## What this means for comparisons

Comparisons between recent years are on firm ground: the same sources, the same rules, and accounts for almost everyone.
Comparisons that reach back before 2011 compare commits only.
Comparisons that reach back before 2006 also miss many authors.
And organisation statistics of the early years say more about where people are today than about who sponsored their work then.

```{seealso}
{doc}`method-history` shows when each of these limits was found and addressed.
```
