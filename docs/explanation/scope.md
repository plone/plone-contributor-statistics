(explanation-scope)=

# What the statistics measure

The statistics try to answer a simple question: who does the work on Plone, and which organisations make that work possible?
The answer is never complete, because much of the work on an open source project leaves no trace in a repository.
This page explains which traces the statistics follow, which they leave out, and why.

## The `plone` GitHub organisation is the core

Plone's code lives in the [`plone` organisation on GitHub](https://github.com/plone).
Its repositories hold the history of Plone since 2002, imported from CVS and Subversion.
That history is the one source that covers the whole life of the project in the same form, so it is the core of the statistics.

The collector reads every repository of the organisation, including archived ones.
A repository that is archived today was active once, and its commits belong to the years they were made ([#36](https://github.com/plone/plone-contributor-statistics/issues/36)).

An explicit list names the few repositories that are not Plone work, each with a reason.
Examples are forks that carry the upstream history of Docker images, and archived forks of Zope Foundation repositories.
The list is open for review ([#60](https://github.com/plone/plone-contributor-statistics/issues/60)).
How to count Zope and the other projects of the Plone Foundation is not decided yet ([#58](https://github.com/plone/plone-contributor-statistics/issues/58)).

## Commits and merged pull requests

Two things are counted for each person: commits and merged pull requests.

A commit is the smallest unit of authored code.
Only commits that reached the default branch count, together with the older history that some repositories keep only on release branches.
Work on a feature branch that was never merged did not become part of Plone.

A pull request counts only when it was merged.
A merged pull request is a contribution that the project accepted.
Open and rejected pull requests are left out, so the numbers reflect the code that Plone actually contains.

{doc}`counting-rules` explains the details: which date decides the year, why merge commits don't count, and how bots are recognized.

## Engagement is counted separately

Reviews and comments are work too, and often the work that keeps a project healthy.
They are collected as {doc}`pull request interactions <pr-interactions>`, for pull requests in any state.
They are not yet credited to people or organisations ([#61](https://github.com/plone/plone-contributor-statistics/issues/61)).

## Work outside GitHub

Plone is more than code.
People organise conferences and sprints, lead teams, manage releases, give trainings and talks.
None of this shows up in a repository.

For some of this work, the statistics use {doc}`curated data <curated-community-data>`: lists that people compile by hand from public sources.
Other work, such as documentation outside GitHub, marketing, or answering questions in the forum, is not recorded at all.
How to recognise it is an open question ([#35](https://github.com/plone/plone-contributor-statistics/issues/35)).

## From data to reports

```{mermaid}
:alt: Flow of the data from the sources through the per-year files to the reports
:caption: How the data flows

flowchart LR
    gh[GitHub repositories] --> contrib[Contributors per year]
    contrib --> orgs[Organisations per year]
    mapping[Organisation mapping] --> orgs
    orgs --> summaries[Multi-year summaries and reports]
    gh --> interactions[PR interactions per year]
    plips[PLIPs] --> recognition[Community recognition]
    curated[Curated community data] --> recognition
    summaries --> recognition
```

The collectors write one file per year.
The {doc}`organisation mapping <attribution>` then turns people into organisations, year by year.
Summaries and reports are built from those files and never query GitHub themselves.
This is why a corrected mapping needs no new collection, only a regeneration.

```{seealso}
{doc}`/reference/data-sources` lists every source with the years it covers.
```
