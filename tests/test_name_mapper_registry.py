"""The changelog NameMapper asks the registry: identities first, then collected logins, then bots."""

from scripts.lib.changelogs import NameMapper
from scripts.lib.model import Identity
from tests.conftest import registry_of

SVN = '8e7b5d44-0c2e-0410-a6c3-b8c4e1e1bd1f'


def make_mapper(logins=(), bots=(), people=(), identities=()):
    people = [
        *people,
        ('alex-clark', 'Alex Clark', 'aclark4life', 'https://example.org/a'),
        ('riaan-booysen', 'Riaan Booysen', None, 'https://example.org/r'),
        ('runyaga', 'Alan Runyan', 'runyaga', 'https://example.org/y'),
    ]
    identities = [
        *identities,
        Identity('alex-clark', 'email', f'aclark@{SVN}', 'https://example.org/a'),
        Identity('runyaga', 'github-alias', 'bobdobbs666', 'https://example.org/y'),
    ]
    return NameMapper(registry_of(people, identities), logins, bots)


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


def test_single_token_name_identity_matches():
    mapper = make_mapper(people=[('jens-w-klein', 'Jens W. Klein', 'jensens', 'https://example.org/j')],
                         identities=[Identity('jens-w-klein', 'name', 'yenzens', 'https://example.org/j')])
    assert mapper.map('yenzens') == ('jensens', 'identity')


def test_first_name_without_identity_is_unmatched():
    assert make_mapper().map('Andy') == ('Andy', 'unmatched')


def test_local_part_of_an_ordinary_address_does_not_resolve():
    mapper = make_mapper(identities=[Identity('runyaga', 'email', 'tiran@example.org', 'https://example.org/y')])
    assert mapper.map('tiran') == ('tiran', 'unmatched')


def kims(logins=()):
    people = [('kim-a', 'Kim A', 'kima', 'https://example.org/a'),
              ('kim-b', 'Kim B', 'kimb', 'https://example.org/b')]
    identities = [Identity('kim-a', 'name', 'Kim', 'https://example.org/a'),
                  Identity('kim-b', 'name', 'Kim', 'https://example.org/b')]
    return make_mapper(logins=logins, people=people, identities=identities)


def test_ambiguous_name_falls_through():
    assert kims().map('Kim') == ('Kim', 'unmatched')
    assert kims(logins=['kim']).map('Kim') == ('kim', 'login')


def test_ambiguous_svn_local_part_is_unmatched():
    people = [('pat-a', 'Pat A', 'pata', 'https://example.org/a'),
              ('pat-b', 'Pat B', 'patb', 'https://example.org/b')]
    identities = [Identity('pat-a', 'email', 'pat@localhost', 'https://example.org/a'),
                  Identity('pat-b', 'email', 'pat@localhost', 'https://example.org/b')]
    assert make_mapper(people=people, identities=identities).map('pat') == ('pat', 'unmatched')
