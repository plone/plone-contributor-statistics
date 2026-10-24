"""Capture a source once: its row in the source register and the passages around the quotes that cite it.

The page is fetched once through the local cache and read with the adapter for its address; only the paragraph
around each quote is stored, through the model, never the whole page.
"""

import dataclasses
import datetime
import os
import re
import subprocess
import urllib.parse
from collections.abc import Sequence

import requests

from scripts.lib.capture import extract as extraction  # the module: a name `extract` here would hide it
from scripts.lib.capture import fetch
from scripts.lib.capture.extract import (
    COMMIT_PATH,
    ISSUE_PATH,
    ExtractError,
    adapter_for,
    extract_commit,
    extract_github_issue,
    extract_github_profile,
    extract_google_doc,
    extract_video,
    extract_volto,
    google_doc_id,
    is_pdf,
    video_folder,
)
from scripts.lib.capture.fetch import FetchError, Fetcher, nearest_capture, raw_capture_url
from scripts.lib.capture.passages import cut_passage, find_name, find_quote
from scripts.lib.github_api import GitHubAPIError
from scripts.lib.model import (
    PASSAGE_SEPARATOR,
    Source,
    add_passage,
    archive_url_of,
    is_uncaptured,
    load_sources,
    normalize_url,
    passages,
    read_excerpt,
    replace_excerpt,
    source_id,
    split_archive_url,
    write_source,
)
from scripts.lib.model.sources import UNCAPTURED_MARKERS

KIND_BY_ADAPTER = {'github-profile': 'profile', 'github-issue': 'issue-comment', 'commit': 'commit', 'video': 'video',
                   'google-doc': 'page'}
WHOLE_TEXT_KINDS = ('profile', 'commit')
GENERIC_KIND = 'page'  # what a read knows of a web page that no adapter reads more specifically
OWN_REPOSITORY = 'plone/plone-contributor-statistics'  # its issues and comments are our own public record
# a block of an issue page starts after a blank line with its optional title and its author and date lines
BLOCK_START = re.compile(r'\n\n(?=(?:Title: [^\n]*\n)?Author: [^\n]*\nDate: )')
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
    notes: str | None = None


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


def _is_wayback(url):
    parts = urllib.parse.urlsplit(url.strip())
    return (parts.hostname or '').lower() == 'web.archive.org' and parts.path.startswith('/web/')


def _timestamp_date(timestamp):
    return datetime.date(int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]))


def _read_archive(fetcher, archive_url, kind, run):
    original, timestamp = split_archive_url(archive_url)
    raw = fetcher.get(raw_capture_url(archive_url))
    if raw.status in GONE_STATUSES:
        raise _Gone(raw.fetched, kind or ('pdf' if is_pdf(raw) else 'page'))
    served = split_archive_url(raw.final_url)
    notes = None
    if served is not None:
        if served[1] != timestamp:  # the Archive sent us to another capture: record that one
            timestamp = served[1]
        if normalize_url(served[0]) != normalize_url(original):  # a capture of another page: keep the address asked
            notes = f'served {archive_url_of(served[0], served[1])}'
    extracted = extraction.extract(raw, run=run)
    return _Read(original, timestamp, kind or ('pdf' if is_pdf(raw) else 'page'), extracted.text,
                 extracted.full_text, extracted.title, extracted.date, raw.fetched, notes)


def _read_live(url, fetcher, session, run, refresh=False):
    """Read a live address with its adapter; raises _Gone when the page is gone.

    A video is read from the tracks kept in its cache folder, one per video, unless `refresh`.
    """
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
        if adapter == 'google-doc':
            extracted = extract_google_doc(fetcher, google_doc_id(url))
        elif adapter == 'github-profile':
            login = [segment for segment in urllib.parse.urlsplit(url).path.split('/') if segment][0]
            extracted = extract_github_profile(login, session)
        elif adapter == 'github-issue':
            parts = urllib.parse.urlsplit(url)
            owner, repo, number = ISSUE_PATH.match(parts.path).groups()
            extracted = extract_github_issue(owner, repo, number, parts.fragment, session)
        elif adapter == 'commit':
            owner, repo, sha = COMMIT_PATH.match(urllib.parse.urlsplit(url).path).groups()
            extracted = extract_commit(owner, repo, sha, run=run, session=session)
        else:
            extracted = extract_video(url, fetch.cache_dir(fetch.SOURCES_CACHE, 'video', video_folder(url)), run=run,
                                      fetcher=fetcher, refresh=refresh)
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
    if read.timestamp:  # an archived copy speaks for the day of its capture, not for a date the page shows
        captured = _timestamp_date(read.timestamp)
        if read.date and read.date != captured:
            shown = f'page shows date {read.date.isoformat()}'
            notes = f'{notes}; {shown}' if notes else shown
        chosen = date or captured
    else:
        chosen = date or read.date or read.fetched.date()
    return Source(
        id=sid,
        kind=kind or read.kind,
        title=title or read.title or read.original,
        date=chosen,
        url=read.original,
        archive_url=archive_url,
        fetched=read.fetched,
        notes=notes,
    )


