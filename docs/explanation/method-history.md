(explanation-method-history)=

# How the method evolved

The method described in these pages didn't arrive at once.
It grew over a year, from a first script to a reviewed collection with tests.
Each change altered the data, so files collected before a change are not comparable with files collected after it.
This page tells that story in order, so that you can place any data file in it.

The other explanation pages say why each rule exists.
This page says when it came.

## First version, August 2025 to March 2026

Timo Stollenwerk wrote the first collector in August 2025.
It counted commits and pull requests per person for each repository of the `plone` organisation.
An early script guessed organisations from GitHub profiles and email domains, and a hand-maintained mapping soon replaced it.
The summaries were sorted by pull requests instead of commits from the start.
Self-employed people were moved out of the organisation list into a list of individual contributors.

In March 2026, the project took the shape it has today:

- The generated files moved to `data/` ([#7](https://github.com/plone/plone-contributor-statistics/issues/7)).
- World Plone Day counts only events held in person.
- The Volto statistics cover all Volto contributors, not only the Volto team.
- One file, `organisations.csv`, became the single organisation mapping ([#10](https://github.com/plone/plone-contributor-statistics/pull/10)).
- Only merged pull requests count, in the core and in Volto ([#12](https://github.com/plone/plone-contributor-statistics/pull/12), [#13](https://github.com/plone/plone-contributor-statistics/pull/13)).
- Commits count only on the default branch, read from the commit list instead of the contributor statistics of the GitHub API.
- Overrides record past organisations for a range of years ([#16](https://github.com/plone/plone-contributor-statistics/issues/16), [#17](https://github.com/plone/plone-contributor-statistics/pull/17)).

## Community recognition, May and June 2026

In May 2026, the recognition levels were changed to five tiers, so that the organisations spread more evenly across them ([#19](https://github.com/plone/plone-contributor-statistics/issues/19), [#20](https://github.com/plone/plone-contributor-statistics/pull/20)).
At a meeting in Bonn in June, the levels were amended once more ([#21](https://github.com/plone/plone-contributor-statistics/pull/21)), and five-year reports were added ([#23](https://github.com/plone/plone-contributor-statistics/pull/23)).

In June 2026, Mikel Larreategi opened pull requests with the community data of 2020 to 2024: sprints, release managers, team leaders, the Board, podcasts, World Plone Day and the conferences.
They were merged in October 2026, after the review described below.
The Foundation published the first recognition levels in August 2026 ({doc}`community-recognition`).

## Review of the method, October 2026

In October 2026, Jens W. Klein reviewed the method and the data, with corrections from Johannes Raggam, Mikel Larreategi and others.
The review found that several numbers were wrong in ways nobody had noticed, and changed the rules to make such errors visible.

Data and sources:

- A typo in the mapping had sent one organisation's activity to the wrong group, and format tests now check the mapping files ([#38](https://github.com/plone/plone-contributor-statistics/issues/38)).
- The conference organisers of 2003 to 2019 were added, each with a source.
- Unsourced rows were removed, and the scripts that fetched curated data were dropped.
- Strategic sprints, release managers and team leaders were aligned with the Board minutes and the team pages.
- Overrides record the employers of people who moved, as confirmed by them or by public sources ([#47](https://github.com/plone/plone-contributor-statistics/pull/47), [#49](https://github.com/plone/plone-contributor-statistics/pull/49), [#55](https://github.com/plone/plone-contributor-statistics/pull/55)).
- The conference trainings were checked against the conference websites ([#30](https://github.com/plone/plone-contributor-statistics/pull/30)).

Collection:

- Some scripts still read files from their old place after the move to `data/`, and all organisation files were generated again ([#40](https://github.com/plone/plone-contributor-statistics/issues/40)).
- Archived repositories are collected, and an explicit list names the excluded ones ([#36](https://github.com/plone/plone-contributor-statistics/issues/36)).
- API errors no longer count as zero activity, and interrupted runs no longer overwrite data ([#41](https://github.com/plone/plone-contributor-statistics/issues/41)).
- Merge commits no longer count ([#39](https://github.com/plone/plone-contributor-statistics/issues/39)).
- Pull requests count by merge date everywhere, backports included ([#42](https://github.com/plone/plone-contributor-statistics/issues/42)).
- Each repository is read once for all years ([#63](https://github.com/plone/plone-contributor-statistics/pull/63)).
- "Independent" was split into Unmapped and named independent contributors, and Unmapped is no longer ranked ([#53](https://github.com/plone/plone-contributor-statistics/issues/53)).
- All years from 2003 to 2025 were collected again with the fixed collector ([#65](https://github.com/plone/plone-contributor-statistics/pull/65)).

Pull request interactions:

- The paging stopped too early, so big repositories had no pull requests in some past years, and pull requests are now assigned to the year they were created ([#37](https://github.com/plone/plone-contributor-statistics/issues/37)).
- The collector moved to GraphQL, and bots are left out ([#74](https://github.com/plone/plone-contributor-statistics/pull/74)).
- The years from 2010 on were collected again.

History:

- Commits are read from local clones, including the history that exists only on old release branches ([#75](https://github.com/plone/plone-contributor-statistics/pull/75)).

Tooling:

- The tests run in GitHub Actions on every pull request ([#73](https://github.com/plone/plone-contributor-statistics/pull/73)).
- This documentation replaced the earlier notes, which moved to `archive/`.

## Which files are comparable

All contributor files from 2003 to 2025 and all interaction files from 2010 to 2025 were collected with the method of October 2026.
The Volto files and the recognition report are older, as {doc}`known-limitations` describes.
Files in `archive/` describe earlier states of the method and data.
