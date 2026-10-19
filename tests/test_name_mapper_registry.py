"""The changelog NameMapper asks the registry: identities first, then collected logins, then bots."""

from scripts.lib.changelogs import NameMapper
from scripts.lib.model import Identity, Person, Registry

SVN = '8e7b5d44-0c2e-0410-a6c3-b8c4e1e1bd1f'


def make_mapper(logins=(), bots=()):
    people = [
        Person('alex-clark', 'Alex Clark', 'aclark4life', 'https://example.org/a'),
        Person('riaan-booysen', 'Riaan Booysen', None, 'https://example.org/r'),
        Person('runyaga', 'Alan Runyan', 'runyaga', 'https://example.org/y'),
    ]
    identities = [
        Identity('alex-clark', 'email', f'aclark@{SVN}', 'https://example.org/a'),
        Identity('runyaga', 'login', 'bobdobbs666', 'https://example.org/y'),
    ]
    return NameMapper(Registry(people, identities, [], []), logins, bots)


def test_svn_local_part_resolves_through_email_identity():
    assert make_mapper().map('aclark') == ('aclark4life', 'identity')


def test_email_resolves_through_email_identity():
    assert make_mapper().map(f'aclark@{SVN}') == ('aclark4life', 'identity')


def test_name_equal_to_collected_login_resolves():
    assert make_mapper(logins=['Somelogin']).map('somelogin') == ('Somelogin', 'login')


def test_no_login_person_is_written_with_prefix():
    assert make_mapper().map('Riaan Booysen') == ('person:riaan-booysen', 'identity')


def test_second_account_counts_under_the_main_login():
    assert make_mapper(logins=['bobdobbs666']).map('bobdobbs666') == ('runyaga', 'identity')


def test_bot_is_dropped():
    mapper = make_mapper(bots=['mister-roboto'])
    assert mapper.map('mister-roboto') == (None, 'bot')
    assert mapper.map('pre-commit-ci[bot]') == (None, 'bot')


def test_unknown_name_stays_unmatched():
    assert make_mapper().map(' someone@example.org ') == ('someone@example.org', 'unmatched')
