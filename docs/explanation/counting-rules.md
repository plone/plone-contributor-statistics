(explanation-counting-rules)=

# How contributions are counted

A commit or a pull request seems easy to count.
In practice, every count depends on small decisions: which date decides the year, who gets the credit, and what is not a contribution at all.
This page explains those decisions and why they were made.

## A commit belongs to its author

GitHub links a commit to the account whose email address is the commit's author address.
The collector does the same: it reads the commits from local clones and asks the GitHub GraphQL API which account each new email address belongs to.
Commits without a linked account are left out, because there is no way to tell who made them.
{doc}`history-and-coverage` explains why this matters most for the early years.

A commit counts for the year of its committer date.
The committer date is when the commit was added to the history, the author date is when the change was first written.
The two differ when a commit is rebased or cherry-picked, and then a commit can land in a later year than the one it was written in.

## Merge commits are not contributions

When someone merges a pull request with GitHub's merge button, GitHub creates a merge commit and makes the person who merged its author.
Counting those commits gave maintainers an extra commit for every pull request they merged.
For some maintainers, that was about a third of their commits.

Merging is not writing code, and how often it creates a commit depends on each repository's merge strategy.
So commits with more than one parent are not counted ([#39](https://github.com/plone/plone-contributor-statistics/issues/39)).
Review and merge work deserves recognition of its own, which is still open ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

## A pull request belongs to the person who opened it

A merged pull request counts for the person who opened it, not for people who pushed commits to it or reviewed it.
It counts for the year it was merged, the moment the project accepted it.

The same rule applies to the core repositories and to Volto ([#42](https://github.com/plone/plone-contributor-statistics/issues/42)).

Pull requests to any branch count, including backports to maintenance branches.
A backport is work of its own: it needs to be adapted, tested and released.

## Bots don't count

Bots open pull requests, push commits and write comments, sometimes more than people do.
The statistics leave them out.
A bot is recognized by its account type, by the `[bot]` suffix of GitHub Apps, or by an entry in `bot_accounts.csv` for bots that GitHub lists as users.
Commits and pull requests of deleted accounts are left out as well, because they can't be attributed to anyone.

## Each repository is read once

Each repository's commits and pull requests are read once for the whole time range and then assigned to the years ([#63](https://github.com/plone/plone-contributor-statistics/pull/63)).
Asking per contributor and per year would need many thousands of requests per year, and the contributor list of the GitHub API stops after 500 people.
Reading whole repositories needs few requests and misses nobody.

## An error stops the run

GitHub limits how many requests a client may send.
The collector waits when GitHub asks it to, and stops on any other error.
An interrupted run writes only a checkpoint file and never replaces the data files ([#41](https://github.com/plone/plone-contributor-statistics/issues/41)).

A failed request must never look like a year without activity.
Wrong zeros are worse than no data, because nobody notices them.

```{seealso}
{doc}`/reference/data-files` describes the columns of the files these rules produce.
```
