"""Polite, cached fetching of web pages and the Wayback Machine helpers.

Raw downloads go to the gitignored cache only; a page with a cached copy is never fetched again unless
the fetcher is told to refresh. Requests are paced per host, also across fetchers and processes, and
retried when the server or the connection fails.

The cache is the `.cache` directory of the main checkout, so all worktrees of one checkout share it;
the environment variable PLONE_STATS_CACHE names another directory instead.
"""

import contextlib
import dataclasses
import datetime
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
from datetime import timezone

import requests

from scripts.lib.model.sources import archive_url_of, split_archive_url

CACHE_ENV = 'PLONE_STATS_CACHE'
SOURCES_CACHE = 'sources'  # the raw downloads of the sources, below the cache root
USER_AGENT = 'plone-contributor-statistics/1.0 (+https://github.com/plone/plone-contributor-statistics)'
# Hosts paced together: the Internet Archive counts its requests across its hosts
PACE_KEYS = {'web.archive.org': 'archive.org', 'archive.org': 'archive.org'}
# Seconds between two requests to a pace key: at most 15 a minute to the Internet Archive
PACE = {'archive.org': 4.0}
DEFAULT_PACE = 1.0
MAX_RETRIES = 5
CACHED_STATUSES = (200, 404, 410)
RETRY_STATUSES = (429, 500, 502, 503, 504)
CONNECTION_ERRORS = (requests.exceptions.ConnectionError,
                     requests.exceptions.Timeout,
                     requests.exceptions.ChunkedEncodingError)
TIMEOUT = 60


class FetchError(Exception):
    """A page could not be fetched."""


def cache_root(run=subprocess.run):
    """The cache directory: PLONE_STATS_CACHE, else `.cache` in the main checkout, else in the current directory.

    The main checkout is the parent of the common Git directory, which all worktrees of a checkout share.
    Resolved at call time, so a change of the current directory counts.
    """
    override = os.environ.get(CACHE_ENV)
    if override:
        return override
    try:
        result = run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                     capture_output=True, check=True, text=True)
        common = (result.stdout or '').strip()
    except (OSError, subprocess.CalledProcessError):
        common = ''
    if not common:
        return os.path.abspath('.cache')
    return os.path.join(os.path.dirname(common.rstrip('/')), '.cache')


def cache_dir(*parts):
    """A directory below the cache root, such as `cache_dir('sources')`."""
    return os.path.join(cache_root(), *parts)


def pace_key(url):
    host = (urllib.parse.urlsplit(url).hostname or '').lower()
    return PACE_KEYS.get(host, host) or '_'


def _write_atomic(path, data):
    """Write to a temporary file next to the path, then rename it: readers see the old file or the whole new one."""
    handle, temporary = tempfile.mkstemp(dir=os.path.dirname(path) or '.', prefix='.tmp-')
    try:
        with os.fdopen(handle, 'wb') as out:
            out.write(data)
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


@dataclasses.dataclass(frozen=True)
class Raw:
    url: str
    status: int
    content_type: str
    body: bytes
    fetched: datetime.datetime


def now():
    return datetime.datetime.now(timezone.utc)


def raw_capture_url(archive_url):
    """The `id_` form of a Wayback address: the capture as archived, without the toolbar and rewritten links."""
    split = split_archive_url(archive_url)
    if split is None:
        raise ValueError(f'not a Wayback address: {archive_url}')
    original, timestamp = split
    # keep the original exactly as written in the address (a `:80` or a missing scheme matters to the match)
    marker = re.search(r'/web/\d+[a-z_]*/', archive_url)
    written = archive_url[marker.end():] if marker else original
    return f'https://web.archive.org/web/{timestamp}id_/{written}'


