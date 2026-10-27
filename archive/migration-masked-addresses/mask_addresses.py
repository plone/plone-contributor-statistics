#!/usr/bin/env python3
"""Mask the mail addresses in the tracked files once: the migration to masked addresses.

    list    every distinct address in the tracked text files, with its count, its class and its files, and the
            addresses spelled out to fool harvesters ("jane at acme dot com")
    write   mask them, by the rule of docs/explanation/attribution.md: the excerpts and the `snippet` cells of
            identities.csv and citations.csv keep a company domain, the `notes` cells of the registers in
            curated/mappings name it in words ("h-… (an address at acme.test)"), everything else gets the
            bare hash, the value of an email identity included
    verify  compare the persons the old registers (at --base) and the new ones (the working tree) find for every
            commit author of the cached clones; exit code 1 on any difference

Placeholder addresses (example.com, .example, .invalid, .localhost) stay as they are: they are nobody's. A
spelled-out address is masked only when it is listed in SPELLED_ADDRESSES, after a person checked it: the patterns
also find prose ("look at plone dot org").
"""

import argparse
import csv
import io
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from scripts.collect.plone_changelogs import ORGANISATION, cached_repositories
from scripts.lib import git_history, paths
from scripts.lib.addresses import ADDRESS, address_hash, is_masked, mask_address
from scripts.lib.commit_authors import Finder
from scripts.lib.model import load_bot_accounts, load_registry
from scripts.lib.model.registers import load_citations, load_identities, write_citations, write_identities

FOLDERS = ('curated', 'collected', 'derived', 'reports', 'archive')
SPELLED = re.compile(r'\b([\w.]+)\s+(?:at|\[at\])\s+([\w-]+)\s+(?:dot|\[dot\])\s+([a-z]{2,})\b', re.I)
# Domains reserved for documentation: an address there is nobody's
PLACEHOLDER = re.compile(r'(?:\.(?:example|invalid|localhost)|(?:^|\.)example\.(?:com|org|net))$')

# The addresses spelled out to fool harvesters, found by `list` and by searches for other spellings, and checked
# by hand: each is a person's address. A spelled-out candidate (`SPELLED_CANDIDATE`) is masked when the hash of its
# text, white space folded, is listed here; the value is the hash of the address and the company domain it keeps in
# excerpts and snippets, if any. Hashes, because the spelled-out text is as readable as the address.
SPELLED_ADDRESSES = {
    'h-d842773901994c1d': ('h-200871da9d06eef6', 'aclark.net'),
    'h-96ab5a90f6f5ad2e': ('h-aef3104a9bd7a9a1', 'iosn.net'),
    'h-f885a904ed5b1e9d': ('h-2f548dd4da4cb8a8', 'plope.com'),
    'h-c3147de9890c7814': ('h-ba3368f7a368cf0c', None),
    'h-6b187932acd833fc': ('h-37fee78d98b1b8b1', 'chaoflow.net'),
    'h-61e2d21e2daa9220': ('h-7797f72bcd6864c0', None),
    'h-1df0078d9b5ca0fe': ('h-2a81dec361a96bc4', 'elkner.net'),
    'h-2e75821bd5a143cd': ('h-6ccc515a924f4c52', None),
    'h-336fd27693e46e25': ('h-3e7062edbd9c37a9', 'contextualcorp.com'),
    'h-44fb049cb2c49fef': ('h-d6b9ea48c4fc161d', 'jazkarta.com'),
    'h-769b04011011574e': ('h-a13eb3cd6593d0d2', 'moss.org.ph'),
    'h-e7fc4c145de58b5c': ('h-c8b693ff54ea4c77', 'pretaweb.com'),
    'h-6535ee48a4d3857b': ('h-b1e01befe255a634', None),
    'h-12283b81858ea36e': ('h-646a8fe09b59a679', '4teamwork.ch'),
}
# Words, "at" and a domain whose labels are separated by "dot" or by dots, in the spellings found
_AT = r'(?:at|<at>|\[at\])'
_DOT = r'(?:dot|<dot>|\[dot\])'
SPELLED_CANDIDATE = re.compile(rf'(?<![\w.])[\w.\-]+(?:\s+{_DOT}\s+[\w\-]+)*\s+{_AT}\s+[\w\-]+'
                               rf'(?:(?:\s+{_DOT}\s+|\.)[\w\-]+)+', re.I)


