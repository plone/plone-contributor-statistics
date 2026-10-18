"""Unmapped contributors are not ranked as an organisation in the reports (#53)."""

import pandas as pd

import multi_year_summary
from generate_contributor_report import top_organisations_table
from organisation_stats import UNMAPPED


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

    _, txt_file = multi_year_summary.save_summary(organisations(), [2022, 2023, 2024])

    text = (tmp_path / txt_file).read_text(encoding='utf-8')
    assert '- 2 total organisations tracked' in text
    assert f'. {UNMAPPED}:' not in text
    assert '2. Kombinat: 537 PRs' in text
    assert 'Not mapped to an organisation: 692 PRs' in text
