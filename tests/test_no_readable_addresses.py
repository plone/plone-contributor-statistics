"""No readable mail address in the repository, see docs/explanation/attribution.md.

Every tracked text file holds masked addresses only, apart from the Subversion-era, noreply and not personal
addresses (`NOT_PERSONAL`) and the domains reserved for examples and tests. The form that keeps a company domain
belongs to the excerpts and the `snippet` cells quoting them, and to the tests of the masking.
"""
import csv
import io
import subprocess

from conftest import REPO
from scripts.lib import paths
from scripts.lib.addresses import MASKED_WITH_DOMAIN, readable_addresses

# The registers whose `snippet` cells quote the excerpts, and so keep a company domain
SNIPPET_FILES = {paths.IDENTITIES.as_posix(), paths.CITATIONS.as_posix()}


def tracked_texts():
    """(path, text) of every tracked text file: no file with a NUL byte or that is not UTF-8."""
    output = subprocess.run(['git', 'ls-files', '-z'], cwd=REPO, capture_output=True, check=True).stdout
    for name in sorted(n for n in output.decode().split('\0') if n):
        path = REPO / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b'\0' in data:
            continue
        try:
            yield name, data.decode('utf-8')
        except UnicodeDecodeError:
            continue


def test_no_tracked_file_holds_a_readable_address():
    found = {name: addresses for name, text in tracked_texts() if (addresses := readable_addresses(text))}
    assert not found, 'readable mail addresses, mask them with python -m scripts.tools.mask_address: ' + '; '.join(
        f'{name}: {", ".join(sorted(set(addresses)))}' for name, addresses in sorted(found.items()))


def _cells_with_domain(name, text):
    """The masked values with a domain outside the snippet column of a register."""
    rows = csv.DictReader(io.StringIO(text, newline=''))
    return [f'row {number}, {field}' for number, row in enumerate(rows, start=2)
            for field, value in row.items() if field != 'snippet' and MASKED_WITH_DOMAIN.search(value or '')]


def test_the_form_with_a_domain_only_in_excerpts_snippets_and_tests():
    excerpts = paths.EXCERPTS_DIR.as_posix() + '/'
    found = {}
    for name, text in tracked_texts():
        if name.startswith((excerpts, 'tests/')):
            continue
        if name in SNIPPET_FILES:
            places = _cells_with_domain(name, text)
        else:
            places = sorted({match.group(0) for match in MASKED_WITH_DOMAIN.finditer(text)})
        if places:
            found[name] = places
    assert not found, 'masked addresses with a domain outside excerpts and snippets, use the bare form: ' + '; '.join(
        f'{name}: {", ".join(places)}' for name, places in sorted(found.items()))