def spelled_key(text):
    """The key of a spelled-out address in SPELLED_ADDRESSES: the hash of its text, white space folded."""
    return address_hash(' '.join(text.split()))


def spelled_masked(text, keep_domain=False):
    """The masked form of a checked spelled-out address, with its company domain when asked; else None."""
    if spelled_key(text) not in SPELLED_ADDRESSES:
        return None
    bare, domain = SPELLED_ADDRESSES[spelled_key(text)]
    return f'{bare}@{domain}' if keep_domain and domain else bare


def is_placeholder(address):
    return bool(PLACEHOLDER.search(address.rsplit('@', 1)[1].lower()))


def in_words(masked):
    """A masked value with a company domain as the notes of the registers give it: the hash, then the domain in
    words, which the guard against readable addresses accepts; a bare hash as it is."""
    if '@' not in masked:
        return masked
    bare, domain = masked.split('@', 1)
    return f'{bare} (an address at {domain})'


def mask(text, keep_domain=False, words=False):
    """The text with every address masked, placeholders left, and the checked spelled-out addresses masked.

    keep_domain: a company address keeps its domain, as in the excerpts and snippets. words: a company address
    becomes its hash and the domain in words, as in the notes of the registers ("h-… (an address at acme.test)")."""
    def address(match):
        found = match.group(0)
        if is_placeholder(found):
            return found
        if words:
            masked = mask_address(found, keep_domain=True)
            return in_words(masked) if is_masked(masked) else masked
        return mask_address(found, keep_domain)

    def spelled(match):
        masked = spelled_masked(match.group(0), keep_domain or words)
        if masked is None:
            return match.group(0)
        return in_words(masked) if words else masked

    return SPELLED_CANDIDATE.sub(spelled, ADDRESS.sub(address, text))


def tracked_files(folders=FOLDERS):
    """The tracked text files below the folders: no file with a NUL byte or that is not UTF-8."""
    output = subprocess.run(['git', 'ls-files', '-z', '--', *folders], capture_output=True, check=True).stdout
    files = []
    for name in sorted(n for n in output.decode().split('\0') if n):
        path = Path(name)
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b'\0' in data:
            continue
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        files.append(path)
    return files


def is_excerpt(path):
    return path.parent == paths.EXCERPTS_DIR and path.suffix == '.md'


def _read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def _write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def _csv_text(rows):
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator='\n').writerows(rows)
    return buffer.getvalue()


def mask_csv(text, words_columns=()):
    """The CSV text with every cell masked, bare, or in words in the named columns; the quoting as it was.

    Through the csv module when the file reads and writes back unchanged; otherwise as text, which gives the same
    result for the bare form, because an address and its hash hold no comma, quote or line break and so never
    cross a cell."""
    rows = list(csv.reader(io.StringIO(text, newline='')))
    if _csv_text(rows) != text:
        if words_columns:
            raise ValueError('a register that does not read and write back unchanged')
        return mask(text)
    if not rows:
        return text
    header = rows[0]
    words = [name in words_columns for name in header]
    return _csv_text([header] + [[mask(cell, words=n < len(words) and words[n]) for n, cell in enumerate(row)]
                                 for row in rows[1:]])


def _masked_cells(row, fields):
    """The changed cells of a register row: the snippet with its domain, the notes with the domain in words, the
    other text cells bare."""
    changes = {}
    for field in fields:
        value = getattr(row, field)
        if isinstance(value, str):
            masked = mask(value, keep_domain=field == 'snippet', words=field == 'notes')
            if masked != value:
                changes[field] = masked
    return changes


