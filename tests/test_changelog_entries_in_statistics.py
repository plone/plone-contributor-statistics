"""Changelog entries in their own column of the statistics and the report, never added to commits (#71)."""

import sys

import pandas as pd

from scripts.derive import multi_year_summary, organisation_stats
from scripts.derive.organisation_stats import UNMAPPED
from scripts.lib.model import load_registry
from scripts.lib import paths
from scripts.report import generate_contributor_report as report

CONTRIBUTORS = ('username,total_commits,total_pull_requests,repositories_count,repositories,first_contribution,'
                'last_contribution\n')
CHANGELOG = 'username,changelog_entries,repositories_count,repositories,changelog_names,matched_by\n'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_entries_by_organisation():
    changelog = pd.DataFrame([
        {'username': 'hannosch', 'changelog_entries': 5, 'matched_by': 'login'},
        {'username': 'alecpm', 'changelog_entries': 3, 'matched_by': 'changelog_names'},
        # An unmatched name counts as Unmapped, even if it is spelled like a mapped login
        {'username': 'limi', 'changelog_entries': 2, 'matched_by': 'unmatched'},
        {'username': 'Andy McKay', 'changelog_entries': 1, 'matched_by': 'commit_authors'},
        {'username': 'mister-roboto', 'changelog_entries': 9, 'matched_by': 'login'},
    ])
    mapping = {'hannosch': 'Jarn', 'alecpm': 'Jarn', 'limi': 'Plone Solutions'}.get

    entries = organisation_stats.changelog_entries_by_organisation(
        changelog, lambda username: mapping(username, UNMAPPED), {'mister-roboto': 'bot'})

    assert dict(entries) == {'Jarn': 8, UNMAPPED: 3}


def stats():
    return pd.DataFrame([
        {'username': 'hannosch', 'total_commits': 10, 'total_pull_requests': 0, 'repositories': 'a',
         'first_contribution': '2008-01-01', 'last_contribution': '2008-02-01'},
        {'username': 'stranger', 'total_commits': 20, 'total_pull_requests': 1, 'repositories': 'b',
         'first_contribution': '2008-01-01', 'last_contribution': '2008-02-01'},
    ])


def test_the_column_is_next_to_commits_and_never_added_to_them():
    changelog = pd.DataFrame([
        {'username': 'hannosch', 'changelog_entries': 50, 'matched_by': 'login'},
        {'username': 'timo', 'changelog_entries': 4, 'matched_by': 'unmatched'},
        # The only person of an organisation without code work in the year: no new row
        {'username': 'limi', 'changelog_entries': 7, 'matched_by': 'login'},
    ])
    mapping = {'hannosch': 'Jarn', 'limi': 'Plone Solutions'}.get

    grouped = organisation_stats.aggregate_organisation_stats(
        stats(), lambda username: mapping(username, UNMAPPED), bots={}, changelog_df=changelog)
    df = organisation_stats.create_organisation_dataframe(grouped)

    assert list(df.columns[:4]) == ['organisation', 'total_commits', 'total_pull_requests', 'changelog_entries']
    # Still sorted by commits
    assert df[['organisation', 'total_commits', 'changelog_entries']].values.tolist() == [
        [UNMAPPED, 20, 4], ['Jarn', 10, 50]]


def test_a_year_without_changelog_file_gets_zero(write_registers, monkeypatch):
    write(paths.contributors_file(2026), CONTRIBUTORS + 'hannosch,3,1,1,a,2026-01-01,2026-01-02\n')
    write_registers(people=[('hannosch', 'hannosch')], affiliations=[('hannosch', 'jarn', 2002, '')],
                    organisations=[('jarn', 'Jarn')])
    monkeypatch.setattr(sys, 'argv', ['organisation_stats', '--year', '2026'])

    organisation_stats.main()

    df = pd.read_csv(paths.organisation_contributors_file(2026))
    assert df[['organisation', 'total_commits', 'changelog_entries']].values.tolist() == [['Jarn', 3, 0]]


