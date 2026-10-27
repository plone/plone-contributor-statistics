from scripts.lib.addresses import mask_address
from scripts.tools import mask_address as tool


def test_the_tool_prints_both_forms(capsys):
    tool.main(['Jane@acme.test'])
    out = capsys.readouterr().out
    assert f'identities and notes: {mask_address("Jane@acme.test")}\n' in out
    assert f'snippets:             {mask_address("Jane@acme.test", keep_domain=True)}\n' in out
    assert mask_address('Jane@acme.test', keep_domain=True).endswith('@acme.test')