def mask_identities(mappings_dir=paths.MAPPINGS_DIR):
    """Mask identities.csv: the value of an email identity to its hash; True when something changed."""
    identities = load_identities(mappings_dir)
    masked = []
    for identity in identities:
        changes = _masked_cells(identity, ('person', 'kind', 'value', 'source', 'snippet', 'notes'))
        if identity.kind == 'email':
            changes['value'] = mask_address(identity.value)
        masked.append(replace(identity, **changes))
    if masked != identities:
        write_identities(masked, mappings_dir)
        return True
    return False


def mask_citations(mappings_dir=paths.MAPPINGS_DIR):
    """Mask citations.csv; True when something changed."""
    citations = load_citations(mappings_dir)
    masked = [replace(c, **_masked_cells(c, ('affiliation', 'source', 'snippet', 'supersedes', 'notes')))
              for c in citations]
    if masked != citations:
        write_citations(masked, mappings_dir)
        return True
    return False


def write(files):
    """Mask the files; the changed ones."""
    changed = []
    for path in files:
        if path == paths.IDENTITIES:
            if mask_identities(path.parent):
                changed.append(path)
            continue
        if path == paths.CITATIONS:
            if mask_citations(path.parent):
                changed.append(path)
            continue
        text = _read(path)
        if is_excerpt(path):
            new = mask(text, keep_domain=True)
        elif path.suffix == '.csv' and path.parent == paths.MAPPINGS_DIR:
            new = mask_csv(text, words_columns={'notes'})
        elif path.suffix == '.csv':
            new = mask_csv(text)
        else:
            new = mask(text)
        if new != text:
            _write(path, new)
            changed.append(path)
    return changed


def classify(address):
    """company (keeps its domain in excerpts and snippets), complete (the bare hash everywhere) or unchanged."""
    if is_placeholder(address):
        return 'unchanged: placeholder'
    if is_masked(address):
        return 'unchanged: masked'
    masked = mask_address(address, keep_domain=True)
    if masked == address:
        return 'unchanged: subversion, noreply or not personal'
    return 'company' if '@' in masked else 'complete'


def inventory(files):
    """({address: (count, {file})}, {spelled-out match: (rebuilt address, count, {file})},
    {spelled-out candidate in SPELLED_ADDRESSES: (masked form, count, {file})})."""
    found = defaultdict(lambda: [0, set()])
    spelled = defaultdict(lambda: [None, 0, set()])
    checked = defaultdict(lambda: [None, 0, set()])
    for path in files:
        text = _read(path)
        for match in ADDRESS.finditer(text):
            entry = found[match.group(0).lower()]
            entry[0] += 1
            entry[1].add(str(path))
        for match in SPELLED.finditer(text):
            entry = spelled[' '.join(match.group(0).split())]
            entry[0] = '{}@{}.{}'.format(*match.groups()).lower()
            entry[1] += 1
            entry[2].add(str(path))
        for match in SPELLED_CANDIDATE.finditer(text):
            masked = spelled_masked(match.group(0), keep_domain=True)
            if masked:
                entry = checked[' '.join(match.group(0).split())]
                entry[0] = masked
                entry[1] += 1
                entry[2].add(str(path))
    return found, spelled, checked


def print_inventory(files):
    found, spelled, checked = inventory(files)
    classes = defaultdict(int)
    for address, (count, where) in sorted(found.items()):
        kind = classify(address)
        classes[kind] += 1
        print(f'{address}\t{count}\t{kind}\t{" ".join(sorted(where))}')
    print()
    for kind, n in sorted(classes.items()):
        print(f'# {n} distinct addresses: {kind}')
    print()
    for text, (rebuilt, count, where) in sorted(spelled.items()):
        print(f'spelled\t{text}\t{rebuilt}\t{count}\t{" ".join(sorted(where))}')
    print()
    for text, (masked, count, where) in sorted(checked.items()):
        print(f'checked\t{text}\t{masked}\t{count}\t{" ".join(sorted(where))}')


