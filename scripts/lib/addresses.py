"""Mask mail addresses: a hash replaces the readable address, see docs/explanation/attribution.md.

The bare form `h-<16 hex>` is the default. The form with the domain, `h-<16 hex>@<company domain>`, is only for
excerpts and snippets, which quote text where the domain is the evidence.
"""
import hashlib
import re

from scripts.lib.changelogs import SVN_DOMAIN
from scripts.lib.commit_authors import NOREPLY, is_company_domain

PREFIX = 'h-'
MASKED = re.compile(r'h-[0-9a-f]{16}')
_MASKED_VALUE = re.compile(r'(?P<bare>h-[0-9a-f]{16})(?:@(?P<domain>[^@\s]+))?')

# An address in free text: not part of a path, a scoped package or a longer word; the last label of the domain
# has letters only (react@18.2.0 is a version)
ADDRESS = re.compile(r'(?<![\w.+\-/@])[\w.+\-]+@(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}(?![\w\-])')

# Addresses that are not a person's and stay readable, each with its reason
NOT_PERSONAL = {
    'git@github.com': 'the SSH address of GitHub repositories',
    'noreply@github.com': "GitHub's sender address",
}


def address_hash(address):
    """The masked form of an address: `h-` and 16 hex characters of SHA-256 over the normalised address."""
    normalised = address.strip().strip('<>').strip().lower()
    return PREFIX + hashlib.sha256(normalised.encode('utf-8')).hexdigest()[:16]


def is_masked(value):
    """Whether the value is `h-<16 hex>`, with or without `@domain`."""
    return bool(_MASKED_VALUE.fullmatch(value.strip()))


def mask_address(address, keep_domain=False):
    """Mask an address; masked values, Subversion, noreply and not personal addresses stay as they are."""
    match = _MASKED_VALUE.fullmatch(address.strip())
    if match:
        if keep_domain and match.group('domain'):
            return match.group('bare') + '@' + match.group('domain').lower()
        return match.group('bare')
    cleaned = address.strip().strip('<>').strip()
    if '@' not in cleaned:
        return address
    domain = cleaned.rsplit('@', 1)[1].lower()
    if cleaned.lower() in NOT_PERSONAL or NOREPLY.match(cleaned) or SVN_DOMAIN.match(domain):
        return address
    hashed = address_hash(cleaned)
    if keep_domain and is_company_domain(domain):
        return hashed + '@' + domain
    return hashed


def mask_text(text, keep_domain=False):
    """Mask every address in free text."""
    return ADDRESS.sub(lambda m: mask_address(m.group(0), keep_domain), text)
