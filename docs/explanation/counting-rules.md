(explanation-counting-rules)=

# How contributions are counted

A commit or a pull request seems easy to count.
In practice, every count depends on small decisions: which date decides the year, who gets the credit, and what is not a contribution at all.
This page explains those decisions and why they were made.

## A commit belongs to its author

GitHub links a commit to the account whose email address is the commit's author address.
The collector does the same: it reads the commits from local clones and asks the GitHub GraphQL API which account each new email address belongs to.

Many old addresses belong to no account today: Subversion users like `name@localhost`, or company addresses that people no longer use.
For these, an identity of the kind `email` in `curated/mappings/identities.csv` names the person behind the address, each with a source (a masked address, see {ref}`masked-addresses`; the collector hashes the commit address and compares), or, for an early commit address, with notes that say what the identification rests on ([#77](https://github.com/plone/plone-contributor-statistics/pull/77)).
A person with a GitHub account is counted under the login of their identity of the kind `github`, a person without one as `person:<id>`.
Commits whose address is neither linked by GitHub nor an identity are left out, because there is no way to tell who made them.
{doc}`history-and-coverage` explains why this matters most for the early years.

Some people have a second GitHub account that GitHub links to an old address.
An identity of the kind `github-alias` counts such an account for the person, for commits and pull requests.

A commit counts for the year of its committer date.
The committer date is when the commit was added to the history, the author date is when the change was first written.
The two differ when a commit is rebased or cherry-picked, and then a commit can land in a later year than the one it was written in.

## A change counts once

Some changes exist twice in the history, with different commit IDs.
`buildout.coredev` contains automatic copies of the commits in the core packages, marked `[fc]` and made under the original author's name.
They are not counted, because the original commit already is.
Within a repository, commits with the same author date and message are the same change, for example a rebased branch that was merged as well, or history that was imported twice.
They are counted once ([#78](https://github.com/plone/plone-contributor-statistics/issues/78)).

## Merge commits are not contributions

When someone merges a pull request with GitHub's merge button, GitHub creates a merge commit and makes the person who merged its author.
Counting those commits gave maintainers an extra commit for every pull request they merged.
For some maintainers, that was a large share of their commits.

Merging is not writing code, and how often it creates a commit depends on each repository's merge strategy.
So commits with more than one parent are not counted ([#39](https://github.com/plone/plone-contributor-statistics/issues/39)).
Review and merge work deserves recognition of its own, which is still open ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

## A pull request belongs to the person who opened it

A merged pull request counts for the person who opened it, not for people who pushed commits to it or reviewed it.
It counts for the year it was merged, the moment the project accepted it.

The same rule applies to every repository, Volto included ([#42](https://github.com/plone/plone-contributor-statistics/issues/42)).

Pull requests to any branch count, including backports to maintenance branches.
A backport is work of its own: it needs to be adapted, tested and released.

## A changelog entry belongs to the people it names

Before pull requests, the changelogs of the packages said who made a change.
From 2003 on, an entry ends with the name of the person in brackets, such as `[limi]`; towncrier entries from 2016 on end with `@login` ([#71](https://github.com/plone/plone-contributor-statistics/issues/71)).
The changelog collector reads these entries from the changelog files at the tips of the default branch and the release branches of every repository.
It needs no file history, because the tip of a changelog holds all of its entries.

An entry counts for the year of the release it is listed under.
The release header gives the date; when it has none, the date of the release's tag does.
Entries without a release date, such as unreleased sections, don't count.
The release date is simple and reproducible, but it is later than the work, see {doc}`history-and-coverage`.

Each entry exists several times: on every later release branch, in files that moved within a repository, and in copies between repositories.
The same text, names included, counts once within a repository, for its earliest release.
Across repositories, the same text counts once when it is long enough not to be generic, or when both copies have the same release date.
A short text such as "Initial release" therefore still counts in each package that has it.
A backport whose text was edited counts twice, in line with the rule that a backport is work of its own.

An entry with several names counts in full for each person, as joint work does elsewhere in the statistics.
Names that are no person, such as `[plone devs]`, placeholders such as "Nothing changed yet", and bots don't count.

The names are mapped to people with the identities, see {doc}`attribution` and {ref}`reference-curated-files`.
A name maps through the layers named in the `matched_by` column: `identity` for a name, an address, a login or a second account that the registers know, and `login` for a login with commits or pull requests.
The names of bots are left out, so they never appear in the files.
A name that nothing maps counts as written, as `unmatched`, and belongs to no organisation.
The collected changelog files are still those of the run before the registers, and carry the older layer names, see {doc}`known-limitations`.

Names of one word, such as the nicknames of the Subversion years, match as well, if the registers list them as an identity of the kind `name`.
A display name in `curated/mappings/people.csv` matches only when it has more than one word, since a one-word display name is often a login or a first name that nobody checked against the changelogs.
So does the identity of the kind `name` that holds the name of a person without a GitHub account, the record of their name.
A name that the identities give to two people maps to neither, because nothing tells them apart.
The policy for short names governs them: a short name that several people may have used, such as a first name, is added only when the records show that one person used it in the changelogs.
Two rules are not identities of their own: a name that equals a login with commits or pull requests, and the part before the `@` of the Subversion address of an `email` identity.

## Changelog entries are shown, not added

The organisation statistics, the summaries and the contributor report show the changelog entries in a column of their own, next to commits and pull requests.
They are never added to the commits or the pull requests, and the order of the tables stays the order by commits or pull requests.

An entry and a commit measure the same work in two ways: most changes have both.
Adding them would count that work twice.
How many commits a person makes for one entry is personal habit, so neither number is a fair conversion of the other.
Shown side by side, the entries are a second view of the years before pull requests, and they make visible people whose work others committed.
The report shows them for the years in which almost every entry names a person and pull requests didn't exist yet, see {doc}`history-and-coverage`.
The community recognition doesn't use them.

## Bots don't count

Bots open pull requests, push commits and write comments, sometimes more than people do.
The statistics leave them out.
A bot is recognised by its account type, by the `[bot]` suffix of GitHub Apps, or by an entry in `curated/mappings/bot_accounts.csv` for bots that GitHub lists as users.
Commits of deleted accounts are left out as well, because GitHub links their addresses to no account and they can't be attributed to anyone.
Pull requests of deleted accounts are still counted, under the login `ghost` and as Unmapped, see {doc}`known-limitations`.

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
