"""Unmapped contributors, bots and the organisation mapping (#53)."""

import csv
import re
from pathlib import Path

import pandas as pd

import generate_community_recognition_report as recognition
from organisation_stats import UNMAPPED, aggregate_organisation_stats, load_organisation_mapping

ROOT = Path(__file__).resolve().parent.parent
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?')


def contributors(*rows):
    return pd.DataFrame([
        {'username': user, 'total_commits': commits, 'total_pull_requests': prs, 'repositories': 'volto',
         'first_contribution': '2024-01-01', 'last_contribution': '2024-12-31'}
        for user, commits, prs in rows
    ])


def test_unmapped_contributors_are_not_independent():
    stats = aggregate_organisation_stats(
        contributors(('alice', 3, 1), ('newcomer', 1, 1)), {'alice': 'kitconcept GmbH'}, bots={}
    )

    assert set(stats) == {'kitconcept GmbH', UNMAPPED}
    assert stats[UNMAPPED]['contributors'] == {'newcomer'}
    assert 'Independent' not in stats


def test_bots_are_left_out():
    stats = aggregate_organisation_stats(
        contributors(('alice', 3, 1), ('mister-roboto', 50, 0)), {'alice': 'kitconcept GmbH'},
        bots={'mister-roboto': 'Plone CI bot'},
    )

    assert set(stats) == {'kitconcept GmbH'}


def test_yearly_override(tmp_path):
    mapping = tmp_path / 'organisations.csv'
    mapping.write_text('Organisation,Team\nZest Software,fred\n', encoding='utf-8')
    overrides = tmp_path / 'overrides.csv'
    overrides.write_text('github_username,organisation,from_year,to_year\ntoalba,Klein & Partner KG,2023,2023\n',
                         encoding='utf-8')

    for year, expected in [(2022, None), (2023, 'Klein & Partner KG'), (2024, None)]:
        assert load_organisation_mapping(str(mapping), str(overrides), year=year).get('toalba') == expected


def test_recognition_report_excludes_unmapped():
    points = {'kitconcept GmbH': {'PR Contributions': 20}, UNMAPPED: {'PR Contributions': 20}, '': {'WPD Talk': 1}}

    assert recognition.exclude_unmapped(points) == {'kitconcept GmbH': {'PR Contributions': 20}}
    # The old name from existing data files is treated the same way
    assert recognition.normalize_organization_name('Independent') == UNMAPPED


# Format checks for the mapping files


def test_organisations_csv_format():
    with open(ROOT / 'organisations.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['Organisation', 'Team']
        rows = list(reader)

    seen = {}
    for row in rows:
        assert row['Organisation'].strip() == row['Organisation'] and row['Organisation']
        for login in filter(None, (m.strip() for m in row['Team'].split(';'))):
            # Would have caught "vangheem:vangheem" (#38)
            assert LOGIN.fullmatch(login), f"invalid GitHub login {login!r} in {row['Organisation']}"
            # GitHub logins are case-insensitive
            key = login.casefold()
            assert key not in seen, f"{login} is listed twice: {seen.get(key)} and {row['Organisation']}"
            seen[key] = row['Organisation']


def test_overrides_csv_format():
    with open(ROOT / 'organisation_mapping_overrides.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['github_username', 'organisation', 'from_year', 'to_year', 'source']
        rows = list(reader)

    for row in rows:
        assert LOGIN.fullmatch(row['github_username']), row
        assert row['organisation'].strip(), row
        assert row['source'].strip(), f"every override needs a source: {row}"
        assert row['from_year'].isdigit(), row
        if row['to_year']:
            assert row['to_year'].isdigit() and int(row['from_year']) <= int(row['to_year']), row


def test_proposals_csv_format():
    # Proposals are not used by the statistics; they wait for a confirmation (#70)
    with open(ROOT / 'organisation_mapping_proposals.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['contributor', 'organisation', 'from_year', 'to_year', 'evidence']
        rows = list(reader)

    for row in rows:
        assert row['contributor'].strip() and row['organisation'].strip(), row
        assert row['from_year'].isdigit() and row['to_year'].isdigit(), row
        assert int(row['from_year']) <= int(row['to_year']), row
        assert row['evidence'].strip(), row


def test_override_to_unmapped_counts_as_unmapped(tmp_path):
    # Years before an organisation existed, or before a person's affiliation is documented (#70)
    mapping = tmp_path / 'organisations.csv'
    mapping.write_text('Organisation,Team\nkitconcept GmbH,tisto\n', encoding='utf-8')
    overrides = tmp_path / 'overrides.csv'
    overrides.write_text('github_username,organisation,from_year,to_year,source\n'
                         'tisto,Unmapped,2002,2015,Founded in 2016\n', encoding='utf-8')

    for year, expected in [(2015, {UNMAPPED}), (2016, {'kitconcept GmbH'})]:
        m = load_organisation_mapping(str(mapping), str(overrides), year=year)
        stats = aggregate_organisation_stats(contributors(('tisto', 3, 1)), m, bots={})
        assert set(stats) == expected


def test_overrides_name_listed_organisations_and_dont_overlap():
    _, organisations = read_csv('organisations.csv')
    names = {row['Organisation'] for row in organisations}
    _, overrides = read_csv('organisation_mapping_overrides.csv')

    ranges = {}
    for row in overrides:
        assert row['organisation'] in names | {UNMAPPED}, f"add {row['organisation']!r} to organisations.csv"
        start, end = int(row['from_year']), int(row['to_year'] or 9999)
        for other_start, other_end in ranges.get(row['github_username'], []):
            assert end < other_start or start > other_end, f"overlapping overrides for {row['github_username']}"
        ranges.setdefault(row['github_username'], []).append((start, end))


def read_csv(name):
    with open(ROOT / name, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)
