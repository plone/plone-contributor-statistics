(explanation-pr-interactions)=

# Pull request interactions

Commits and merged pull requests show who writes the code.
They don't show who reads it, answers questions, and helps others get their changes in.
The pull request interactions are an attempt to make that part of the work visible.

## What is counted

For each pull request, the collector counts the comments on the pull request, the comments on lines of code, and the submitted reviews with their verdicts.
Pending reviews that were never submitted don't count.
It also records how many people took part, and how long it took until someone other than the author responded.

The counts are kept per pull request, not per person.
They describe how the project works together, but they don't credit anyone yet ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

## Every pull request counts, merged or not

Contribution statistics count only merged pull requests, because only those became part of Plone.
For interactions, that rule would hide exactly the work that matters: a careful review that leads to a pull request being closed is still work for the project.
So interactions are collected for pull requests in any state.

A pull request belongs to the year it was created.
Many of these pull requests were never merged, so the creation date is the one date they all have.

## Bots are left out

Bots once opened about a third of the pull requests in a year, most of them automated updates of tool versions.
Bot comments arrive within seconds and made the response times look like zero hours.
Pull requests, comments and reviews by bots are therefore left out, with the same rules as for {doc}`commits <counting-rules>`.

## Why the collector uses GraphQL

The first version of this collector made three REST requests per pull request and listed every repository's pull requests again for every year.
Collecting all years took about 85,000 requests, or 17 hours.
It also lost data silently: a failed request counted as a pull request without comments, and one deleted user account made it skip a whole repository.

The current collector reads each repository once with the GitHub GraphQL API, which returns fifty pull requests with their comments and reviews in one request ([#74](https://github.com/plone/plone-contributor-statistics/pull/74)).
Code review comments come from one listing per repository, and long discussions are completed with the REST API.
A failed request stops the run, like in the {doc}`contribution collector <counting-rules>`.

An earlier bug stopped the paging too early, so that the big repositories had no pull requests at all in some past years ([#37](https://github.com/plone/plone-contributor-statistics/issues/37)).
All years from 2010 on were collected again with the fixed collector.

```{seealso}
{doc}`/reference/data-files` lists the columns of `data/YYYY-plone-pr-interactions.csv`.
```
