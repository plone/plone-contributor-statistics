"""Commits and PRs are fetched once per repository and assigned to periods (years)."""

import csv
import sys
from datetime import datetime

import pytest

import plone_contributors
from plone_contributors import BOT_ACCOUNTS_FILE, PloneStatsExtractor, year_periods


def commit(login, date, author_date=None, parents=1, user_type='User'):
    return {
        'author': {'login': login, 'type': user_type} if login else None,
        'commit': {
            'author': {'date': f'{author_date or date}T12:00:00Z'},
            'committer': {'date': f'{date}T12:00:00Z'},
        },
        'parents': [{'sha': str(i)} for i in range(parents)],
    }


def pr(login, merged, user_type='User'):
    return {
        'merged_at': f'{merged}T12:00:00Z' if merged else None,
        'updated_at': f'{merged or "2020-01-01"}T13:00:00Z',
        'user': {'login': login, 'type': user_type},
    }


@pytest.fixture
def extractor(tmp_repo, monkeypatch, tmp_path):
    (tmp_path / BOT_ACCOUNTS_FILE).write_text('login,reason\nmister-roboto,Plone CI bot\n', encoding='utf-8')
    monkeypatch.setattr(plone_contributors.time, 'sleep', lambda seconds: None)
    return PloneStatsExtractor(token='test-token', periods=year_periods(2012, 2014))


def test_year_periods():
    assert year_periods(2012, 2013) == [
        ('2012-plone-contributors', datetime(2012, 1, 1), datetime(2012, 12, 31, 23, 59, 59)),
        ('2013-plone-contributors', datetime(2013, 1, 1), datetime(2013, 12, 31, 23, 59, 59)),
    ]


def test_commits_are_assigned_to_the_year_of_their_commit_date(extractor):
    extractor.process_commits('Products.CMFPlone', [
        commit('alice', '2012-05-01'),
        commit('alice', '2013-02-01'),
        commit('alice', '2013-03-01'),
        commit('bob', '2014-07-01'),
    ])

    data = extractor.contributors_data
    assert data['2012-plone-contributors']['alice']['commits'] == 1
    assert data['2013-plone-contributors']['alice']['commits'] == 2
    assert data['2014-plone-contributors']['bob']['commits'] == 1
    assert 'bob' not in data['2012-plone-contributors']


def test_bots_and_unlinked_commits_are_skipped(extractor):
    extractor.process_commits('volto', [
        commit('mister-roboto', '2013-01-01'),                 # bot listed in bot_accounts.csv
        commit('dependabot[bot]', '2013-01-01', user_type='Bot'),
        commit(None, '2013-01-01'),                            # email not linked to a GitHub account
        commit('alice', '2013-01-01'),
    ])

    assert list(extractor.contributors_data['2013-plone-contributors']) == ['alice']


def test_pull_requests_are_assigned_to_the_year_they_were_merged(extractor):
    extractor.process_pull_requests('volto', [
        pr('alice', '2012-12-31'),
        pr('alice', '2013-01-01'),
        pr('alice', None),               # closed without merge
        pr('mister-roboto', '2013-05-01'),
        pr('renovate', '2013-05-01', user_type='Bot'),
    ])

    data = extractor.contributors_data
    assert data['2012-plone-contributors']['alice']['pull_requests'] == 1
    assert data['2013-plone-contributors']['alice']['pull_requests'] == 1
    assert 'mister-roboto' not in data['2013-plone-contributors']
    assert 'renovate' not in data['2013-plone-contributors']


def test_report_per_period(extractor):
    extractor.process_commits('volto', [commit('alice', '2013-02-01', author_date='2013-01-15')])
    extractor.process_pull_requests('plone.restapi', [pr('alice', '2013-03-01')])

    df = extractor.generate_report('2013-plone-contributors')

    row = df.iloc[0]
    assert (row['username'], row['total_commits'], row['total_pull_requests']) == ('alice', 1, 1)
    assert row['repositories'] == 'plone.restapi, volto'
    assert row['first_contribution'] == '2013-01-15'
    assert extractor.generate_report('2012-plone-contributors').empty


def test_main_writes_one_file_per_year(tmp_repo, monkeypatch, tmp_path):
    (tmp_path / 'data').mkdir()
    monkeypatch.setattr(sys, 'argv', ['plone_contributors.py', '--from-year', '2012', '--to-year', '2013',
                                      '--token', 'test-token'])

    def run(self, *args, **kwargs):
        self.process_commits('volto', [commit('alice', '2012-05-01'), commit('bob', '2013-05-01')])

    monkeypatch.setattr(PloneStatsExtractor, 'extract_all_stats', run)

    assert plone_contributors.main() == 0
    for year, user in [(2012, 'alice'), (2013, 'bob')]:
        with open(tmp_path / 'data' / f'{year}-plone-contributors.csv', newline='') as f:
            assert [row['username'] for row in csv.DictReader(f)] == [user]


def test_from_and_to_year_must_be_used_together(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plone_contributors.py', '--from-year', '2012', '--token', 'test-token'])

    assert plone_contributors.main() == 1


def test_bot_accounts_file_format():
    """Format check for the committed bot list."""
    from pathlib import Path
    with open(Path(__file__).resolve().parent.parent / BOT_ACCOUNTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['login', 'reason']
        rows = list(reader)
    assert rows
    assert len({row['login'] for row in rows}) == len(rows)
    assert all(row['reason'].strip() for row in rows)