def read_clone(path):
    """[(sha, email, name, date)] of every commit of the clone, the converted ones included."""
    return git_history.read_authors(path)


def compare(old_dir, new_dir, clones, read=read_clone, bots=None, workers=8):
    """(number of distinct authors, [(email, name, old person id, new person id)] that differ).

    An author is an (address, name) pair of a commit in the clones; the persons are those the registers in old_dir
    and in new_dir find for it, through the matching of the collectors (`Finder`)."""
    bots = load_bot_accounts() if bots is None else bots
    old, new = Finder(load_registry(old_dir), bots), Finder(load_registry(new_dir), bots)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(read, clones))
    authors = {(email, name) for result in results for _, email, name, _ in result}
    differences = []
    for email, name in sorted(authors):
        before, after = old.person(email, name), new.person(email, name)
        before, after = before and before.id, after and after.id
        if before != after:
            differences.append((email, name, before, after))
    return len(authors), differences


def email_index_differences(old_dir, new_dir):
    """The email identities whose person differs between the raw lower-cased values at old_dir and the hashes
    at new_dir: [(old value, old persons, new persons)]. Empty when no identity was lost and no hashes collide."""
    def index(identities, key):
        found = defaultdict(set)
        for identity in identities:
            if identity.kind == 'email':
                found[key(identity.value)].add(identity.person)
        return found

    old = index(load_identities(old_dir), str.lower)
    new = index(load_identities(new_dir), lambda value: mask_address(value).lower())
    return [(value, persons, new.get(mask_address(value).lower(), set()))
            for value, persons in sorted(old.items()) if new.get(mask_address(value).lower(), set()) != persons
            ] + ([('(number of keys)', len(old), len(new))] if len(old) != len(new) else [])


def _clones(cache):
    if not os.path.isdir(os.path.join(cache, ORGANISATION)) and os.path.isdir(os.path.join(cache, 'repositories')):
        cache = os.path.join(cache, 'repositories')
    return [os.path.join(cache, ORGANISATION, f'{name}.git') for name, _ in cached_repositories(cache)]


def verify(cache, base):
    clones = _clones(cache)
    if not clones:
        raise SystemExit(f'No clones in {cache}/{ORGANISATION}.')
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(['git', 'archive', base, str(paths.MAPPINGS_DIR)], capture_output=True, check=True)
        subprocess.run(['tar', '-x', '-C', tmp], input=archive.stdout, check=True)
        old_dir = Path(tmp) / paths.MAPPINGS_DIR
        index = email_index_differences(old_dir, paths.MAPPINGS_DIR)
        authors, differences = compare(old_dir, paths.MAPPINGS_DIR, clones)
    print(f'{len(clones)} clones, {authors} distinct authors (address and name), {len(differences)} differences; '
          f'{len(index)} differences in the index of the email identities')
    for email, name, before, after in differences:
        print(f'  {email}\t{name}\t{before} -> {after}')
    for value, before, after in index:
        print(f'  identity {value}\t{before} -> {after}')
    return 1 if differences or index else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['list', 'write', 'verify'])
    parser.add_argument('--cache', default=git_history.CACHE_DIR,
                        help='directory of the clones, or the folder that holds it (verify)')
    parser.add_argument('--base', default='origin/main', help='the commit of the old registers (verify)')
    args = parser.parse_args(argv)
    if args.command == 'list':
        print_inventory(tracked_files())
        return 0
    if args.command == 'write':
        changed = write(tracked_files())
        print(f'{len(changed)} files changed')
        return 0
    return verify(args.cache, args.base)


if __name__ == '__main__':
    sys.exit(main())
