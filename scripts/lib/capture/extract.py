"""Readable text from fetched HTML and PDF pages.

`text` is the main content, used for quotes and passages; `full_text` is everything readable on the page,
used only to find a quote that main-content extraction cut off, such as a sidebar biography. Neither is
ever written whole to `curated/`.
"""

import dataclasses
import datetime
import html as html_lib
import json
import os
import re
import subprocess
import urllib.parse

import trafilatura
from trafilatura.utils import load_html

from scripts.lib import git_history
from scripts.lib.capture.fetch import FetchError, Raw
from scripts.lib.github_api import GitHubAPIError, github_get
from scripts.lib.model import split_archive_url

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


BLOCK_TAGS = {'address', 'article', 'aside', 'blockquote', 'center', 'dd', 'details', 'dialog', 'div', 'dl', 'dt',
              'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
              'hr', 'legend', 'li', 'main', 'nav', 'ol', 'p', 'pre', 'section', 'summary', 'table', 'td', 'th',
              'tr', 'ul'}
HIDDEN_TAGS = {'head', 'noscript', 'script', 'style', 'template'}
BLOCK, LINE = '\ue000', '\ue001'  # markers from the private use area: lxml refuses control characters


def block_text(html: str) -> str:
    """Everything readable on the page, one paragraph per block element, separated by blank lines.

    A `<br>` is a line break, two of them a paragraph break, as old pages use them.
    """
    tree = load_html(html)
    body = tree.find('.//body') if tree is not None else None
    if body is None:
        return ''
    for element in list(body.iter()):
        tag = element.tag if isinstance(element.tag, str) else None
        if tag is None or tag.lower() in HIDDEN_TAGS:
            if element.getparent() is not None:
                element.drop_tree()  # keeps the text that follows the element
            continue
        tag = tag.lower()
        if tag in BLOCK_TAGS:
            element.text = BLOCK + (element.text or '')
            element.tail = BLOCK + (element.tail or '')
        elif tag == 'br':
            element.tail = LINE + (element.tail or '')
    text = ' '.join(body.text_content().split())
    paragraphs = []
    for block in text.split(BLOCK):
        lines = '\n'.join(line.strip() for line in block.split(LINE))
        paragraphs.extend(part.strip() for part in re.split(r'\n\s*\n', lines) if part.strip())
    return '\n\n'.join(paragraphs)


def extract_html(raw: Raw) -> Extracted:
    html = decode(raw)
    text = trafilatura.extract(html, output_format='markdown', include_comments=False,
                               include_tables=True, favor_recall=True, with_metadata=False) or ''
    full_text = block_text(html)
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


# --- site adapters ---

VOLTO_HOSTS = {'plone.org', '2022.ploneconf.org', '2023.ploneconf.org', '2024.ploneconf.org', '2025.ploneconf.org'}
VIDEO_HOSTS = {'youtube.com', 'youtu.be', 'vimeo.com'}
# first path segments of github.com that are pages of the site, not logins
GITHUB_RESERVED = {'search', 'orgs', 'settings', 'topics', 'marketplace', 'sponsors', 'explore', 'features', 'about',
                   'pricing', 'login', 'join', 'notifications', 'issues', 'pulls', 'trending', 'collections',
                   'events', 'new', 'apps', 'enterprise', 'security', 'customer-stories', 'readme', 'site'}
SUBTITLE_LANGUAGES = 'en.*,de.*,es.*,pt.*,it.*,nl.*,fr.*'
COMMIT_PATH = re.compile(r'^/([^/]+)/([^/]+)/commit/([0-9a-fA-F]+)/?$')
VTT_TAG = re.compile(r'<[^>]*>')
VTT_TIME = re.compile(r'(?:(\d+):)?(\d{2}):(\d{2})\.\d+')


