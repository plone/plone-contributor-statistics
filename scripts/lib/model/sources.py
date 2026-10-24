"""The register of sources: the pages, profiles, commits and videos that the other registers cite."""

import contextlib
import csv
import hashlib
import io
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.schema import read_rows

SOURCE_KINDS = ('page', 'speaker-page', 'profile', 'commit', 'video', 'pdf', 'register', 'issue-comment', 'decision')

_ARCHIVE = re.compile(r'^https?://web\.archive\.org/web/(\d{14})(?:[a-z]{2}_)?/(.+)$', re.IGNORECASE)
_SCHEME = re.compile(r'^https?://', re.IGNORECASE)
_COMMENT_FRAGMENT = re.compile(r'^(issuecomment-\d+|discussion_r\d+|pullrequestreview-\d+)$')
GOOGLE_DOC_PATH = re.compile(r'^/document/d/([^/?#]+)')
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


UNCAPTURED_MARKERS = ('not captured on', 'could not be fetched on')
"""How the notes of a source that was never read start, and so does the only passage of its excerpt."""


def is_uncaptured(source):
    """Whether the source was never read: recorded by the migration without a capture (`not captured on …`)
    or by a capture that could not fetch it (`could not be fetched on …`)."""
    return (source.notes or '').startswith(UNCAPTURED_MARKERS)


def normalize_url(url):
    """The key of a web address: no scheme, lower-case host, no default port, no fragment, no trailing slash.

    The query stays, because pages that differ in their query differ in their content. So does the fragment
    of a GitHub comment, review or review comment: it names a different text on the same page.
    A Google Doc is its id alone: `/edit`, `?usp=sharing` and the like are the same document.
    """
    url, _, fragment = _SCHEME.sub('', url.strip()).partition('#')
    rest = url.find('/')
    query = url.find('?')
    ends = [i for i in (rest, query) if i >= 0]
    cut = min(ends) if ends else len(url)
    host, tail = url[:cut].lower(), url[cut:]
    host = _DEFAULT_PORT.sub('', host)
    path, _, query = tail.partition('?')
    path = path.rstrip('/')
    doc = GOOGLE_DOC_PATH.match(path) if host == 'docs.google.com' else None
    if doc:
        return f'{host}/document/d/{doc.group(1)}'
    keep = f'#{fragment}' if host in ('github.com', 'www.github.com') and _COMMENT_FRAGMENT.match(fragment) else ''
    return host + path + (f'?{query}' if query else '') + keep


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


_MEMO = {}  # resolved path -> ((st_mtime_ns, st_size), register)


def _stamp(path):
    stat = Path(path).stat()
    return stat.st_mtime_ns, stat.st_size


def load_sources(path=None):
    """The register, by id. Raises FileNotFoundError without the file.

    Kept in memory while the file is unchanged (same path, modification time and size), so a run of thousands
    of captures reads it once; each call gets its own dict.
    """
    path = path or paths.SOURCES
    stamp = _stamp(path)  # raises FileNotFoundError
    key = str(Path(path).resolve())
    memo = _MEMO.get(key)
    if memo is None or memo[0] != stamp:
        rows = read_rows(path)
        register = {row['id']: Source(row['id'], row['kind'], row['title'], row['date'], row['url'],
                                      row['archive_url'], row['fetched'], row['notes'])
                    for row in rows}
        memo = _MEMO[key] = (stamp, register)
    return dict(memo[1])


def excerpt_path(source_id):
    """The file that holds the passages cited from the source."""
    return Path(paths.EXCERPTS_DIR) / f'{source_id}.md'


def _write_atomic(path, text):
    """Write to a temporary file next to the path, then rename it: readers see the old file or the whole new one.

    The new file keeps the permissions of the old one (a temporary file is private to its owner).
    """
    path = Path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.tmp-')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='') as out:
            out.write(text)
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644)
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


PASSAGE_SEPARATOR = '\n\n---\n\n'
SOURCE_FIELDS = ('id', 'kind', 'title', 'date', 'url', 'archive_url', 'fetched', 'notes')


def write_source(source):
    """Add the source to sources.csv or replace the row with its id; the file stays sorted by id."""
    try:
        existing = load_sources()
    except FileNotFoundError:
        existing = {}
    existing[source.id] = source
    rows = []
    for item in sorted(existing.values(), key=lambda item: item.id):
        fetched = item.fetched.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        rows.append({'id': item.id, 'kind': item.kind, 'title': item.title, 'date': item.date.isoformat(),
                     'url': item.url, 'archive_url': item.archive_url or '', 'fetched': fetched,
                     'notes': item.notes or ''})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SOURCE_FIELDS, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    _write_atomic(paths.SOURCES, buffer.getvalue())
    _MEMO[str(Path(paths.SOURCES).resolve())] = (_stamp(paths.SOURCES), dict(sorted(existing.items())))


def read_excerpt(source_id):
    """The text of the excerpt file of the source; empty without the file."""
    path = excerpt_path(source_id)
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def passages(source_id):
    """The passages cited from the source."""
    text = read_excerpt(source_id).strip()
    return text.split(PASSAGE_SEPARATOR) if text else []


def _collapse(text):
    return ' '.join(text.split())


def replace_excerpt(source_id, text):
    """Replace the whole excerpt of the source by the text (passages joined by PASSAGE_SEPARATOR), atomically."""
    path = excerpt_path(source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, text.strip() + '\n')


def add_passage(source_id, passage):
    """Append the passage unless one of the passages contains it already, ignoring whitespace; True if added."""
    passage = passage.strip()
    wanted = _collapse(passage)
    existing = passages(source_id)
    if any(wanted in _collapse(other) for other in existing):
        return False
    path = excerpt_path(source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, PASSAGE_SEPARATOR.join([*existing, passage]) + '\n')
    return True
