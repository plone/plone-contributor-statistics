"""People behind unlinked commit emails, and second accounts (#69)."""

import csv
import re
from pathlib import Path

import pytest

import plone_contributors
from plone_contributors import ACCOUNT_ALIASES_FILE, COMMIT_AUTHORS_FILE, PloneStatsExtractor, year_periods

ROOT = Path(__file__).resolve().parent.parent
LOGIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?')


def local_commit(sha, email):
    date = '2003-06-01T10:00:00Z'
    return {'sha': sha, 'parents': [{'sha': 'p'}], 'author': None,
            'commit': {'author': {'name': 'x', 'email': email, 'date': date}, 'committer': {'date': date}}}


@pytest.fixture
def extractor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / COMMIT_AUTHORS_FILE).write_text(
        'email,github_username,name,source\n'
        'whit@localhost,whitmo,Whit Morriss,Review\n'
        'bsaller@localhost,,Benjamin Saller,Review\n'
        'linked@example.org,someone-else,X,Review\n', encoding='utf-8')
    (tmp_path / ACCOUNT_ALIASES_FILE).write_text(
        'alias,github_username,source\nbobdobbs666,runyaga,Same address\n', encoding='utf-8')

    linked = {'linked@example.org': 'alice', 'alan@enfoldsystems.com': 'bobdobbs666'}

    def fake_graphql(session, query, variables=None, **kwargs):
        shas = [part.split('"')[1] for part in query.split('object(oid: ')[1:]]
        return {'repository': {f'c{i}': {'author': {'user': {'login': linked[sha]} if sha in linked else None}}
                               for i, sha in enumerate(shas)}}

    monkeypatch.setattr(plone_contributors, 'github_graphql', fake_graphql)
    return PloneStatsExtractor(token='test-token', periods=year_periods(2003, 2003))


def logins(extractor, *emails):
    # The sha is the email here, so that the fake GraphQL can answer per email
    commits = [local_commit(email.strip().lower(), email) for email in emails]
    extractor.link_authors('Products.CMFPlone', commits)
    return [c['author'] and c['author']['login'] for c in commits]


def test_unlinked_emails_are_mapped(extractor):
    assert logins(extractor, 'Whit@localhost ', 'bsaller@localhost', 'unknown@localhost') == [
        'whitmo', 'Benjamin Saller', None]


def test_github_links_win_over_the_mapping(extractor):
    assert logins(extractor, 'linked@example.org') == ['alice']


def test_second_accounts_count_for_the_main_account(extractor):
    assert logins(extractor, 'alan@enfoldsystems.com') == ['runyaga']

    extractor.process_pull_requests('Products.CMFPlone', [
        {'merged_at': '2003-05-01T12:00:00Z', 'user': {'login': 'bobdobbs666', 'type': 'User'}}])
    assert extractor.contributors_data['2003-plone-contributors']['runyaga']['pull_requests'] == 1


# Format checks


def read(name):
    with open(ROOT / name, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_commit_authors_format():
    fields, rows = read(COMMIT_AUTHORS_FILE)
    assert fields == ['email', 'github_username', 'name', 'source']

    emails = [row['email'] for row in rows]
    assert len(emails) == len(set(emails)), 'an email is listed twice'
    for row in rows:
        assert row['email'] == row['email'].strip().lower() and '@' in row['email'], row
        assert row['source'].strip(), row
        if row['github_username']:
            assert LOGIN.fullmatch(row['github_username']), row
        else:
            # People without a GitHub account are counted by name; a name is no valid login
            assert row['name'].strip() and not LOGIN.fullmatch(row['name']), row


def test_account_aliases_format():
    fields, rows = read(ACCOUNT_ALIASES_FILE)
    assert fields == ['alias', 'github_username', 'source']

    aliases = {row['alias'] for row in rows}
    for row in rows:
        assert LOGIN.fullmatch(row['alias']) and LOGIN.fullmatch(row['github_username']), row
        assert row['github_username'] not in aliases, f"chained alias: {row}"
        assert row['source'].strip(), row
