"""Readable text from fetched HTML and PDF pages.

`text` is the main content, used for quotes and passages; `full_text` is everything readable on the page,
used only to find a quote that main-content extraction cut off, such as a sidebar biography. Neither is
ever written whole to `curated/`.
"""

import dataclasses
import datetime
import re
import subprocess

import trafilatura

from scripts.lib.capture.fetch import Raw

CHARSET_HEADER = re.compile(r'charset\s*=\s*["\']?([\w.:-]+)', re.IGNORECASE)
CHARSET_META = re.compile(rb'<meta[^>]+charset\s*=\s*["\']?([\w.:-]+)', re.IGNORECASE)


# Browsers read these labels as windows-1252 (WHATWG Encoding), and old pages rely on it
WINDOWS_1252_LABELS = {'iso-8859-1', 'iso8859-1', 'latin1', 'latin-1', 'ascii', 'us-ascii'}


class ExtractError(Exception):
    """Text could not be extracted from a page."""


@dataclasses.dataclass(frozen=True)
class Extracted:
    text: str
    full_text: str
    title: str | None
    date: datetime.date | None


def declared_charset(raw: Raw) -> str | None:
    match = CHARSET_HEADER.search(raw.content_type or '')
    if match is None:
        match = CHARSET_META.search(raw.body[:4096])
        return match.group(1).decode('ascii', 'replace') if match else None
    return match.group(1)


def decode(raw: Raw) -> str:
    """Decode with the declared charset; otherwise UTF-8, falling back to cp1252."""
    charset = declared_charset(raw)
    if charset:
        if charset.lower() in WINDOWS_1252_LABELS:
            charset = 'cp1252'
        try:
            return raw.body.decode(charset, errors='replace')
        except LookupError:
            pass
    try:
        return raw.body.decode('utf-8')
    except UnicodeDecodeError:
        return raw.body.decode('cp1252', errors='replace')


def parse_date(value: str | None) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def extract_html(raw: Raw) -> Extracted:
    html = decode(raw)
    text = trafilatura.extract(html, output_format='markdown', include_comments=False,
                               include_tables=True, favor_recall=True, with_metadata=False) or ''
    full_text = trafilatura.html2txt(html, clean=False) or ''
    metadata = trafilatura.extract_metadata(html)
    title = getattr(metadata, 'title', None) or None
    return Extracted(text=text, full_text=full_text, title=title,
                     date=parse_date(getattr(metadata, 'date', None)))


def extract_pdf(raw: Raw, run=subprocess.run) -> Extracted:
    try:
        result = run(['pdftotext', '-enc', 'UTF-8', '-', '-'], input=raw.body,
                     capture_output=True, check=True)
    except FileNotFoundError as error:
        raise ExtractError('pdftotext is not installed; install poppler-utils to read PDF sources') from error
    except subprocess.CalledProcessError as error:
        raise ExtractError(f'pdftotext failed for {raw.url}: {error.stderr!r}') from error
    text = result.stdout.decode('utf-8', errors='replace')
    return Extracted(text=text, full_text=text, title=None, date=None)


def is_pdf(raw: Raw) -> bool:
    return ('application/pdf' in (raw.content_type or '').lower()
            or raw.url.lower().split('?')[0].split('#')[0].endswith('.pdf'))


def extract(raw: Raw, run=subprocess.run) -> Extracted:
    """Extract by content type; site adapters go in front of this dispatch."""
    if is_pdf(raw):
        return extract_pdf(raw, run=run)
    return extract_html(raw)
