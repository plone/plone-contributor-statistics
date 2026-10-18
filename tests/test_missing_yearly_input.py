"""A missing yearly file stops the derive and report scripts (repository layout, spec 4.3a)."""

import ast
from pathlib import Path

import pytest

from scripts.report import generate_community_recognition_report as recognition
from scripts.report import generate_contributor_report
from scripts.derive import multi_year_summary
from scripts.lib import paths
from scripts.derive import yearly_activity_analysis

CONTRIBUTORS = 'username,total_commits,total_pull_requests,repositories_count,repositories,first_contribution,last_contribution\n'


def contributors(year):
    path = paths.contributors_file(year)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONTRIBUTORS + 'alice,1,1,1,plone/volto,2024-01-01,2024-01-01\n', encoding='utf-8')


def test_yearly_activity_raises_on_missing_organisation_year(tmp_repo):
    # e.g. make yearly-activity before make run-organisation-stats for a new year
    contributors(2024)
    with pytest.raises(FileNotFoundError, match='2024-plone-organisation-contributors.csv'):
        yearly_activity_analysis.main()


def test_contributor_report_raises_on_missing_organisation_year(tmp_repo):
    contributors(2024)
    with pytest.raises(FileNotFoundError, match='2024-plone-organisation-contributors.csv'):
        generate_contributor_report.load_organisation_file(2024)


def test_contributor_report_raises_on_missing_contributor_year(tmp_repo):
    with pytest.raises(FileNotFoundError, match='2024-plone-contributors.csv'):
        generate_contributor_report.load_contributor_file(2024)


def test_summary_contributor_totals_raise_on_missing_year(tmp_repo):
    contributors(2023)
    with pytest.raises(FileNotFoundError, match='2024-plone-contributors.csv'):
        multi_year_summary.get_contributor_totals([2023, 2024])


def test_recognition_report_is_not_curated_data(tmp_path):
    # The derived report lives next to the curated files: it must not count as curated data of the year
    (tmp_path / '2025-community-recognition-report.csv').write_text('Organisation\n', encoding='utf-8')
    with pytest.raises(FileNotFoundError, match='2025'):
        recognition.require_community_year(tmp_path, 2025)


def test_paths_assigns_each_name_once():
    tree = ast.parse(Path(paths.__file__).read_text(encoding='utf-8'))
    names = [target.id for node in tree.body if isinstance(node, ast.Assign) for target in node.targets]
    assert len(names) == len(set(names)), sorted(n for n in names if names.count(n) > 1)
