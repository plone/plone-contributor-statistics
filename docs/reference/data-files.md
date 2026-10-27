(reference-data-files)=

# Data files

This page describes the committed data files: which script writes them, what one row is, and which columns they have.
The top-level folders follow their role in the pipeline:

| Folder | Holds | Edit by hand? |
|---|---|---|
| `curated/` | Registers, lists and curated community data. | yes, with a public record for every entry |
| `collected/` | Data the collectors fetch from GitHub. | no |
| `derived/` | Data computed from curated and collected data. | no |
| `reports/` | Reports, text summaries and graphs. | no |

The code is in `scripts/`, one folder per stage, and `scripts/lib/paths.py` lists the location of every file.
Each file pattern with `YYYY` exists once per year that was collected or, for the recognition report, once per recognition year that was run.
Tables of people and organisations are sorted by their count, highest first, and rows with the same count by name, ignoring case, so that a new run only changes the rows whose data changed.
The commit domains are sorted by person, then by commits, highest first.
The scripts that derive data and write reports stop with an error if a yearly file they need is missing, for example when the organisation statistics of a new year have not been written yet.

See {doc}`/explanation/counting-rules` for why the files count the way they do.

## Collected data

`collected/contributors/YYYY-plone-contributors.csv`
:   Written by `scripts/collect/plone_contributors.py`.
    One row per person with at least one counted commit or merged pull request in the year.
    `username` is the GitHub login, or `person:<id>` for a person without a GitHub account.
    Columns: `username`, `total_commits`, `total_pull_requests`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.
    A commit counts for the year of its committer date, a pull request for the year it was merged.
    `first_contribution` and `last_contribution` use the author dates of the commits; they are empty for a person with pull requests only.

`collected/pr-interactions/YYYY-plone-pr-interactions.csv`
:   Written by `scripts/collect/plone_pr_interactions.py`.
    One row per pull request created in the year, in any state.
    Pull requests by bots are left out, and so are the comments and reviews of bots.
    Columns: `repo`, `pr_number`, `title`, `author`, `created_at`, `merged_at`, `state`, `merged`, `issue_comments_count`, `review_comments_count`, `reviews_count`, `total_comments`, `participants_count`, `reviewers_count`, `commenters_count`, `approved_reviews`, `changes_requested_reviews`, `comment_reviews`, `reactions_total`, `first_response_time`.
    `first_response_time` is in hours.

`collected/commit-domains/YYYY-plone-commit-domains.csv`
:   Written by `scripts/collect/plone_commit_domains.py`.
    One row per person and mail domain of the commits made in the year, by author date, in all clones of the `plone` repositories except the excluded ones.
    `username` is the GitHub login, or `person:<id>` for a person without a GitHub account.
    Columns: `username`, `domain`, `commits`.
    The domain is lower case without trailing dots; GitHub noreply addresses give `users.noreply.github.com`.
    Only the domain is stored, never the local part of an address, not even masked.
    The names of machines and placeholders are left out, since they are no public mail domains and some carry a person's name: names without a dot, names that end in `.local`, `.lan`, `.home`, `.localdomain`, `.fritz.box`, `.in-addr.arpa` or `.example`, names with `(none)`, and `example.com`, `example.org` and `example.net` with their subdomains.
    So are the domains of the Subversion years: `localhost`, the repository UUIDs and `users.sourceforge.net`.
    `commits` follows the rules of "A change counts once" in {doc}`/explanation/counting-rules`: a commit counts once however many branches hold it, the `[fc]` copies in `buildout.coredev` don't count, and commits with the same author date and subject in one repository count once.
    A commit that two repositories share counts once as well, which the commit statistics don't check.
    Merge commits, commits imported from Subversion, bots and authors that no register identifies are left out.
    A year without such commits has a file with the header only.

`collected/changelogs/YYYY-plone-changelog-entries.csv`
:   Written by `scripts/collect/plone_changelogs.py`.
    One row per person named in at least one changelog entry of a release in the year.
    `username` is the GitHub login, `person:<id>` for a person without a GitHub account, or the name as the changelog writes it if no identity maps it.
    Columns: `username`, `changelog_entries`, `repositories_count`, `repositories`, `changelog_names`, `matched_by`.
    `changelog_entries` counts each entry once, in full for every person it names.
    `changelog_names` lists the names in the changelogs that were mapped to the person, separated by semicolons.
    A mail address in `username` or `changelog_names` is stored masked, as the bare hash, see {ref}`masked-addresses`.
    `matched_by` lists the rules that mapped them, separated by semicolons: `identity` for a name, address or login of `curated/mappings/identities.csv` or `curated/mappings/people.csv`, `login` for a login with commits or pull requests, or `unmatched` for a name that nothing maps; the names of bots are left out.
    The committed files carry the `username` and `matched_by` values of their last run; a change of the registers shows in them at the next `make run-changelogs`.
    The files collected before the registers still carry `commit_authors` and `fullname`, the older names of what is now `identity`, until that run, see {doc}`/explanation/known-limitations`.
    A year without entries has a file with the header only.
    {doc}`/explanation/counting-rules` explains the dating and the deduplication.

`collected/plips/plone-plips.csv`
:   Written by `scripts/collect/plone_plips.py`.
    One row per PLIP author, over all years.
    Columns: `username`, `total_plips`, `open_plips`, `closed_plips`, `repositories_count`, `repositories`, `first_plip`, `last_plip`.

`collected/plips/plone-plips-detailed.csv`
:   Written by `scripts/collect/plone_plips.py`.
    One row per PLIP.
    Columns: `number`, `title`, `author`, `state`, `created_at`, `updated_at`, `closed_at`, `repository`, `html_url`.

