"""The register of sources: the pages, profiles, commits and videos that the other registers cite."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.schema import read_rows

SOURCE_KINDS = ('page', 'speaker-page', 'profile', 'commit', 'video', 'pdf', 'register', 'issue-comment', 'decision')

_ARCHIVE = re.compile(r'^https?://web\.archive\.org/web/(\d{14})(?:[a-z]{2}_)?/(.+)$', re.IGNORECASE)
_SCHEME = re.compile(r'^https?://', re.IGNORECASE)
_DEFAULT_PORT = re.compile(r':(?:80|443)(?=/|\?|$)')


@dataclass(frozen=True)
class Source:
    id: str
    kind: str
    title: str
    date: date
    url: str
    archive_url: str | None
    fetched: datetime
    notes: str | None


def normalize_url(url):
    """The key of a web address: no scheme, lower-case host, no default port, no fragment, no trailing slash.

    The query stays, because pages that differ in their query differ in their content.
    """
    url = _SCHEME.sub('', url.strip()).split('#', 1)[0]
    rest = url.find('/')
    query = url.find('?')
    ends = [i for i in (rest, query) if i >= 0]
    cut = min(ends) if ends else len(url)
    host, tail = url[:cut].lower(), url[cut:]
    host = _DEFAULT_PORT.sub('', host)
    path, _, query = tail.partition('?')
    path = path.rstrip('/')
    return host + path + (f'?{query}' if query else '')


def split_archive_url(url):
    """(original address, timestamp) of a Wayback Machine address in any form, else None."""
    match = _ARCHIVE.match(url.strip())
    if not match:
        return None
    timestamp, original = match.groups()
    if not _SCHEME.match(original):
        original = f'http://{original}'
    return original, timestamp


def archive_url_of(original, timestamp):
    """The readable Wayback address of the copy of the original taken at the timestamp."""
    return f'https://web.archive.org/web/{timestamp}/{original}'


def source_id(url, timestamp=None):
    """The twelve-character id of a source; an archived copy and the live page are different sources."""
    return hashlib.sha1(f'{normalize_url(url)} {timestamp or ""}'.encode()).hexdigest()[:12]


def load_sources(path=None):
    """The register, by id. Raises FileNotFoundError without the file."""
    rows = read_rows(path or paths.SOURCES)
    return {row['id']: Source(row['id'], row['kind'], row['title'], row['date'], row['url'], row['archive_url'],
                              row['fetched'], row['notes'])
            for row in rows}


def excerpt_path(source_id):
    """The file that holds the passages cited from the source."""
    return Path(paths.EXCERPTS_DIR) / f'{source_id}.md'
