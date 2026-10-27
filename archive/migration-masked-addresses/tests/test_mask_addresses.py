import shutil
import subprocess
from pathlib import Path

from conftest import record_source
from scripts.lib import paths
from scripts.lib.addresses import mask_address
from scripts.lib.model import Citation, Identity, load_citations, load_identities, write_citations, write_identities
from scripts.tools import mask_addresses as tool

JANE = 'jane@acme.test'
SPELLED = 'natea at jazkarta dot test'


def track():
    """Make the current directory a git repository with every file tracked: the tool reads `git ls-files`."""
    subprocess.run(['git', 'init', '-q'], check=True)
    subprocess.run(['git', 'add', '-A'], check=True)


def registers(monkeypatch):
    """Jane with an address identity and a citation; an excerpt, an archive file and a collected CSV file."""
    monkeypatch.setattr(tool, 'SPELLED_ADDRESSES',
                        {tool.spelled_key(SPELLED): (mask_address('natea@jazkarta.test'), 'jazkarta.test')})
    sid = record_source()
    (paths.EXCERPTS_DIR / f'{sid}.md').write_text(f'Author: Jane <{JANE}>\n\nWrite to {SPELLED}.\n',
                                                  encoding='utf-8')
    paths.PEOPLE.write_text('id,name\njane-doe,Jane Doe\n', encoding='utf-8')
    write_identities([Identity('jane-doe', 'email', JANE, sid, f'Author: Jane <{JANE}>', f'see {JANE}')])
    write_citations([Citation('jane-doe-acme', sid, f'Jane <{JANE}>', None, f'from {JANE}')])
    archive = Path('archive/old.md')
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(f'Mail {JANE}.\n', encoding='utf-8')
    collected = Path('collected/changelogs/2020.csv')
    collected.parent.mkdir(parents=True, exist_ok=True)
    collected.write_text(f'author,count\n"Doe, Jane <{JANE}>",1\nplain,2\n', encoding='utf-8')
    return sid


def test_write_masks_the_value_bare_and_the_snippet_with_its_domain(tmp_repo, monkeypatch):
    sid = registers(monkeypatch)
    track()
    tool.main(['write'])
    [identity] = load_identities()
    assert identity.value == mask_address(JANE)
    assert identity.snippet == f'Author: Jane <{mask_address(JANE, keep_domain=True)}>'
    assert identity.notes == f'see {mask_address(JANE)} (an address at acme.test)'
    [citation] = load_citations()
    assert citation.snippet == f'Jane <{mask_address(JANE, keep_domain=True)}>'
    assert citation.notes == f'from {mask_address(JANE)} (an address at acme.test)'
    excerpt = (paths.EXCERPTS_DIR / f'{sid}.md').read_text(encoding='utf-8')
    assert f'Author: Jane <{mask_address(JANE, keep_domain=True)}>' in excerpt
    assert mask_address(JANE, keep_domain=True).endswith('@acme.test')
    assert Path('archive/old.md').read_text(encoding='utf-8') == f'Mail {mask_address(JANE)}.\n'


def test_write_masks_a_spelled_out_address_in_the_form_of_its_place(tmp_repo, monkeypatch):
    sid = registers(monkeypatch)
    track()
    tool.main(['write'])
    excerpt = (paths.EXCERPTS_DIR / f'{sid}.md').read_text(encoding='utf-8')
    assert f'Write to {mask_address("natea@jazkarta.test", keep_domain=True)}.' in excerpt
    assert SPELLED not in excerpt


def test_write_keeps_the_csv_quoting(tmp_repo, monkeypatch):
    registers(monkeypatch)
    track()
    tool.main(['write'])
    assert Path('collected/changelogs/2020.csv').read_text(encoding='utf-8') == (
        f'author,count\n"Doe, Jane <{mask_address(JANE)}>",1\nplain,2\n')


def test_write_leaves_placeholder_addresses_and_unchecked_spellings(tmp_repo, monkeypatch):
    monkeypatch.setattr(tool, 'SPELLED_ADDRESSES', {})
    note = Path('archive/note.md')
    note.parent.mkdir(parents=True, exist_ok=True)
    text = 'Write to user@example.com, or look at plone dot org.\n'
    note.write_text(text, encoding='utf-8')
    track()
    tool.main(['write'])
    assert note.read_text(encoding='utf-8') == text


def test_masking_twice_changes_nothing(tmp_repo, monkeypatch):
    registers(monkeypatch)
    track()
    tool.main(['write'])
    before = {p: p.read_bytes() for p in Path('.').rglob('*') if p.is_file() and '.git' not in p.parts}
    tool.main(['write'])
    assert before == {p: p.read_bytes() for p in before}


def test_list_names_the_address_its_class_and_its_files(tmp_repo, monkeypatch, capsys):
    registers(monkeypatch)
    track()
    tool.main(['list'])
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if line.startswith(JANE))
    assert 'company' in line and 'archive/old.md' in line
    assert 'natea at jazkarta dot test' in out