def test_the_yearly_file_takes_the_entries_of_the_year(write_registers, monkeypatch):
    write(paths.contributors_file(2008), CONTRIBUTORS + 'hannosch,3,0,1,a,2008-01-01,2008-01-02\n')
    write(paths.changelog_entries_file(2008), CHANGELOG + 'hannosch,12,2,"a, b",hannosch,login\n')
    write_registers(people=[('hannosch', 'hannosch')], affiliations=[('hannosch', 'jarn', 2002, '')],
                    organisations=[('jarn', 'Jarn')])
    monkeypatch.setattr(sys, 'argv', ['organisation_stats', '--year', '2008'])

    organisation_stats.main()

    df = pd.read_csv(paths.organisation_contributors_file(2008))
    assert df[['organisation', 'total_commits', 'changelog_entries']].values.tolist() == [['Jarn', 3, 12]]


ORGANISATION_COLUMNS = ('organisation,total_commits,total_pull_requests,changelog_entries,contributors_count,'
                        'contributors,repositories_count,repositories,first_contribution,last_contribution\n')


def test_summaries_add_up_the_entries(tmp_repo):
    write(paths.organisation_contributors_file(2010), ORGANISATION_COLUMNS
          + 'Jarn,10,2,30,1,hannosch,1,a,2010-01-01,2010-02-01\n')
    # A file written before the column existed
    write(paths.organisation_contributors_file(2011), 'organisation,total_commits,total_pull_requests,'
          'contributors_count,contributors,repositories_count,repositories,first_contribution,last_contribution\n'
          'Jarn,5,1,1,hannosch,1,a,2011-01-01,2011-02-01\n')

    df = multi_year_summary.combine_multi_year_stats([2010, 2011])

    assert list(df.columns[:4]) == ['organisation', 'total_commits', 'total_pull_requests', 'changelog_entries']
    assert df[['total_commits', 'total_pull_requests', 'changelog_entries']].values.tolist() == [[15, 3, 30]]


def test_report_section(tmp_repo):
    for year in range(2004, 2013):
        write(paths.contributors_file(year), CONTRIBUTORS + 'hannosch,10,0,1,a,2004-01-01,2004-01-02\n')
        write(paths.organisation_contributors_file(year), ORGANISATION_COLUMNS
              + 'Jarn,10,0,4,1,hannosch,1,a,2004-01-01,2004-01-02\n' + f'{UNMAPPED},0,0,1,0,,0,,,\n')
    write(paths.changelog_entries_file(2004), CHANGELOG + 'hannosch,3,1,a,hannosch,login\n'
          'timo,1,1,a,timo,unmatched\n')
    write(paths.changelog_entries_file(2005), CHANGELOG + 'hannosch,1,1,a,hannosch,login\n')

    section = '\n'.join(report.changelog_section(list(range(2003, 2026))))

    assert section.startswith('## Changelog Entries 2004–2012\n')
    assert '| 1 | hannosch | 4 | 90 |' in section
    # A name without a mapping is shown as written, in italics
    assert '| 2 | *timo* | 1 | 0 |' in section
    assert '| 1 | Jarn | 36 | 90 | 1 |' in section
    assert 'Not mapped to an organisation: 9 changelog entries, 0 commits.' in section


def test_person_without_login_counts_for_the_organisation(write_registers):
    write_registers(people=[('timo-stollenwerk', '')], affiliations=[('timo-stollenwerk', 'jarn', 2002, '')],
                    organisations=[('jarn', 'Jarn')])
    registry = load_registry()
    stats = pd.DataFrame([
        {'username': 'person:timo-stollenwerk', 'total_commits': 7, 'total_pull_requests': 1, 'repositories': 'a',
         'first_contribution': '2008-01-01', 'last_contribution': '2008-02-01'}])

    grouped = organisation_stats.aggregate_organisation_stats(
        stats, lambda username: registry.organisation_for_username(username, 2008), bots={})

    assert {name: values['total_commits'] for name, values in grouped.items()} == {'Jarn': 7}


def test_no_report_section_without_changelog_files(tmp_repo):
    assert report.changelog_section([2024, 2025]) == []