def capture(url: str, quotes: Sequence[str] = (), kind: str | None = None, title: str | None = None,
            date: datetime.date | None = None, refresh: bool = False, fetcher: Fetcher | None = None,
            session=None, run=subprocess.run, names: Sequence[str] = ()) -> CaptureResult:
    """Capture the source at the address: write its row if new and add the passages around the quotes.

    A Wayback address is stored readable and fetched raw. A live address that is gone is replaced by its
    nearest Wayback capture; without one the source is recorded as unreachable. Quotes that are already in a
    stored passage are skipped; quotes not found on the page are reported as missing, never stored. A new
    source none of whose quotes is found is not recorded at all.
    When no quote is given or none is found, the names decide: the passage around the first occurrence of each
    name is stored, and a name that is not found is reported as missing; a profile, a commit and an issue or
    comment of this repository store their whole text then, found name or not. Names are ignored when a quote
    is found; quotes not found are reported as missing either way.
    A fetcher given here keeps its own refresh setting; one built here refetches when refresh is true.
    """
    quotes = tuple(quotes)
    names = tuple(names)
    split = split_archive_url(url)
    if split is None and _is_wayback(url):
        raise CaptureError(f'{url}: give the full 14-digit capture URL, '
                           'such as https://web.archive.org/web/20100125023558/http://limi.net/about')
    original, timestamp = split if split else (url, None)
    sid = source_id(original, timestamp)
    sources = load_sources()
    if sid not in sources and not quotes and not names:
        raise CaptureError(f'{url}: a new source needs at least one quote or name')
    if (sid in sources and not refresh and not is_uncaptured(sources[sid])
            and all(_stored(sid, quote) for quote in quotes)):
        return CaptureResult(sid, False, (), (), False)

    fetcher = fetcher or Fetcher(refresh=refresh)
    session = session or github_session()
    try:
        try:
            if split:
                read = _read_archive(fetcher, url, None, run)
            else:
                read = _read_live(url, fetcher, session, run, refresh)
        except _Gone as gone:
            nearest = None if split else nearest_capture(fetcher, url)
            if nearest is None:
                return _unreachable(sources.get(sid), sid, original, timestamp, gone, quotes or names, kind, title,
                                    date)
            read = _read_archive(fetcher, nearest, KIND_BY_ADAPTER.get(adapter_for(url)), run)
    except _Gone as gone:  # the nearest capture is gone as well
        return _unreachable(sources.get(sid), sid, original, timestamp, gone, quotes or names, kind, title, date)
    except (FetchError, ExtractError, GitHubAPIError) as error:
        raise CaptureError(f'{url}: {error}') from error

    sid = source_id(read.original, read.timestamp)
    existing = sources.get(sid)
    found, missing = [], []
    quote_found = False
    for quote in quotes:
        if _stored(sid, quote):
            quote_found = True
            continue
        passage = _passage(read, quote)
        if passage is None:
            missing.append(quote)
        else:
            quote_found = True
            found.append(passage)
    if not quote_found and (names or not quotes):  # no quote found: the names decide
        if _is_whole(read):
            found.append(read.text.strip())
        else:
            for name in names:
                passage = _name_passage(read, name)
                if passage is None:
                    missing.append(name)
                elif passage not in found:
                    found.append(passage)
    if existing is None and not found:  # a new source is recorded only with a passage that supports something
        return CaptureResult(sid, False, (), tuple(missing), False)
    if existing is not None and found and is_uncaptured(existing):
        return _renew(existing, read, kind, title, date, found, missing)
    row = _source(existing, sid, read, kind, title, date, read.notes, refresh)
    if row is not None:
        write_source(row)
    added = tuple(passage for passage in found if add_passage(sid, passage))
    return CaptureResult(sid, existing is None, added, tuple(missing), False)


