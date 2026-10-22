"""Polite, cached fetching of web pages and the Wayback Machine helpers.

Raw downloads go to the gitignored cache only; a page with a cached copy is never fetched again unless
the fetcher is told to refresh. Requests are paced per host and retried when the server or the
connection fails.
"""

import dataclasses
import datetime
import hashlib
import json
import os
import re
import time
import urllib.parse
from datetime import timezone

import requests

from scripts.lib.model.sources import archive_url_of, split_archive_url

CACHE_DIR = os.path.join('.cache', 'sources')
USER_AGENT = 'plone-contributor-statistics/1.0 (+https://github.com/plone/plone-contributor-statistics)'
# Seconds between two requests to a host: at most 15 a minute to the Internet Archive
PACE = {'web.archive.org': 4.0, 'archive.org': 4.0}
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

    def __init__(self, cache=CACHE_DIR, session=None, sleep=None, clock=None, refresh=False):
        self.cache = cache
        self._session = session
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
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
        body_path, meta_path = self._paths(url)
        if self.refresh or not (os.path.exists(body_path) and os.path.exists(meta_path)):
            return None
        with open(meta_path, encoding='utf-8') as handle:
            meta = json.load(handle)
        with open(body_path, 'rb') as handle:
            body = handle.read()
        return Raw(meta['url'], meta['status'], meta['content_type'], body,
                   datetime.datetime.fromisoformat(meta['fetched']))

    def _store(self, raw):
        body_path, meta_path = self._paths(raw.url)
        os.makedirs(self.cache, exist_ok=True)
        with open(body_path, 'wb') as handle:
            handle.write(raw.body)
        meta = {'url': raw.url, 'status': raw.status, 'content_type': raw.content_type,
                'fetched': raw.fetched.isoformat()}
        with open(meta_path, 'w', encoding='utf-8') as handle:
            json.dump(meta, handle, indent=2)

    def _pace(self, url):
        host = urllib.parse.urlsplit(url).hostname or ''
        last = self.last_request.get(host)
        if last is not None:
            wait = PACE.get(host, DEFAULT_PACE) - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        self.last_request[host] = self.clock()

    def get(self, url):
        cached = self._cached(url)
        if cached is not None:
            return cached
        self._pace(url)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=TIMEOUT)
            except CONNECTION_ERRORS as error:
                failure = f'{type(error).__name__}: {error}'
            else:
                status = response.status_code
                if status in CACHED_STATUSES:
                    raw = Raw(url, status, response.headers.get('Content-Type', ''), response.content, now())
                    self._store(raw)
                    return raw
                if status not in RETRY_STATUSES:
                    raise FetchError(f'{url}: HTTP {status}')
                failure = f'HTTP {status}'
            if attempt == MAX_RETRIES:
                raise FetchError(f'{url}: {failure} after {MAX_RETRIES} attempts')
            self.sleep(2 ** attempt)


def nearest_capture(fetcher, url, timestamp=None):
    """The readable Wayback address of the capture closest to the timestamp, or None."""
    query = {'url': url}
    if timestamp:
        query['timestamp'] = timestamp
    raw = fetcher.get('https://archive.org/wayback/available?' + urllib.parse.urlencode(query))
    if raw.status != 200:
        return None
    closest = json.loads(raw.body).get('archived_snapshots', {}).get('closest')
    if not closest or not closest.get('available'):
        return None
    return archive_url_of(split_archive_url(closest['url'])[0], closest['timestamp'])