def copy_mappings(target):
    """A copy of the registers of the current directory, in the layout load_registry expects."""
    shutil.copytree(paths.MAPPINGS_DIR, target / 'curated/mappings')
    return target / 'curated/mappings'


def reader(authors):
    return lambda path: authors


def test_verify_finds_no_difference_for_a_masked_identity(tmp_repo, monkeypatch, tmp_path_factory):
    registers(monkeypatch)
    old = copy_mappings(tmp_path_factory.mktemp('old'))
    [identity] = load_identities()
    write_identities([identity.__class__(identity.person, 'email', mask_address(JANE), identity.source,
                                         identity.snippet, identity.notes)])
    authors = [('a1', 'Jane@ACME.test', 'J.', '2020-01-01T00:00:00Z'),
               ('a2', 'nobody@acme.test', 'Nobody', '2020-01-01T00:00:00Z')]
    pairs, differences = tool.compare(old, paths.MAPPINGS_DIR, ['clone'], read=reader(authors))
    assert pairs == 2
    assert differences == []


def test_verify_reports_a_dropped_identity(tmp_repo, monkeypatch, tmp_path_factory):
    registers(monkeypatch)
    old = copy_mappings(tmp_path_factory.mktemp('old'))
    write_identities([])
    authors = [('a1', JANE, 'J.', '2020-01-01T00:00:00Z')]
    pairs, differences = tool.compare(old, paths.MAPPINGS_DIR, ['clone'], read=reader(authors))
    assert differences == [(JANE, 'J.', 'jane-doe', None)]


def test_write_masks_a_spelling_with_dots_on_both_sides_as_a_whole(tmp_repo, monkeypatch):
    spellings = {'ken <dot> doe <at> acme.test': 'ken.doe@acme.test', 'rj at moss dot org dot test': 'rj@moss.org.test'}
    monkeypatch.setattr(tool, 'SPELLED_ADDRESSES', {tool.spelled_key(text): (mask_address(address), None)
                                                    for text, address in spellings.items()})
    note = Path('archive/note.md')
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text('Write to ken <dot> doe <at> acme.test or to rj at moss dot org dot test - or look at plone.org.\n',
                    encoding='utf-8')
    track()
    tool.main(['write'])
    assert note.read_text(encoding='utf-8') == (f'Write to {mask_address("ken.doe@acme.test")} or to '
                                                f'{mask_address("rj@moss.org.test")} - or look at plone.org.\n')


def test_the_index_of_the_email_identities_keeps_every_address_and_its_person(tmp_repo, monkeypatch,
                                                                              tmp_path_factory):
    registers(monkeypatch)
    old = copy_mappings(tmp_path_factory.mktemp('old'))
    [identity] = load_identities()
    write_identities([identity.__class__(identity.person, 'email', mask_address(JANE), identity.source,
                                         identity.snippet, identity.notes)])
    assert tool.email_index_differences(old, paths.MAPPINGS_DIR) == []
    write_identities([identity.__class__('john-doe', 'email', mask_address(JANE), identity.source)])
    assert tool.email_index_differences(old, paths.MAPPINGS_DIR) == [(JANE, {'jane-doe'}, {'john-doe'})]


def test_notes_of_the_registers_name_the_company_domain_in_words(tmp_repo, monkeypatch):
    registers(monkeypatch)
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n'
                                  f'a1,jane-doe,acme,2006,2006,stated,,"Jane Doe / {JANE}, bob@gmx.test"\n',
                                  encoding='utf-8')
    track()
    tool.main(['write'])
    words = f'{mask_address(JANE)} (an address at acme.test)'
    [identity] = load_identities()
    assert identity.notes == f'see {words}'
    assert identity.snippet == f'Author: Jane <{mask_address(JANE, keep_domain=True)}>'
    [citation] = load_citations()
    assert citation.notes == f'from {words}'
    assert paths.AFFILIATIONS.read_text(encoding='utf-8').splitlines()[1] == (
        f'a1,jane-doe,acme,2006,2006,stated,,"Jane Doe / {words}, {mask_address("bob@gmx.test")}"')
    # Elsewhere the bare form
    assert Path('archive/old.md').read_text(encoding='utf-8') == f'Mail {mask_address(JANE)}.\n'
    before = paths.IDENTITIES.read_bytes(), paths.CITATIONS.read_bytes(), paths.AFFILIATIONS.read_bytes()
    tool.main(['write'])
    assert (paths.IDENTITIES.read_bytes(), paths.CITATIONS.read_bytes(), paths.AFFILIATIONS.read_bytes()) == before


def test_a_spelled_out_address_in_notes_names_its_domain_in_words(tmp_repo, monkeypatch):
    registers(monkeypatch)
    write_citations([Citation('jane-doe-acme', None, None, None, f'cited as: "write to {SPELLED}"')])
    track()
    tool.main(['write'])
    [citation] = load_citations()
    assert citation.notes == f'cited as: "write to {mask_address("natea@jazkarta.test")} (an address at jazkarta.test)"'
