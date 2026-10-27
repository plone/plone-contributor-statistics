import hashlib

from scripts.tools import mask_address as tool


def h(address):
    return 'h-' + hashlib.sha256(address.encode()).hexdigest()[:16]


def test_the_tool_prints_the_three_forms_of_a_company_address(capsys):
    tool.main(['Jane@acme.test'])
    out = capsys.readouterr().out
    assert out == ('Jane@acme.test\n'
                   f'  identities: {h("jane@acme.test")}\n'
                   f'  notes:      {h("jane@acme.test")} (an address at acme.test)\n'
                   f'  snippets:   {h("jane@acme.test")}@acme.test\n')


def test_the_tool_prints_a_general_service_address_bare_in_every_form(capsys):
    tool.main(['jane@gmx.test'])
    out = capsys.readouterr().out
    bare = h('jane@gmx.test')
    assert out == f'jane@gmx.test\n  identities: {bare}\n  notes:      {bare}\n  snippets:   {bare}\n'
