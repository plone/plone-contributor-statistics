"""Find the person behind a commit author, and the mail domain of an address.

Shared by the tools and collectors that read the authors of commits in the cached clones.
"""

import re

from scripts.lib.changelogs import SVN_DOMAIN
from scripts.lib.model.names import fold

NOREPLY = re.compile(r'^(?:\d+\+)?(?P<login>[^@]+)@users\.noreply\.github\.com$', re.IGNORECASE)

# Domains that say nothing about an employer, see the attribution rules. A "*" stands for any top-level domain
# or part of the name: yahoo.* is yahoo.com and yahoo.co.uk. Subdomains count as well (lists.plone.org).
PERSONAL_DOMAINS = [
    'gmail.com', 'googlemail.com', 'yahoo.*', 'hotmail.*', 'outlook.*', 'live.*', 'msn.com', 'aol.com', 'gmx.*',
    'web.de', 'posteo.*', 'mailbox.org', 'protonmail.*', 'fastmail.*', 'me.com', 'mac.com', 'icloud.com',
    'free.fr', 'wanadoo.fr', 'laposte.net', 'users.noreply.github.com', 'localhost', 'localhost.localdomain',
    'plone.org', 'zope.org',
    # Mail services of internet providers: a mailbox there says nothing about an employer either
    'arcor.de', 't-online.de', 'freenet.de', 'aon.at', 'chello.at', 'bluewin.ch', 'orange.fr', 'libero.it',
    'tiscali.*', 'mail.ru', 'yandex.*',
    # Mail aliases that professional societies give their members
    'computer.org', 'acm.org', 'ieee.org',
    # Addresses of other projects and of the Finnish members' mail service
    'gnome.org', 'apache.org', 'debian.org', 'kde.org', 'iki.fi',
    # The BlueDynamics Alliance is a network of companies, each of them the employer, not the alliance
    'bluedynamics.com',
]
_PERSONAL = re.compile(
    r'^(?:.+\.)?(?:' + '|'.join(re.escape(d).replace(r'\*', '.+') for d in PERSONAL_DOMAINS) + ')$')


# The names of machines in a local network, which git takes when nobody set an address, and the domains reserved
# for examples (RFC 2606): no public mail domain, and some of them carry a person's name (katjas-imac.local)
LOCAL_ENDINGS = ('.local', '.lan', '.home', '.localdomain', '.fritz.box', '.in-addr.arpa', '.example')
_EXAMPLE = re.compile(r'^(?:.+\.)?example\.(?:com|org|net)$')


def is_local_name(domain):
    """Whether the domain is the name of a machine or a placeholder: no dot, a local ending, `(none)`, example.com."""
    domain = domain.lower().strip().rstrip('.')
    return ('.' not in domain or '(none)' in domain or domain.endswith(LOCAL_ENDINGS)
            or bool(_EXAMPLE.match(domain)))


def is_company_domain(domain):
    """Whether the domain may name an employer: not personal, not a local name, not Subversion-era."""
    domain = domain.lower().strip()
    return not (not domain or is_local_name(domain) or _PERSONAL.match(domain) or SVN_DOMAIN.match(domain))


MIN_NAME_PART = 4  # a name part shorter than this inside a domain label is no evidence that the domain is own
# Second-level labels under a two-letter country domain: foo.com.au, foo.co.uk, foo.ac.at
_SECOND_LEVEL = {'com', 'co', 'org', 'net', 'ac', 'gov', 'edu', 'or', 'ne', 'go', 'ltd', 'plc'}


def registrable_label(domain):
    """The label that the owner of the domain chose: `foo` in foo.com, foo.com.au and mail.foo.co.uk."""
    labels = domain.lower().strip().split('.')
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return labels[-3]
    return labels[-2] if len(labels) >= 2 else labels[0]


def is_own_domain_for(domain, name, logins=()):
    """Whether the domain looks like the person's own, which says nothing about an employer.

    Its registrable label equals one of the GitHub logins or a whole part of the folded name, or contains a
    part of at least four letters (`leeb` in andersonleeb.com). Use it only for a domain that no organisation
    claims: a registered organisation always wins, so the company of a self-employed person is never lost.
    """
    label = fold(registrable_label(domain)).replace(' ', '')
    parts = fold(name or '').split()
    folded_logins = {fold(login).replace(' ', '') for login in logins if login}
    return bool(label) and (label in folded_logins or label in parts
                            or any(len(part) >= MIN_NAME_PART and part in label for part in parts))


class Finder:
    """The person behind the author of a commit, and whether the author is a bot."""

    def __init__(self, registry, bots):
        self.registry = registry
        self.bots = {bot.casefold() for bot in bots}
        self._cache = {}

    def person(self, email, name):
        """The person, or None when the author is a bot or matches nobody. Noreply login, address, then name."""
        key = (email.lower(), name)
        if key not in self._cache:
            self._cache[key] = self._find(email, name)
        return self._cache[key]

    def _is_bot(self, login):
        return login.endswith('[bot]') or login.casefold() in self.bots

    def _find(self, email, name):
        found = NOREPLY.match(email)
        if found:
            login = found.group('login')
            if self._is_bot(login):
                return None
            person = self.registry.person_for(login=login)
            if person:
                return person
        if self._is_bot(name.strip()):
            return None
        return self.registry.person_for(email=email) or self.registry.person_for(name=name)


def domain_of(email):
    """The mail domain of an address: lower case, without trailing dots.

    None for an address without `@`, for the Subversion-era domains (a repository UUID, localhost and
    `users.sourceforge.net`, see `SVN_DOMAIN`) and for the names of machines and placeholders (`is_local_name`:
    pepper.local, rudolf.(none), example.com): those say nothing about an employer, and some of them carry a
    person's name. GitHub noreply addresses give `users.noreply.github.com`.
    """
    if '@' not in email:
        return None
    domain = email.rsplit('@', 1)[1].strip().lower().rstrip('.')
    if not domain or SVN_DOMAIN.match(domain) or is_local_name(domain):
        return None
    return domain
