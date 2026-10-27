import hashlib

from scripts.lib.addresses import (NOT_PERSONAL, address_hash, is_masked, mask_address, mask_address_for_notes,
                                   mask_text, readable_addresses)


# An invented machine name; built here, because no domain of machine names is reserved, so that the check for
# readable addresses in the repository (test_no_readable_addresses) passes
MACHINE = 'jane@' + 'janes-imac.local'


def h(address):
    return 'h-' + hashlib.sha256(address.encode()).hexdigest()[:16]


def test_hash_normalises_case_space_and_brackets():
    assert address_hash(' <Jane.Doe@Acme.TEST> ') == h('jane.doe@acme.test')


def test_company_address_keeps_its_domain_only_when_asked():
    assert mask_address('Jane@Acme.test', keep_domain=True) == h('jane@acme.test') + '@acme.test'
    assert mask_address('Jane@Acme.test') == h('jane@acme.test')


def test_general_service_and_machine_names_are_masked_completely():
    for address in ('jane@gmx.test', MACHINE, 'jane@example.com'):
        assert mask_address(address, keep_domain=True) == h(address)


def test_subversion_noreply_and_not_personal_stay():
    for address in ('jdoe@localhost', 'jdoe@3b4cdb85-528f-c531-b63d-5919d5b1aa08',
                    '123+jdoe@users.noreply.github.com', 'git@github.com'):
        assert mask_address(address) == address
        assert mask_address(address, keep_domain=True) == address


def test_masking_is_idempotent():
    with_domain = mask_address('jane@acme.test', keep_domain=True)
    assert mask_address(with_domain, keep_domain=True) == with_domain
    text = 'Author: Jane <jane@acme.test>\nCc: bob@gmx.test'
    for keep in (False, True):
        assert mask_text(mask_text(text, keep), keep) == mask_text(text, keep)


def test_bare_form_drops_the_domain_of_a_masked_value():
    bare = h('jane@acme.test')
    assert mask_address(bare + '@acme.test') == bare
    assert mask_address(bare) == bare


def test_mask_text_replaces_only_addresses():
    text = ('Author: Jane <jane@acme.test>, see https://acme.test/@jane and @jarn.com; '
            'react@18.2.0, @plone/volto, gocept@Saltlabs, git@github.com:plone/x.git')
    assert mask_text(text, keep_domain=True) == text.replace('jane@acme.test', h('jane@acme.test') + '@acme.test')
    assert mask_text(text) == text.replace('jane@acme.test', h('jane@acme.test'))


def test_is_masked():
    assert is_masked(h('a@b.test')) and is_masked(h('a@b.test') + '@b.test')
    assert not is_masked('jane@acme.test') and not is_masked('h-xyz@acme.test')


def test_value_without_at_sign_is_unchanged():
    assert mask_address('Jane Doe') == 'Jane Doe'


def test_reserved_domains_and_masked_values_are_not_readable():
    text = 'a jane@acme.test b ' + mask_address('jane@acme.test', keep_domain=True) + ' c x@example.com y@mail.example.org'
    assert readable_addresses(text) == []


def test_a_raw_address_in_a_real_domain_is_readable():
    address = 'jane@' + 'acme' + '.com'
    assert readable_addresses(f'write to {address}, please') == [address]


def test_noreply_and_svn_addresses_are_not_readable():
    assert readable_addresses('1+jdoe@users.noreply.github.com and git@github.com') == []


def test_an_address_glued_to_a_capitalised_word_ends_with_its_domain():
    # As in a page whose text lost its spaces: the address, then a title
    text = 'jane@acme.testPlone Conf 2010; JANE@ACME.TEST; jane@Acme.Test.'
    assert mask_text(text) == (h('jane@acme.test') + 'Plone Conf 2010; ' + h('jane@acme.test') + '; '
                               + h('jane@acme.test') + '.')


def test_every_address_that_is_not_personal_stays_and_says_why():
    for address, reason in NOT_PERSONAL.items():
        assert address == address.lower() and reason
        assert mask_address(address, keep_domain=True) == address
        assert readable_addresses(f'write to {address}') == []


def test_an_address_in_markdown_emphasis_is_masked_without_the_underscores():
    text = 'Author: Jane _jane@acme.test_ <jane_doe@acme.test>'
    assert mask_text(text, keep_domain=True) == (f'Author: Jane _{h("jane@acme.test")}@acme.test_ '
                                                 f'<{h("jane_doe@acme.test")}@acme.test>')
    assert mask_text(text) == f'Author: Jane _{h("jane@acme.test")}_ <{h("jane_doe@acme.test")}>'


def test_an_address_in_markdown_emphasis_is_readable():
    address = 'jane@' + 'acme' + '.com'
    assert readable_addresses(f'Author: Jane _{address}_') == [address]


def test_a_masked_value_with_a_company_domain_is_not_readable():
    masked = mask_address('jane@' + 'acme' + '.com', keep_domain=True)
    assert masked == h('jane@' + 'acme' + '.com') + '@' + 'acme' + '.com'
    assert readable_addresses(f'Author: Jane <{masked}> and _{masked}_') == []


def test_the_notes_name_the_domain_of_a_company_address_in_words():
    words = h('jane@acme.test') + ' (an address at acme.test)'
    assert mask_address_for_notes('Jane@Acme.test') == words
    assert mask_address_for_notes(h('jane@acme.test') + '@acme.test') == words
    assert readable_addresses(mask_address_for_notes('jane@' + 'acme' + '.com')) == []


def test_the_notes_give_other_addresses_bare_or_unchanged():
    assert mask_address_for_notes('jane@gmx.test') == h('jane@gmx.test')
    assert mask_address_for_notes(MACHINE) == h(MACHINE)
    assert mask_address_for_notes('jdoe@localhost') == 'jdoe@localhost'
    assert mask_address_for_notes('Jane Doe') == 'Jane Doe'
