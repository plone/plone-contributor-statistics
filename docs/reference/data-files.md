(reference-data-files)=

# Data files

This page describes the committed data files: which script writes them, what one row is, and which columns they have.
Each file pattern with `YYYY` exists once per year.

## Collected data

`data/YYYY-plone-contributors.csv`
:   Written by `plone_contributors.py`.
    One row per GitHub account with at least one counted commit or merged pull request in the year.
    Columns: `username`, `total_commits`, `total_pull_requests`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.
    A commit counts for the year of its committer date, a pull request for the year it was merged.
    `first_contribution` and `last_contribution` use the author dates.

`data/YYYY-plone-pr-interactions.csv`
:   Written by `plone_pr_interactions.py`.
    One row per pull request created in the year, in any state.
    Columns: `repo`, `pr_number`, `title`, `author`, `created_at`, `merged_at`, `state`, `merged`, `issue_comments_count`, `review_comments_count`, `reviews_count`, `total_comments`, `participants_count`, `reviewers_count`, `commenters_count`, `approved_reviews`, `changes_requested_reviews`, `comment_reviews`, `reactions_total`, `first_response_time`.
    `first_response_time` is in hours.

`data/YYYY-volto-stats.csv`
:   Written by `volto_stats.py`.
    One row per contributor of `plone/volto` with at least one pull request or commit in the year.
    Columns: `github_username`, `pull_requests`, `commits`.

`plone-plips.csv`
:   Written by `plone_plips.py`.
    One row per PLIP author, over all years.
    Columns: `username`, `total_plips`, `open_plips`, `closed_plips`, `repositories_count`, `repositories`, `first_plip`, `last_plip`.

`plone-plips-detailed.csv`
:   Written by `plone_plips.py`.
    One row per PLIP.
    Columns: `number`, `title`, `author`, `state`, `created_at`, `updated_at`, `closed_at`, `repository`, `html_url`.

`cmfplone-releases.csv`
:   Written by `fetch_cmfplone_releases.py`.
    One row per release of `Products.CMFPlone`.
    Columns: `release`, `date`.

`data/community-contributions/YYYY-board-of-directors.csv`
:   Written by `fetch_board_members.py`.
    One row per board member of the board term that ends in the year.
    Columns: `Name`, `Organisation`.

## Curated data

All curated files are in `data/community-contributions/`.
Several people or organisations in one cell are separated by semicolons.

`data/community-contributions/YYYY-plone-conference.csv`
:   One row per organising organisation of the Plone Conference.
    Columns 2003–2019: `Organisation`, `Organiser(s)`, `Source`, `Notes`.
    Columns 2020–2025: `Organisation`.

`data/community-contributions/YYYY-plone-conference-trainings.csv`
:   One row per training at the Plone Conference.
    Columns: `Title`, `Trainer(s)`, `GitHub Handle(s)`, `Organisation`, and `Source` from 2020 to 2024.
    Trainers, handles and organisations are listed in the same order.

`data/community-contributions/YYYY-release-managers.csv`
:   One row per release manager.
    Columns: `Name`, `Github`, `Organisation`, and `Source` from 2020 to 2024.

`data/community-contributions/YYYY-team-leaders.csv`
:   One row per team leader and team.
    Columns: `Name`, `Team`, `Organisation`, and `Source` from 2020 to 2024.

`data/community-contributions/YYYY-strategic-sprints.csv`
:   One row per strategic sprint.
    Columns: `Sprint`, `Organiser/Host`, `Organisation`, and `Source` from 2020 to 2024.

`data/community-contributions/YYYY-podcasts.csv`
:   One row per podcast host.
    Columns: `Name`, `Organisation`.

`data/community-contributions/YYYY-world-plone-day-event.csv`
:   One row per in-person World Plone Day event.
    Columns: `Organisation`, `Reference`.

`data/community-contributions/YYYY-world-plone-day-talks.csv`
:   One row per World Plone Day talk.
    Columns: `Video Title`, `Speaker(s)`, `Organisation`, `Event / Location`, `Type`, `YouTube ID`.

## Derived data

`data/YYYY-plone-organisation-contributors.csv`
:   Written by `organisation_stats.py`.
    One row per organisation, plus one row `Unmapped`.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `first_contribution`, `last_contribution`.

`summary-past-*-years-*.csv`
:   Written by `multi_year_summary.py`.
    One row per organisation over the years in the file name.
    Columns: `organisation`, `total_commits`, `total_pull_requests`, `contributors_count`, `contributors`, `repositories_count`, `repositories`, `years_active`, `first_contribution`, `last_contribution`.

`STATISTICS-PAST-*-YEARS.txt`
:   Written by `multi_year_summary.py`.
    A text summary of the matching `summary-past-*-years-*.csv`.

`yearly-activity-statistics.csv`
:   Written by `yearly_activity_analysis.py`.
    One row per year with totals and ratios over all contributors.

`data/community-contributions/YYYY-community-recognition-report.csv`
:   Written by `generate_community_recognition_report.py`.
    One row per organisation with its points per category, its total points and its level.

## Reports

`reports/github-contributor-report.md`
:   Written by `generate_contributor_report.py`.

`reports/github-pr-interactions-report-YYYY.md`
:   Written by `plone_pr_interactions.py`.

`reports/volto.md`
:   Written by `generate_volto_team_report.py`.

`reports/community-recognition.md`
:   Written by `generate_community_recognition_report.py`.

`reports/plips.md`
:   Its generator `generate_plip_report.py` is not in the repository.
