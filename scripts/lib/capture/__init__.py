"""Capture a source once: its row in the source register and the passages around the quotes that cite it.

The page is fetched once through the local cache and read with the adapter for its address; only the paragraph
around each quote is stored, through the model, never the whole page.
"""

import dataclasses
import datetime
import os
import subprocess
import urllib.parse
from collections.abc import Sequence

import requests

from scripts.lib.capture import extract as extraction  # the module: a name `extract` here would hide it
from scripts.lib.capture import fetch
from scripts.lib.capture.extract import (
    COMMIT_PATH,
    ExtractError,
    adapter_for,
    extract_commit,
    extract_github_profile,
    extract_video,
    extract_volto,
    is_pdf,
)
from scripts.lib.capture.fetch import FetchError, Fetcher, nearest_capture, raw_capture_url
from scripts.lib.capture.passages import cut_passage, find_quote
from scripts.lib.github_api import GitHubAPIError
from scripts.lib.model import (
    Source,
    add_passage,
    archive_url_of,
    load_sources,
    passages,
    source_id,
    split_archive_url,
    write_source,
)

KIND_BY_ADAPTER = {'github-profile': 'profile', 'commit': 'commit', 'video': 'video'}
GONE_STATUSES = (404, 410)


class CaptureError(Exception):
    """A source could not be captured; nothing was written."""


@dataclasses.dataclass(frozen=True)
class CaptureResult:
    source_id: str
    created: bool
    added: tuple[str, ...]
    missing: tuple[str, ...]
    unreachable: bool


class GitHubSession:
    """A GitHub API session built on first use from the GITHUB_TOKEN environment variable."""

    def __init__(self):
        self._session = None

    @property
    def session(self):
        if self._session is None:
            token = os.environ.get('GITHUB_TOKEN')
            if not token:
                raise CaptureError('this source is read through the GitHub API: set GITHUB_TOKEN')
            self._session = requests.Session()
            self._session.headers.update({'Authorization': f'token {token}',
                                          'Accept': 'application/vnd.github+json',
                                          'User-Agent': fetch.USER_AGENT})
        return self._session

    def get(self, url, **kwargs):
        return self.session.get(url, **kwargs)


def github_session():
    return GitHubSession()


@dataclasses.dataclass(frozen=True)
class _Read:
    """What was read: the address of the source, the copy read, and the text."""
    original: str
    timestamp: str | None
    kind: str
    text: str
    full_text: str
    title: str | None
    date: datetime.date | None
    fetched: datetime.datetime


class _Gone(Exception):
    """The live address answers that the page is gone."""

    def __init__(self, fetched, kind):
        super().__init__('gone')
        self.fetched = fetched
        self.kind = kind


def _is_gone(error):
    """True for a GitHub API answer that the user or commit does not exist, also when wrapped by the adapter."""
    while error is not None:
        if isinstance(error, GitHubAPIError):
            return any(f'HTTP {status}' in str(error) for status in GONE_STATUSES)
        error = error.__cause__
    return False


def _timestamp_date(timestamp):
    return datetime.date(int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]))


def _read_archive(fetcher, archive_url, kind, run):
    original, timestamp = split_archive_url(archive_url)
    raw = fetcher.get(raw_capture_url(archive_url))
    if raw.status in GONE_STATUSES:
        raise _Gone(raw.fetched, kind or ('pdf' if is_pdf(raw) else 'page'))
    extracted = extraction.extract(raw, run=run)
    return _Read(original, timestamp, kind or ('pdf' if is_pdf(raw) else 'page'), extracted.text,
                 extracted.full_text, extracted.title, extracted.date, raw.fetched)


def _read_live(url, sid, fetcher, session, run):
    """Read a live address with its adapter; raises _Gone when the page is gone."""
    adapter = adapter_for(url)
    kind = KIND_BY_ADAPTER.get(adapter)
    if adapter in ('generic', 'volto'):
        raw = fetcher.get(url)
        if raw.status in GONE_STATUSES:
            raise _Gone(raw.fetched, 'pdf' if is_pdf(raw) else 'page')
        extracted = extract_volto(fetcher, url) if adapter == 'volto' else extraction.extract(raw, run=run)
        return _Read(url, None, 'pdf' if is_pdf(raw) else 'page', extracted.text, extracted.full_text,
                     extracted.title, extracted.date, raw.fetched)
    fetched = fetch.now()
    try:
        if adapter == 'github-profile':
            login = [segment for segment in urllib.parse.urlsplit(url).path.split('/') if segment][0]
            extracted = extract_github_profile(login, session)
        elif adapter == 'commit':
            owner, repo, sha = COMMIT_PATH.match(urllib.parse.urlsplit(url).path).groups()
            extracted = extract_commit(owner, repo, sha, run=run, session=session)
        else:
            extracted = extract_video(url, os.path.join(fetch.CACHE_DIR, 'video', sid), run=run)
    except (GitHubAPIError, ExtractError) as error:
        if _is_gone(error):
            raise _Gone(fetched, kind) from error
        raise
    return _Read(url, None, kind, extracted.text, extracted.full_text, extracted.title, extracted.date, fetched)


