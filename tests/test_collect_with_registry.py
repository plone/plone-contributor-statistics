"""People behind unlinked commit emails, and second accounts, through the registers (#69, #139)."""

import pytest

from scripts.collect import plone_contributors
from scripts.collect.plone_contributors import PloneStatsExtractor, year_periods
from scripts.lib import paths

SRC = 'https://example.org/record'


def local_commit(sha, email):
    date = '2003-06-01T10:00:00Z'
    return {'sha': sha, 'parents': [{'sha': 'p'}], 'author': None,
            'commit': {'author': {'name': 'x', 'email': email, 'date': date}, 'committer': {'date': date}}}


@pytest.fixture
def extractor(tmp_repo, monkeypatch):
    paths.PEOPLE.write_text(
        'id,name,github,source\n'
        f'whit-morriss,Whit Morriss,whitmo,{SRC}\n'
        f'benjamin-saller,Benjamin Saller,,{SRC}\n'
        f'alan-runyan,Alan Runyan,runyaga,{SRC}\n', encoding='utf-8')
    paths.IDENTITIES.write_text(
        'person,kind,value,source\n'
        f'whit-morriss,email,whit@localhost,{SRC}\n'
        f'benjamin-saller,email,bsaller@localhost,{SRC}\n'
        f'whit-morriss,email,linked@example.org,{SRC}\n'
        f'alan-runyan,login,bobdobbs666,{SRC}\n'
        f'benjamin-saller,login,bsaller-gh,{SRC}\n', encoding='utf-8')

    linked = {'linked@example.org': 'alice', 'bot@example.org': 'pre-commit-ci[bot]',
              'alan@enfoldsystems.com': 'bobdobbs666', 'ben@example.org': 'bsaller-gh'}

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
        'whitmo', 'person:benjamin-saller', None]


def test_github_links_win_over_the_registers(extractor):
    assert logins(extractor, 'linked@example.org') == ['alice']


def test_second_accounts_count_for_the_main_account(extractor):
    assert logins(extractor, 'alan@enfoldsystems.com') == ['runyaga']

    extractor.process_pull_requests('Products.CMFPlone', [
        {'merged_at': '2003-05-01T12:00:00Z', 'user': {'login': 'bobdobbs666', 'type': 'User'}}])
    assert extractor.contributors_data['2003-plone-contributors']['runyaga']['pull_requests'] == 1


def test_second_account_of_a_person_without_github_counts_for_the_person(extractor):
    # As the changelog collector counts it: person:<id>, not the login, so that the person counts once
    assert logins(extractor, 'ben@example.org') == ['person:benjamin-saller']

    extractor.process_pull_requests('Products.CMFPlone', [
        {'merged_at': '2003-05-01T12:00:00Z', 'user': {'login': 'BSaller-GH', 'type': 'User'}}])
    assert extractor.contributors_data['2003-plone-contributors']['person:benjamin-saller']['pull_requests'] == 1


def test_linked_bot_login_stays_a_bot(extractor):
    commits = [local_commit('bot@example.org', 'bot@example.org')]
    extractor.link_authors('Products.CMFPlone', commits)

    assert commits[0]['author'] == {'login': 'pre-commit-ci[bot]', 'type': 'Bot'}
    assert not extractor._is_person(commits[0]['author'])
