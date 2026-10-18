"""Tests for selecting the repositories to collect statistics from (#36)."""

import csv
import re
from pathlib import Path

import pytest

from plone_contributors import (
    EXCLUDED_REPOSITORIES_FILE,
    load_excluded_repositories,
    select_repositories,
)

ROOT = Path(__file__).resolve().parent.parent


def repo(name, archived=False, fork=False):
    return {'name': name, 'archived': archived, 'fork': fork}


def test_archived_repositories_are_selected():
    repos = [repo('Products.CMFPlone'), repo('Products.TinyMCE', archived=True)]

    selected, skipped = select_repositories(repos, {})

    assert [r['name'] for r in selected] == ['Products.CMFPlone', 'Products.TinyMCE']
    assert skipped == []


def test_excluded_repositories_are_skipped_with_reason():
    repos = [repo('volto'), repo('dockerhub-docs', fork=True), repo('plone.app.event.renamedforrestore', archived=True)]
    excluded = {
        'dockerhub-docs': 'Fork of docker-library/docs',
        'plone.app.event.renamedforrestore': 'Duplicate of plone.app.event',
    }

    selected, skipped = select_repositories(repos, excluded)

    assert [r['name'] for r in selected] == ['volto']
    assert skipped == [
        ('dockerhub-docs', 'Fork of docker-library/docs'),
        ('plone.app.event.renamedforrestore', 'Duplicate of plone.app.event'),
    ]


def test_forks_are_not_excluded_automatically():
    # plone.z3cform is a fork, but Plone work: only the list decides.
    selected, _ = select_repositories([repo('plone.z3cform', fork=True)], {})

    assert [r['name'] for r in selected] == ['plone.z3cform']


def test_missing_exclusion_file_raises(tmp_path):
    # A missing file must not silently exclude nothing: a wrong path would change the statistics
    with pytest.raises(FileNotFoundError, match='missing.csv'):
        load_excluded_repositories(str(tmp_path / 'missing.csv'))


def test_load_excluded_repositories(tmp_path):
    path = tmp_path / 'excluded.csv'
    path.write_text('repository,reason\n dockerhub-docs , Fork of docker-library/docs \n', encoding='utf-8')

    assert load_excluded_repositories(str(path)) == {'dockerhub-docs': 'Fork of docker-library/docs'}


def test_exclusion_file_format():
    """Format check for the committed exclusion list."""
    with open(ROOT / EXCLUDED_REPOSITORIES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['repository', 'reason']
        rows = list(reader)

    names = [row['repository'] for row in rows]
    assert len(names) == len(set(names)), 'duplicate repositories'
    for row in rows:
        assert re.fullmatch(r'[A-Za-z0-9._-]+', row['repository']), row
        assert row['reason'].strip(), f"missing reason for {row['repository']}"


def test_extract_all_stats_processes_archived_and_skips_excluded(tmp_repo, monkeypatch, tmp_path):
    import plone_contributors

    # The exclusion list is read relative to the working directory, as with `make run-stats`.
    (tmp_path / EXCLUDED_REPOSITORIES_FILE).write_text(
        'repository,reason\ndockerhub-docs,Fork of docker-library/docs\n', encoding='utf-8'
    )
    monkeypatch.setattr(plone_contributors.time, 'sleep', lambda seconds: None)

    extractor = plone_contributors.PloneStatsExtractor(token='test-token')
    processed = []
    monkeypatch.setattr(extractor, 'get_organization_repos', lambda: [
        repo('Products.CMFPlone'), repo('Products.TinyMCE', archived=True), repo('dockerhub-docs', fork=True),
    ])
    monkeypatch.setattr(extractor, 'get_repository_commits', lambda name, branch: processed.append(name) or [])
    monkeypatch.setattr(extractor, 'get_repository_pull_requests', lambda name: [])

    extractor.extract_all_stats(save_every=0)

    assert processed == ['Products.CMFPlone', 'Products.TinyMCE']