def _stored(sid, quote):
    return any(find_quote(passage, quote) for passage in passages(sid))


def _source(existing, sid, read, kind, title, date, notes, refresh):
    """The row to write, or None when the existing row stays as it is."""
    archive_url = archive_url_of(read.original, read.timestamp) if read.timestamp else None
    if existing is not None:
        return dataclasses.replace(existing, fetched=read.fetched) if refresh else None
    return Source(
        id=sid,
        kind=kind or read.kind,
        title=title or read.title or read.original,
        date=date or read.date or (_timestamp_date(read.timestamp) if read.timestamp else read.fetched.date()),
        url=read.original,
        archive_url=archive_url,
        fetched=read.fetched,
        notes=notes,
    )


def capture(url: str, quotes: Sequence[str] = (), kind: str | None = None, title: str | None = None,
            date: datetime.date | None = None, refresh: bool = False, fetcher: Fetcher | None = None,
            session=None, run=subprocess.run) -> CaptureResult:
    """Capture the source at the address: write its row if new and add the passages around the quotes.

    A Wayback address is stored readable and fetched raw. A live address that is gone is replaced by its
    nearest Wayback capture; without one the source is recorded as unreachable. Quotes that are already in a
    stored passage are skipped; quotes not found on the page are reported as missing, never stored.
    A fetcher given here keeps its own refresh setting; one built here refetches when refresh is true.
    """
    quotes = tuple(quotes)
    split = split_archive_url(url)
    original, timestamp = split if split else (url, None)
    sid = source_id(original, timestamp)
    sources = load_sources()
    if sid in sources and not refresh and all(_stored(sid, quote) for quote in quotes):
        return CaptureResult(sid, False, (), (), False)

    fetcher = fetcher or Fetcher(refresh=refresh)
    session = session or github_session()
    try:
        try:
            if split:
                read = _read_archive(fetcher, url, None, run)
            else:
                read = _read_live(url, sid, fetcher, session, run)
        except _Gone as gone:
            nearest = None if split else nearest_capture(fetcher, url)
            if nearest is None:
                return _unreachable(sources.get(sid), sid, original, timestamp, gone, quotes, kind, title, date)
            read = _read_archive(fetcher, nearest, KIND_BY_ADAPTER.get(adapter_for(url)), run)
    except _Gone as gone:  # the nearest capture is gone as well
        return _unreachable(sources.get(sid), sid, original, timestamp, gone, quotes, kind, title, date)
    except (FetchError, ExtractError, GitHubAPIError) as error:
        raise CaptureError(f'{url}: {error}') from error

    sid = source_id(read.original, read.timestamp)
    existing = sources.get(sid)
    row = _source(existing, sid, read, kind, title, date, None, refresh)
    if row is not None:
        write_source(row)
    added, missing = [], []
    for quote in quotes:
        if _stored(sid, quote):
            continue
        for text in (read.text, read.full_text):
            span = find_quote(text, quote)
            if span is not None:
                passage = cut_passage(text, span)
                if add_passage(sid, passage):
                    added.append(passage)
                break
        else:
            missing.append(quote)
    return CaptureResult(sid, existing is None, tuple(added), tuple(missing), False)


def _unreachable(existing, sid, original, timestamp, gone, quotes, kind, title, date):
    """Record a source that could not be fetched; an existing row and its passages stay untouched."""
    missing = tuple(quote for quote in quotes if not _stored(sid, quote))
    if existing is None:
        note = f'could not be fetched on {gone.fetched.date().isoformat()}'
        read = _Read(original, timestamp, gone.kind or 'page', '', '', None, None, gone.fetched)
        write_source(_source(None, sid, read, kind, title, date, note, False))
        add_passage(sid, note)
    return CaptureResult(sid, existing is None, (), missing, True)
