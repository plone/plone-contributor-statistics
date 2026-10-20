"""Unmapped contributors are not ranked as an organisation in the reports (#53)."""

import pandas as pd

from scripts.derive import multi_year_summary
from scripts.lib import paths
from scripts.report.generate_contributor_report import top_organisations_table
from scripts.derive.organisation_stats import aggregate_organisation_stats
from scripts.lib.model import UNMAPPED
from scripts.report import generate_community_recognition_report as recognition


def organisations():
    return pd.DataFrame([
        {'organisation': 'kitconcept GmbH', 'total_pull_requests': 2528, 'total_commits': 9000,
         'contributors_count': 15, 'contributors': 'a', 'repositories_count': 80, 'repositories': 'volto'},
        {'organisation': UNMAPPED, 'total_pull_requests': 692, 'total_commits': 1500,
         'contributors_count': 209, 'contributors': 'b', 'repositories_count': 120, 'repositories': 'volto'},
        {'organisation': 'Kombinat', 'total_pull_requests': 537, 'total_commits': 2406,
         'contributors_count': 1, 'contributors': 'c', 'repositories_count': 30, 'repositories': 'mockup'},
    ])


def test_report_table_does_not_rank_unmapped():
    table = top_organisations_table(organisations())

    rows = [line for line in table.splitlines() if line.startswith('| ') and line[2].isdigit()]
    assert [row.split('|')[2].strip() for row in rows] == ['kitconcept GmbH', 'Kombinat']
    assert 'Not mapped to an organisation: 692 PRs, 1,500 commits by 209 contributors.' in table


def test_summary_does_not_rank_unmapped(tmp_repo, tmp_path, monkeypatch):
    # The contributor files of the years exist, but are empty
    for year in [2022, 2023, 2024]:
        path = paths.contributors_file(year)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('username,total_commits,total_pull_requests\n', encoding='utf-8')

    _, txt_file = multi_year_summary.save_summary(organisations(), [2022, 2023, 2024])

    text = (tmp_path / txt_file).read_text(encoding='utf-8')
    assert '- 2 total organisations tracked' in text
    assert f'. {UNMAPPED}:' not in text
    assert '2. Kombinat: 537 PRs' in text
    assert 'Not mapped to an organisation: 692 PRs' in text
    # The text says where the CSV file is
    assert '- File generated: derived/summaries/summary-past-three-years-2022-2024.csv\n' in text
    assert (tmp_path / paths.SUMMARIES_DIR / 'summary-past-three-years-2022-2024.csv').exists()
    assert txt_file == paths.SUMMARY_REPORTS_DIR / 'STATISTICS-PAST-THREE-YEARS.txt'


def contributors(*rows):
    return pd.DataFrame([
        {'username': user, 'total_commits': commits, 'total_pull_requests': prs, 'repositories': 'volto',
         'first_contribution': '2024-01-01', 'last_contribution': '2024-12-31'}
        for user, commits, prs in rows
    ])


def organisation_of(username):
    return {'alice': 'kitconcept GmbH'}.get(username, UNMAPPED)


def test_unmapped_contributors_are_not_independent():
    stats = aggregate_organisation_stats(
        contributors(('alice', 3, 1), ('newcomer', 1, 1)), organisation_of, bots={}
    )

    assert set(stats) == {'kitconcept GmbH', UNMAPPED}
    assert stats[UNMAPPED]['contributors'] == {'newcomer'}
    assert 'Independent' not in stats


def test_bots_are_left_out():
    stats = aggregate_organisation_stats(
        contributors(('alice', 3, 1), ('mister-roboto', 50, 0)), organisation_of,
        bots={'mister-roboto': 'Plone CI bot'},
    )

    assert set(stats) == {'kitconcept GmbH'}


def test_recognition_report_excludes_unmapped():
    points = {'kitconcept GmbH': {'PR Contributions': 20}, UNMAPPED: {'PR Contributions': 20}, '': {'WPD Talk': 1}}

    assert recognition.exclude_unmapped(points) == {'kitconcept GmbH': {'PR Contributions': 20}}
