"""Find the person behind a commit author, and the mail domain of an address.

Shared by the tools and collectors that read the authors of commits in the cached clones.
"""

import re

from scripts.lib.changelogs import SVN_DOMAIN

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


def is_company_domain(domain):
    """Whether the domain may name an employer: not personal, not a local name, not Subversion-era."""
    domain = domain.lower().strip()
    return not (not domain or '.' not in domain or domain.endswith(('.local', '.lan', '(none)'))
                or _PERSONAL.match(domain) or SVN_DOMAIN.match(domain))


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

    None for an address without `@`, for a Subversion-UUID domain and for localhost: those say nothing.
    GitHub noreply addresses give `users.noreply.github.com`.
    """
    if '@' not in email:
        return None
    domain = email.rsplit('@', 1)[1].strip().lower().rstrip('.')
    if not domain or SVN_DOMAIN.match(domain):
        return None
    return domain