def host_of(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def adapter_for(url: str) -> str:
    """Which extractor reads this address: volto, github-profile, commit, video or generic."""
    if split_archive_url(url):
        return 'generic'  # a Wayback copy is the raw capture, whatever the original was
    host = host_of(url)
    if host in VOLTO_HOSTS:
        return 'volto'
    if host in VIDEO_HOSTS:
        return 'video'
    if host == 'github.com':
        path = urllib.parse.urlsplit(url).path
        segments = [segment for segment in path.split('/') if segment]
        if len(segments) == 1 and segments[0].lower() not in GITHUB_RESERVED:
            return 'github-profile'
        if COMMIT_PATH.match(path):
            return 'commit'
    return 'generic'


def slate_paragraphs(nodes) -> list[str]:
    """Text of Slate nodes, one paragraph per block that holds text directly (so one per list item)."""
    paragraphs = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        children = node.get('children')
        if children is None:
            if node.get('text', '').strip():
                paragraphs.append(node['text'].strip())
        elif all(isinstance(child, dict) and 'children' not in child for child in children):
            text = ''.join(child.get('text', '') for child in children).strip()
            if text:
                paragraphs.append(text)
        else:
            paragraphs.extend(slate_paragraphs(children))
    return paragraphs


def block_paragraphs(block: dict) -> list[str]:
    paragraphs = slate_paragraphs(block.get('value'))
    text = block.get('text')
    draft = text.get('blocks') if isinstance(text, dict) else block.get('blocks')
    if isinstance(draft, list):
        paragraphs.extend(item['text'].strip() for item in draft
                          if isinstance(item, dict) and str(item.get('text', '')).strip())
    return paragraphs


def volto_paragraphs(page: dict) -> list[str]:
    paragraphs = [str(page[key]).strip() for key in ('title', 'description') if page.get(key)]
    blocks = page.get('blocks') or {}
    order = (page.get('blocks_layout') or {}).get('items') or list(blocks)
    for block_id in order:
        if isinstance(blocks.get(block_id), dict):
            paragraphs.extend(block_paragraphs(blocks[block_id]))
    return paragraphs


def extract_volto(fetcher, url: str) -> Extracted:
    """Text of a Volto page from its ++api++ JSON; the page's own HTML when the JSON has none."""
    parts = urllib.parse.urlsplit(url)
    api_url = f'{parts.scheme}://{parts.netloc}/++api++{parts.path}'
    try:
        raw = fetcher.get(api_url)
        page = json.loads(raw.body) if raw.status == 200 else None
    except (FetchError, ValueError):
        page = None
    if isinstance(page, dict):
        paragraphs = volto_paragraphs(page)
        # a page with only a title is a static export's stub, not a text
        if len(paragraphs) > (1 if page.get('title') else 0) + (1 if page.get('description') else 0):
            text = '\n\n'.join(paragraphs)
            return Extracted(text=text, full_text=text, title=page.get('title') or None,
                             date=parse_date(page.get('effective') or page.get('modified')))
    return extract_html(fetcher.get(url))


def extract_github_profile(login: str, session) -> Extracted:
    profile = github_get(session, f'https://api.github.com/users/{login}').json()
    lines = [f'{label}: {profile[key]}' for label, key in (
        ('Name', 'name'), ('Company', 'company'), ('Bio', 'bio'), ('Location', 'location'), ('Blog', 'blog'))
        if profile.get(key)]
    text = '\n'.join(lines)
    return Extracted(text=text, full_text=text, title=profile.get('name') or None,
                     date=datetime.datetime.now(datetime.timezone.utc).date())


def extract_commit(owner: str, repo: str, sha: str, run=subprocess.run, session=None) -> Extracted:
    """Author, date and message of a commit, from the bare clone when there is one, else from the API."""
    clone = os.path.join(git_history.CACHE_DIR, owner, f'{repo}.git')
    if os.path.isdir(clone):
        try:
            result = run(['git', '--git-dir', clone, 'show', '-s', '--format=%an <%ae>%n%aI%n%n%B', sha],
                         capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as error:
            raise ExtractError(f'git could not show {sha} in {clone}: {error}') from error
        output = result.stdout.decode('utf-8', errors='replace')
        author, date, _, message = (output.split('\n', 3) + ['', '', '', ''])[:4]
    else:
        if session is None:
            raise ExtractError(f'no clone of {owner}/{repo} and no GitHub session to ask')
        try:
            commit = github_get(session, f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}').json()['commit']
        except (GitHubAPIError, KeyError) as error:
            raise ExtractError(f'GitHub has no commit {sha} in {owner}/{repo}: {error}') from error
        person = commit['author']
        author = f"{person['name']} <{person['email']}>"
        date, message = person['date'], commit['message']
    text = f'Author: {author}\nDate: {date}\n\n{message.rstrip()}'
    return Extracted(text=text, full_text=text, title=None, date=parse_date(date))


def vtt_stamp(match) -> str:
    hours, minutes, seconds = int(match.group(1) or 0), match.group(2), match.group(3)
    return f'[{hours}:{minutes}:{seconds}]' if hours else f'[{minutes}:{seconds}]'


def parse_vtt(vtt: str) -> list[str]:
    """One `[mm:ss] text` line per new caption line; rolling auto-captions repeat the previous cue's lines."""
    lines, previous = [], set()
    for block in re.split(r'\n\s*\n', vtt.replace('\r\n', '\n')):
        rows = block.strip().split('\n')
        timing = next((i for i, row in enumerate(rows) if '-->' in row), None)
        if timing is None:  # WEBVTT header, NOTE, STYLE, REGION
            continue
        start = VTT_TIME.match(rows[timing].split('-->')[0].strip())
        if start is None:
            continue
        current = set()
        for row in rows[timing + 1:]:
            row = ' '.join(html_lib.unescape(VTT_TAG.sub('', row)).split())
            if not row:
                continue
            current.add(row)
            if row not in previous:
                lines.append(f'{vtt_stamp(start)} {row}')
        previous = current
    return lines


def extract_video(url: str, workdir: str, run=subprocess.run) -> Extracted:
    """Captions of a video (manual or automatic) with timestamps; the caption files stay in workdir."""
    os.makedirs(workdir, exist_ok=True)
    try:
        run(['yt-dlp', '--skip-download', '--write-auto-sub', '--write-sub', '--sub-langs', SUBTITLE_LANGUAGES,
             '--sub-format', 'vtt', '-o', os.path.join(workdir, '%(id)s'), url],
            capture_output=True, check=True)
        title = run(['yt-dlp', '--skip-download', '--print', 'title', url], capture_output=True, check=False)
    except FileNotFoundError as error:
        raise ExtractError('yt-dlp is not installed; install it to read video sources') from error
    except subprocess.CalledProcessError as error:
        raise ExtractError(f'yt-dlp failed for {url}: {error.stderr!r}') from error
    captions = sorted(name for name in os.listdir(workdir) if name.endswith('.vtt'))
    if not captions:
        raise ExtractError(f'{url} has no captions')
    with open(os.path.join(workdir, captions[0]), encoding='utf-8') as handle:
        text = '\n'.join(parse_vtt(handle.read()))
    if not text:
        raise ExtractError(f'{url} has empty captions')
    return Extracted(text=text, full_text=text, title=(title.stdout or b'').decode('utf-8', 'replace').strip() or None,
                     date=None)
