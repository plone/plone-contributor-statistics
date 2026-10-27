"""Mask mail addresses: a hash replaces the readable address, see docs/explanation/attribution.md.

The bare form `h-<16 hex>` is the default. The form with the domain, `h-<16 hex>@<company domain>`, is only for
excerpts and snippets, which quote text where the domain is the evidence. The `notes` of the curated mappings
name the domain of a company address in words, `h-<16 hex> (an address at <domain>)`.
"""
import hashlib
import re

from scripts.lib.changelogs import SVN_DOMAIN
from scripts.lib import commit_authors  # used at call time: commit_authors imports the model, which imports this

PREFIX = 'h-'
MASKED = re.compile(r'h-[0-9a-f]{16}')
_MASKED_VALUE = re.compile(r'(?P<bare>h-[0-9a-f]{16})(?:@(?P<domain>[^@\s]+))?')

# An address in free text: not part of a path, a scoped package or a longer word; the last label of the domain
# has letters only (react@18.2.0 is a version). A lower-case last label ends before a capitalised word glued to it,
# as in a page that lost its spaces ("jane@acme.testPlone Conf"). Underscores around an address are Markdown
# emphasis ("_jane@acme.test_"), not part of it
ADDRESS = re.compile(r'(?<![A-Za-z0-9.+\-/@])[A-Za-z0-9.+\-][\w.+\-]*@(?:[A-Za-z0-9\-]+\.)+'
                     r'(?:[a-z]{2,}(?=[A-Z][a-z])|[A-Za-z]{2,}(?![A-Za-z0-9\-]))')

# A masked value that keeps its company domain, the form of excerpts and snippets
MASKED_WITH_DOMAIN = re.compile(r'\bh-[0-9a-f]{16}@')

# Domains that cannot be a person's: reserved for tests and documentation
_RESERVED_DOMAIN = re.compile(r'(?:\.(?:test|example|invalid|localhost)|(?:^|\.)example\.(?:com|org|net))$')

# Addresses that are not a person's and stay readable, each with its reason
NOT_PERSONAL = {
    'git@github.com': 'the SSH address of GitHub repositories',
    'noreply@github.com': "GitHub's sender address",
    'noreply@anthropic.com': "Anthropic's sender address, in the Co-Authored-By trailers of commits by Claude",
    'releasemanager@plone.org': "the Plone Foundation's role address of the release manager, the maintainer of "
                                'its npm packages',
    'plonesymp@plone.jp': 'the address of the organising committee of the Plone Symposium Tokyo',
    'eea-jenkins-npm@roles.eea.eionet.europa.eu': "the npm account of the build server (Jenkins) of the European "
                                                  'Environment Agency',
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
    if cleaned.lower() in NOT_PERSONAL or commit_authors.NOREPLY.match(cleaned) or SVN_DOMAIN.match(domain):
        return address
    hashed = address_hash(cleaned)
    if keep_domain and commit_authors.is_company_domain(domain):
        return hashed + '@' + domain
    return hashed


def mask_address_for_notes(address):
    """Mask an address as the `notes` of the curated mappings give it: a company address is the hash, then its
    domain in words, `h-<16 hex> (an address at <domain>)`; any other address as `mask_address` masks it."""
    masked = mask_address(address, keep_domain=True)
    match = _MASKED_VALUE.fullmatch(masked)
    if match and match.group('domain'):
        return f"{match.group('bare')} (an address at {match.group('domain')})"
    return masked


def mask_text(text, keep_domain=False):
    """Mask every address in free text."""
    return ADDRESS.sub(lambda m: mask_address(m.group(0), keep_domain), text)


def readable_addresses(text):
    """The addresses in the text that masking would change: raw addresses, not masked ones with a domain.

    An address in a reserved domain (`.test`, `.example`, `.invalid`, `.localhost`, example.com, .org, .net) is
    not readable: it belongs to nobody."""
    found = []
    for match in ADDRESS.finditer(text):
        address = match.group(0)
        if _RESERVED_DOMAIN.search(address.rsplit('@', 1)[1].lower()):
            continue
        if mask_address(address, keep_domain=True) != address:
            found.append(address)
    return found