## Curated data

{ref}`reference-curated-files` describes the files under `curated/`: their fields, constraints and checks.
This section adds what the schema cannot say.

The community data is one file per kind in `curated/community/`, with the rows of every year.
`curated/community/events.csv` holds the events, of the kinds `conference`, `symposium`, `wpd` and `sprint`; `curated/community/talks.csv`, `curated/community/trainings.csv` and `curated/community/organisers.csv` point to an event by its id.
The roles files, `curated/community/board-of-directors.csv`, `curated/community/team-leaders.csv`, `curated/community/release-managers.csv` and `curated/community/podcasts.csv`, have a `year` column instead.
The rows of a year are in the order in which the recognition reads them, see {doc}`/explanation/community-recognition`.

The community page counts the Plone Conference of a year with recorded organisers, the sprints, and the World Plone Day events held in person or as a hybrid as events; the World Plone Day events held online are recorded, but not counted as events, and neither would be the symposia, a kind that no row has yet.
The roles are Board member, team lead, release manager, trainer, speaker, podcast host, sprint organiser and conference organiser.
Of the World Plone Day videos, only those of the type `Talk` are talks.
A podcast counts for recognition through its hosts with at least five episodes in the year, see {doc}`/explanation/community-recognition`.
`sources` cites the record for the row only, by the ids of the source register, and `cited_as` gives it in words; the records for the organisations of people are the citations of the affiliations, in `curated/mappings/citations.csv`.

The source register is written by `python -m scripts.tools.capture`, not by hand.
`curated/sources/excerpts/<id>.md` holds the passages cited from the source with that id; the passage of a commit keeps its `Author:` and `Date:` lines, and the excerpt of a source that could not be captured holds only its note, `not captured on …` or `could not be fetched on …`.
`make check` finds every snippet in the excerpt of its source, see {doc}`/how-to/capture-a-source`.

`curated/plips/plone-plips-before-github.csv` is read by no script yet.
`Numbering` is `roadmap` for the PLIP numbers of the plone.org roadmap and of the wiki pages before it, or `trac` for the ticket numbers of dev.plone.org.
`Same as` names the other row where a source says that a roadmap PLIP and a Trac ticket are the same PLIP; both rows are kept.

## Derived data

`derived/plone-plip-organisations.csv`
:   Written by `scripts/derive/plip_organisation_stats.py`.
    One row per organisation, with the PLIPs of its members: a closed PLIP counts for the author's organisation in the year it was closed, an open one in the year it was created.
    Columns: `organisation`, `total_plips`, `open_plips`, `closed_plips`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `first_plip`, `last_plip`.

`derived/organisation-contributors/YYYY-plone-organisation-contributors.csv`
:   Written by `scripts/derive/organisation_stats.py`.
    One row per organisation with commits or pull requests in the year, plus one row `Unmapped`.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `changelog_entries`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.
    `changelog_entries` are the changelog entries of the organisation's people in the year, from `collected/changelogs/YYYY-plone-changelog-entries.csv`; they are not part of the other counts.
    Names that no identity maps count for `Unmapped`.
    The entries of an organisation without commits or pull requests in the year are left out, because the rows are those of the code work ([#137](https://github.com/plone/plone-contributor-statistics/issues/137)).
    The column is 0 in a year without a changelog file.
    `contributors` lists the people with commits or pull requests.

`derived/community-page.json`
:   Written by `scripts/derive/community_page.py`.
    Every number and list the community page shows: the headline numbers, the recognition levels and the organisations on the wall with their points and contributions, the yearly counts per person (by login or name, sorted, without ranks, with the organisation of the year, the community roles and the talks of the year with their recordings), and the history per year.
    {doc}`/explanation/community-page` explains the definitions.

`derived/summaries/summary-past-*-years-*.csv`
:   Written by `scripts/derive/multi_year_summary.py`.
    One row per organisation over the years in the file name.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `changelog_entries`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `years_active`, `first_contribution`, `last_contribution`.

`derived/yearly-activity-statistics.csv`
:   Written by `scripts/derive/yearly_activity_analysis.py`.
    One row per year with totals and ratios over all contributors.

`derived/community-recognition/YYYY-community-recognition-report.csv`
:   Written by `scripts/report/generate_community_recognition_report.py`.
    One row per organisation with its points per category, its total points and its level.

## Reports

`reports/github-contributor-report.md`
:   Written by `scripts/report/generate_contributor_report.py`.
    The contributors and organisations with the most contributions in the last full year and in the past three, five and ten years, and the changelog entries of 2004 to 2012 per person and per organisation.

`reports/pr-interactions/github-pr-interactions-report-YYYY.md`
:   Written by `scripts/collect/plone_pr_interactions.py`.
    Pull request engagement of the year: totals, response times, the most active participants and reviewers, and a breakdown per repository.
    The collector writes it, not a report script, because the report ranks participants and reviewers by name, and the CSV file holds only counts per pull request.

`reports/community-recognition.md`
:   Written by `scripts/report/generate_community_recognition_report.py`.
    Points per category and the level of each organisation, with the contributions behind them.

`reports/summaries/STATISTICS-PAST-*-YEARS.txt`
:   Written by `scripts/derive/multi_year_summary.py`, together with the summaries in `derived/summaries/`.
    A text summary of the matching `derived/summaries/summary-past-*-years-*.csv`.

`reports/graphs/`
:   Written by `scripts/report/generate_yearly_graphs.py`.
    Graphs of the totals per year in `derived/yearly-activity-statistics.csv`.