class Fetcher:
    """Fetch addresses through a local cache, at the pace the hosts allow."""

    def __init__(self, cache=None, session=None, sleep=None, clock=None, refresh=False):
        self.cache = cache or cache_dir(SOURCES_CACHE)
        self._session = session
        self.sleep = sleep or time.sleep
        # wall-clock time, because the pace files are read by other processes
        self.clock = clock or time.time
        self.refresh = refresh
        self.last_request = {}

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers['User-Agent'] = USER_AGENT
        return self._session

    def _paths(self, url):
        base = os.path.join(self.cache, hashlib.sha1(url.encode()).hexdigest())
        return base + '.body', base + '.json'

    def _cached(self, url):
        """The cached copy, or None; an entry that cannot be read is a miss."""
        body_path, meta_path = self._paths(url)
        if self.refresh or not (os.path.exists(body_path) and os.path.exists(meta_path)):
            return None
        try:
            with open(meta_path, encoding='utf-8') as handle:
                meta = json.load(handle)
            with open(body_path, 'rb') as handle:
                body = handle.read()
            return Raw(meta['url'], meta['status'], meta['content_type'], body,
                       datetime.datetime.fromisoformat(meta['fetched']))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _store(self, raw):
        """Write the body, then the metadata, each by renaming a complete file: a crash leaves a miss, not junk."""
        body_path, meta_path = self._paths(raw.url)
        os.makedirs(self.cache, exist_ok=True)
        _write_atomic(body_path, raw.body)
        meta = {'url': raw.url, 'status': raw.status, 'content_type': raw.content_type,
                'fetched': raw.fetched.isoformat()}
        _write_atomic(meta_path, json.dumps(meta, indent=2).encode('utf-8'))

    def _pace_path(self, key):
        return os.path.join(self.cache, 'pace', key)

    def _last_request(self, key):
        """When the last request for the pace key was sent, by this fetcher or by any other on the same cache."""
        times = [self.last_request[key]] if key in self.last_request else []
        try:
            with open(self._pace_path(key), encoding='ascii') as handle:
                times.append(float(handle.read().strip()))
        except (OSError, ValueError):
            pass
        return max(times, default=None)

    def _mark(self, url):
        key = pace_key(url)
        self.last_request[key] = self.clock()
        path = self._pace_path(key)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _write_atomic(path, repr(self.last_request[key]).encode('ascii'))
        except OSError:
            pass  # the pace of this process still holds

    def _pace(self, url, backoff=0):
        """Wait before a request: the longest of the back-off and what is left of the host's pace."""
        key = pace_key(url)
        pace = PACE.get(key, DEFAULT_PACE)
        last = self._last_request(key)
        wait = backoff
        if last is not None:
            # at most one pace, even when the last time lies in the future after the clock was set back
            wait = max(wait, min(pace, pace - (self.clock() - last)))
        if wait > 0:
            self.sleep(wait)

    def get(self, url):
        cached = self._cached(url)
        if cached is not None:
            return cached
        retry_after = 0
        for attempt in range(MAX_RETRIES):
            self._pace(url, max(2 ** attempt if attempt else 0, retry_after))
            retry_after = 0
            try:
                try:
                    response = self.session.get(url, timeout=TIMEOUT)
                finally:
                    self._mark(url)
            except CONNECTION_ERRORS as error:
                failure = f'{type(error).__name__}: {error}'
            except requests.RequestException as error:
                raise FetchError(f'{url}: {type(error).__name__}: {error}') from error
            else:
                status = response.status_code
                if status in CACHED_STATUSES:
                    raw = Raw(url, status, response.headers.get('Content-Type', ''), response.content, now())
                    self._store(raw)
                    return raw
                if status not in RETRY_STATUSES:
                    raise FetchError(f'{url}: HTTP {status}')
                if status == 429:
                    retry_after = _seconds(response.headers.get('Retry-After'))
                failure = f'HTTP {status}'
        raise FetchError(f'{url}: {failure} after {MAX_RETRIES} attempts')


def _seconds(value):
    """A Retry-After header given in seconds; 0 for a date or anything else."""
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0


def nearest_capture(fetcher, url, timestamp=None):
    """The readable Wayback address of the capture closest to the timestamp, or None.

    None also for an answer that is not the expected JSON, such as an error page sent with status 200.
    """
    query = {'url': url}
    if timestamp:
        query['timestamp'] = timestamp
    raw = fetcher.get('https://archive.org/wayback/available?' + urllib.parse.urlencode(query))
    if raw.status != 200:
        return None
    try:
        answer = json.loads(raw.body)
    except ValueError:
        return None
    snapshots = answer.get('archived_snapshots') if isinstance(answer, dict) else None
    closest = snapshots.get('closest') if isinstance(snapshots, dict) else None
    if not isinstance(closest, dict) or not closest.get('available'):
        return None
    split = split_archive_url(str(closest.get('url', '')))
    if split is None:
        return None
    return archive_url_of(*split)