def _renew(existing, read, kind, title, date, found, missing):
    """Renew a source that was never read from this read, which found passages: its kind, title, date, fetch
    time and notes come from the read as for a new source (the notes of the read, such as `served …`, stay),
    and the passages replace the note that its excerpt held. A curated kind (such as `speaker-page`) stays when
    no kind is given and the read knows no more than the generic `page`; a specific kind of the read (video,
    profile, commit, issue-comment, pdf) replaces it."""
    new = _source(None, existing.id, read, kind, title, date, read.notes, False)
    new_kind = existing.kind if kind is None and read.kind == GENERIC_KIND else new.kind
    write_source(dataclasses.replace(existing, kind=new_kind, title=new.title, date=new.date, fetched=new.fetched,
                                     notes=new.notes))
    kept = [passage for passage in passages(existing.id) if not passage.startswith(UNCAPTURED_MARKERS)]
    replace_excerpt(existing.id, PASSAGE_SEPARATOR.join(kept))
    added = tuple(passage for passage in found if add_passage(existing.id, passage))
    return CaptureResult(existing.id, False, added, tuple(missing), False)


def _passage(read, quote):
    """The passage to store for the quote, or None when the quote is not in the text.

    A live profile or commit is short and its parts belong together (the author and date of a commit message),
    so its passage is the whole text, and so is a live issue or comment of this repository, our own public
    record; the text of an issue of another repository is cut to the block (issue or comment) with the quote,
    then to the paragraph around it, headed by the block's author and date; anything else gets the paragraph
    around the quote.
    """
    whole = _is_whole(read)
    for text in (read.text, read.full_text):
        block = _block(read, text, lambda part: find_quote(part, quote)) if not whole else None
        span = find_quote(block or text, quote)
        if span is not None:
            return text.strip() if whole else _headed(cut_passage(block or text, span), block)
    return None


def _is_whole(read):
    """True when the whole text of the live source is stored: a profile, a commit, an issue of this repository."""
    return read.timestamp is None and (
        read.kind in WHOLE_TEXT_KINDS or (read.kind == 'issue-comment' and _is_own(read.original)))


def _name_passage(read, name):
    """The passage around the first occurrence of the name, or None when the text does not name it."""
    for text in (read.text, read.full_text):
        block = _block(read, text, lambda part: find_name(part, name))
        span = find_name(block or text, name)
        if span is not None:
            return _headed(cut_passage(block or text, span), block)
    return None


def _block(read, text, finds):
    """The block (issue or comment) of a live issue page in which `finds` finds something, else None."""
    if read.timestamp is not None or read.kind != 'issue-comment':
        return None
    return next((block for block in BLOCK_START.split(text) if finds(block)), None)


def _headed(passage, block):
    """The passage headed by the author and date lines of its block, unless it holds them already."""
    if block is None:
        return passage
    head = '\n'.join(line for line in block.strip().split('\n\n', 1)[0].split('\n')
                     if line.startswith(('Author: ', 'Date: ')))
    return passage if not head or head in passage else f'{head}\n\n{passage}'


def _is_own(url):
    match = ISSUE_PATH.match(urllib.parse.urlsplit(url).path)
    return bool(match) and f'{match.group(1)}/{match.group(2)}'.lower() == OWN_REPOSITORY


def _unreachable(existing, sid, original, timestamp, gone, quotes, kind, title, date):
    """Record a source that could not be fetched; an existing row and its passages stay untouched."""
    missing = tuple(quote for quote in quotes if not _stored(sid, quote))
    if existing is None:
        note = f'could not be fetched on {gone.fetched.date().isoformat()}'
        read = _Read(original, timestamp, gone.kind or 'page', '', '', None, None, gone.fetched)
        write_source(_source(None, sid, read, kind, title, date, note, False))
        add_passage(sid, note)
    return CaptureResult(sid, existing is None, (), missing, True)


def capture_commit(url: str, email: str, names: Sequence[str] = (), **options) -> tuple[str, str | None]:
    """Capture a commit as the source that shows its author's address; return (source id, snippet).

    The commit is read from the local clone when there is one, so no network is needed, else from the GitHub API;
    its whole text is stored. The snippet is the line of the excerpt with the address (ignoring case),
    `Author: Name <address>`; None without an address. Without an address, `names` (at least one) are what the
    capture looks for. The other options go to `capture`. CaptureError when the commit could not be captured.
    """
    result = capture(url, names=(email,) if email else tuple(names), **options)
    if result.unreachable:
        raise CaptureError(f'{url}: could not be fetched')
    if result.source_id not in load_sources():
        raise CaptureError(f'{url}: not captured, {", ".join(result.missing) or "nothing"} not found')
    if not email:
        return result.source_id, None
    excerpt = read_excerpt(result.source_id)
    line = next((line.strip() for line in excerpt.splitlines()
                 if line.startswith('Author: ') and email.lower() in line.lower()), None)
    return result.source_id, line if line and find_quote(excerpt, line) else None
