(reference-data-files)=

# Data files

This page describes the committed data files: which script writes them, what one row is, and which columns they have.
The top-level folders follow their role in the pipeline:

| Folder | Holds | Edit by hand? |
|---|---|---|
| `curated/` | Mapping files and curated community data. | yes, with a public record for every entry |
| `collected/` | Data the collectors fetch from GitHub. | no |
| `derived/` | Data computed from curated and collected data. | no |
| `reports/` | Reports, text summaries and graphs. | no |

The code is in `scripts/`, one folder per stage, and `scripts/lib/paths.py` lists the location of every file.
Each file pattern with `YYYY` exists once per year.
The scripts that derive data and write reports stop with an error if a yearly file they need is missing, for example when the organisation statistics of a new year have not been written yet.

See {doc}`/explanation/counting-rules` for why the files count the way they do.

## Collected data

`collected/contributors/YYYY-plone-contributors.csv`
:   Written by `scripts/collect/plone_contributors.py`.
    One row per person with at least one counted commit or merged pull request in the year.
    `username` is the GitHub login, or the name of a person without a GitHub account.
    Columns: `username`, `total_commits`, `total_pull_requests`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.
    A commit counts for the year of its committer date, a pull request for the year it was merged.
    `first_contribution` and `last_contribution` use the author dates.

`collected/pr-interactions/YYYY-plone-pr-interactions.csv`
:   Written by `scripts/collect/plone_pr_interactions.py`.
    One row per pull request created in the year, in any state.
    Columns: `repo`, `pr_number`, `title`, `author`, `created_at`, `merged_at`, `state`, `merged`, `issue_comments_count`, `review_comments_count`, `reviews_count`, `total_comments`, `participants_count`, `reviewers_count`, `commenters_count`, `approved_reviews`, `changes_requested_reviews`, `comment_reviews`, `reactions_total`, `first_response_time`.
    `first_response_time` is in hours.

`collected/volto/YYYY-volto-stats.csv`
:   Written by `scripts/collect/volto_stats.py`.
    One row per contributor of `plone/volto` with at least one pull request or commit in the year.
    Columns: `github_username`, `pull_requests`, `commits`.

`collected/plips/plone-plips.csv`
:   Written by `scripts/collect/plone_plips.py`.
    One row per PLIP author, over all years.
    Columns: `username`, `total_plips`, `open_plips`, `closed_plips`, `repositories_count`, `repositories`, `first_plip`, `last_plip`.

`collected/plips/plone-plips-detailed.csv`
:   Written by `scripts/collect/plone_plips.py`.
    One row per PLIP.
    Columns: `number`, `title`, `author`, `state`, `created_at`, `updated_at`, `closed_at`, `repository`, `html_url`.

`derived/plone-plip-organisations.csv`
:   Written by `scripts/derive/plip_organisation_stats.py`.
    One row per organisation, with the PLIPs of its members: a closed PLIP counts for the author's organisation in the year it was closed, an open one in the year it was created.
    Columns: `organisation`, `total_plips`, `open_plips`, `closed_plips`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `first_plip`, `last_plip`.


## Curated data

All curated files are in `curated/community-contributions/`.
Several people or organisations in one cell are separated by semicolons.

`curated/community-contributions/YYYY-board-of-directors.csv`
:   One row per member of the Board of Directors whose term ends in the year, including the non-voting officers.
    Columns: `Name`, `Organisation`, `Source`, `Role`.
    `Role` is `voting` for directors and `non-voting` for officers such as the treasurer.

`curated/community-contributions/YYYY-plone-conference.csv`
:   One row per organising organisation of the Plone Conference.
    Columns 2003–2019: `Organisation`, `Organiser(s)`, `Source`, `Notes`.
    Columns 2020–2025: `Organisation`.

`curated/community-contributions/YYYY-plone-conference-trainings.csv`
:   One row per training at the Plone Conference.
    Columns: `Title`, `Trainer(s)`, `GitHub Handle(s)`, `Organisation`, and `Source` from 2020 to 2024.
    Trainers, handles and organisations are listed in the same order.

`curated/community-contributions/YYYY-release-managers.csv`
:   One row per release manager.
    Columns: `Name`, `Github`, `Organisation`, `Source`.

`curated/community-contributions/YYYY-team-leaders.csv`
:   One row per team leader and team.
    Columns: `Name`, `Team`, `Organisation`, and `Source` from 2020 to 2024.

`curated/community-contributions/YYYY-strategic-sprints.csv`
:   One row per strategic sprint.
    Columns: `Sprint`, `Organiser/Host`, `Organisation`, and `Source` from 2020 to 2024.

`curated/community-contributions/YYYY-podcasts.csv`
:   One row per podcast host.
    Columns: `Name`, `Organisation`.

`curated/community-contributions/YYYY-world-plone-day-event.csv`
:   One row per in-person World Plone Day event.
    Columns: `Organisation`, `Reference`.

`curated/community-contributions/YYYY-world-plone-day-talks.csv`
:   One row per World Plone Day talk.
    Columns: `Video Title`, `Speaker(s)`, `Organisation`, `Event / Location`, `Type`, `YouTube ID`.

## Derived data

`derived/organisation-contributors/YYYY-plone-organisation-contributors.csv`
:   Written by `scripts/derive/organisation_stats.py`.
    One row per organisation, plus one row `Unmapped`.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.

`derived/summaries/summary-past-*-years-*.csv`
:   Written by `scripts/derive/multi_year_summary.py`.
    One row per organisation over the years in the file name.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `years_active`, `first_contribution`, `last_contribution`.

`reports/summaries/STATISTICS-PAST-*-YEARS.txt`
:   Written by `scripts/derive/multi_year_summary.py`.
    A text summary of the matching `derived/summaries/summary-past-*-years-*.csv`.

`derived/yearly-activity-statistics.csv`
:   Written by `scripts/derive/yearly_activity_analysis.py`.
    One row per year with totals and ratios over all contributors.

`derived/community-recognition/YYYY-community-recognition-report.csv`
:   Written by `scripts/report/generate_community_recognition_report.py`.
    One row per organisation with its points per category, its total points and its level.

## Reports

`reports/github-contributor-report.md`
:   Written by `scripts/report/generate_contributor_report.py`.

`reports/pr-interactions/github-pr-interactions-report-YYYY.md`
:   Written by `scripts/collect/plone_pr_interactions.py`.
    The collector writes it, not a report script, because the report ranks participants and reviewers by name, and the CSV file holds only counts per pull request.

`reports/volto.md`
:   Written by `scripts/report/generate_volto_team_report.py`.

`reports/community-recognition.md`
:   Written by `scripts/report/generate_community_recognition_report.py`.
