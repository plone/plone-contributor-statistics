"""Readable text from fetched HTML and PDF pages.

`text` is the main content, used for quotes and passages; `full_text` is everything readable on the page,
used only to find a quote that main-content extraction cut off, such as a sidebar biography. Neither is
ever written whole to `curated/`.
"""

import dataclasses
import datetime
import hashlib
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse

import trafilatura
from trafilatura.utils import load_html

from scripts.lib.capture import fetch  # the module: its clock `now` is the capture's clock
from scripts.lib.capture.fetch import Fetcher, FetchError, Raw, cache_dir
from scripts.lib.github_api import GitHubAPIError, github_get
from scripts.lib.model import split_archive_url
from scripts.lib.model.sources import GOOGLE_DOC_PATH

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
    # plain text, not Markdown: Markdown escapes `_` and `*` and adds `**` and `#`, so passages would not be
    # in the page's own spelling; trafilatura puts each block on a line, which becomes a paragraph here
    plain = trafilatura.extract(html, output_format='txt', include_comments=False,
                                include_tables=True, favor_recall=True, with_metadata=False) or ''
    text = '\n\n'.join(line.strip() for line in plain.splitlines() if line.strip())
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
LANGUAGES = ('en', 'de', 'es', 'pt', 'it', 'nl', 'fr')  # the order of preference among the tracks
# Only the automatic captions in the spoken language: yt-dlp names them `<language>-orig`, and a plain language
# code (`en`) selects YouTube's machine translation into it, which YouTube refuses to serve (HTTP 429)
ORIGINAL_TRACKS = '.*-orig'
# Without an original track, the manual subtitles, all of them: without --write-auto-sub no translation is fetched
MANUAL_TRACKS = 'all'
VIDEO_PACE_KEY = 'youtube.com'  # paced with the Fetcher: 30 seconds between two yt-dlp downloads
VIDEO_TIMEOUT = 600  # seconds for one call of yt-dlp
TRACKS_MANIFEST = 'tracks.json'  # in the cache folder of a video: the tracks of its last download, and its title
YOUTUBE_HOSTS = {'youtube.com', 'm.youtube.com', 'youtube-nocookie.com'}
YOUTUBE_PATHS = {'embed', 'shorts', 'live', 'v'}  # `/<path>/<video id>`
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]+$')
ISSUE_PATH = re.compile(r'^/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)/?$')
COMMENT_FRAGMENT = re.compile(r'^(issuecomment|discussion_r|pullrequestreview)-?(\d+)$')
COMMIT_PATH = re.compile(r'^/([^/]+)/([^/]+)/commit/([0-9a-fA-F]+)/?$')
VTT_TAG = re.compile(r'<[^>]*>')
VTT_TIME = re.compile(r'(?:(\d+):)?(\d{2}):(\d{2})\.\d+')


def host_of(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def adapter_for(url: str) -> str:
    """Which extractor reads this address: volto, google-doc, github-issue, github-profile, commit, video or generic."""
    if split_archive_url(url):
        return 'generic'  # a Wayback copy is the raw capture, whatever the original was
    host = host_of(url)
    if host == 'docs.google.com' and GOOGLE_DOC_PATH.match(urllib.parse.urlsplit(url).path):
        return 'google-doc'
    if host in VOLTO_HOSTS:
        return 'volto'
    if host in VIDEO_HOSTS:
        return 'video'
    if host == 'github.com':
        path = urllib.parse.urlsplit(url).path
        segments = [segment for segment in path.split('/') if segment]
        if len(segments) == 1 and segments[0].lower() not in GITHUB_RESERVED:
            return 'github-profile'
        if ISSUE_PATH.match(path):
            return 'github-issue'
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


def draft_paragraphs(draft) -> list[str]:
    """Text of draft.js blocks, one paragraph per block."""
    if not isinstance(draft, list):
        return []
    return [item['text'].strip() for item in draft if isinstance(item, dict) and str(item.get('text', '')).strip()]


def block_paragraphs(block: dict) -> list[str]:
    paragraphs = slate_paragraphs(block.get('value'))
    if block.get('@type') == 'text7':  # plone.org: a title (such as a person's name) over draft.js `content`
        title, content = block.get('title'), block.get('content')
        if isinstance(title, str) and title.strip():
            paragraphs.append(title.strip())
        paragraphs.extend(draft_paragraphs(content.get('blocks') if isinstance(content, dict) else None))
        return paragraphs
    text = block.get('text')
    paragraphs.extend(draft_paragraphs(text.get('blocks') if isinstance(text, dict) else block.get('blocks')))
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


def google_doc_id(url: str) -> str:
    return GOOGLE_DOC_PATH.match(urllib.parse.urlsplit(url).path).group(1)


def extract_google_doc(fetcher, doc_id: str) -> Extracted:
    """Text of a public Google Doc from its plain-text export; a private document raises ExtractError."""
    raw = fetcher.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
    # a private document answers with an error or redirects to a sign-in page, which is HTML, not plain text
    if raw.status != 200 or not (raw.content_type or '').lower().startswith('text/plain'):
        raise ExtractError('not a public document')
    lines = [line.strip() for line in raw.body.decode('utf-8', errors='replace').lstrip('\ufeff').splitlines()]
    paragraphs = [line for line in lines if line]
    text = '\n\n'.join(paragraphs)
    return Extracted(text=text, full_text=text, title=paragraphs[0] if paragraphs else None, date=None)


def extract_github_profile(login: str, session) -> Extracted:
    profile = github_get(session, f'https://api.github.com/users/{login}').json()
    # the Login line keeps the text of an account without any other field from being empty
    lines = [f'Login: {profile.get("login") or login}'] + [f'{label}: {profile[key]}' for label, key in (
        ('Name', 'name'), ('Company', 'company'), ('Bio', 'bio'), ('Location', 'location'), ('Blog', 'blog'))
        if profile.get(key)]
    text = '\n'.join(lines)
    return Extracted(text=text, full_text=text, title=profile.get('name') or None, date=fetch.now().date())


ISSUE_ENDPOINTS = {'issuecomment': 'issues/comments/{id}', 'discussion_r': 'pulls/comments/{id}',
                   'pullrequestreview': 'pulls/{number}/reviews/{id}'}


def _comment_block(data: dict, *, title: str | None = None) -> str:
    login = (data.get('user') or {}).get('login') or 'ghost'
    date = data.get('created_at') or data.get('submitted_at') or ''
    head = ([f'Title: {title}'] if title is not None else []) + [f'Author: {login}', f'Date: {date}']
    return '\n'.join(head) + '\n\n' + (data.get('body') or '').replace('\r\n', '\n').strip()


def extract_github_issue(owner: str, repo: str, number: str, fragment: str | None, session) -> Extracted:
    """An issue or pull request with its comments, or the one comment or review its fragment names."""
    base = f'https://api.github.com/repos/{owner}/{repo}'
    match = COMMENT_FRAGMENT.match(fragment or '')
    if match:
        path = ISSUE_ENDPOINTS[match.group(1)].format(id=match.group(2), number=number)
        data = github_get(session, f'{base}/{path}').json()
        text = _comment_block(data)
        return Extracted(text=text, full_text=text, title=None,
                         date=parse_date(data.get('created_at') or data.get('submitted_at')))
    issue = github_get(session, f'{base}/issues/{number}').json()
    blocks = [_comment_block(issue, title=issue.get('title') or '')]
    page = 1
    while True:
        comments = github_get(session, f'{base}/issues/{number}/comments',
                              params={'per_page': 100, 'page': page}).json()
        blocks.extend(_comment_block(comment) for comment in comments)
        if len(comments) < 100:
            break
        page += 1
    text = '\n\n'.join(blocks)
    return Extracted(text=text, full_text=text, title=issue.get('title') or None,
                     date=parse_date(issue.get('created_at')))


def extract_commit(owner: str, repo: str, sha: str, run=subprocess.run, session=None) -> Extracted:
    """Author, date and message of a commit, from the bare clone when there is one, else from the API."""
    # the clones of the collectors (git_history), in the cache shared by the worktrees of the checkout
    clone = cache_dir('repositories', owner, f'{repo}.git')
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


def track_rank(name: str):
    """Sort key of a caption file `<id>.<language>.vtt`: the original track first, then by LANGUAGES.

    yt-dlp names YouTube's automatic captions in the spoken language `<language>-orig`, and manual subtitles by
    their language.
    """
    language = name[:-len('.vtt')].rsplit('.', 1)[-1]
    languages = language.removesuffix('-orig').split('-')[0]
    order = LANGUAGES.index(languages) if languages in LANGUAGES else len(LANGUAGES)
    return (0 if language.endswith('-orig') else 1, order, name)


def _captions(folder):
    return [name for name in os.listdir(folder) if name.endswith('.vtt')]


def _output(error):
    return b''.join(part if isinstance(part, bytes) else str(part or '').encode()
                    for part in (error.stderr, error.stdout))


def video_folder(url: str) -> str:
    """The name of the cache folder that keeps the caption tracks of a video.

    For YouTube the video id, so every address of one video (`watch?v=`, `youtu.be/`, `embed/`, `shorts/`,
    `live/`) shares the folder; for any other address its host and path, made safe as a folder name.
    """
    parts = urllib.parse.urlsplit(url.strip())
    host = host_of(url)
    segments = [segment for segment in parts.path.split('/') if segment]
    video = None
    if host in YOUTUBE_HOSTS:
        if segments == ['watch']:
            video = (urllib.parse.parse_qs(parts.query).get('v') or [None])[0]
        elif len(segments) >= 2 and segments[0] in YOUTUBE_PATHS:
            video = segments[1]
    elif host == 'youtu.be' and segments:
        video = segments[0]
    if video and VIDEO_ID.match(video):
        return video
    return re.sub(r'[^A-Za-z0-9._-]+', '-', '/'.join([host, *segments])).strip('-.') or '_'


def _manifest_tracks(workdir):
    """The tracks and title of the manifest in workdir, or None without a manifest whose every track is there."""
    try:
        with open(os.path.join(workdir, TRACKS_MANIFEST), encoding='utf-8') as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return None
    tracks = manifest.get('tracks') if isinstance(manifest, dict) else None
    if not isinstance(tracks, list) or not tracks:
        return None
    for name in tracks:
        if (not isinstance(name, str) or not name.endswith('.vtt') or os.path.basename(name) != name
                or not os.path.isfile(os.path.join(workdir, name))):
            return None
    title = manifest.get('title')
    return tracks, title if isinstance(title, str) else None


def _keep(download, workdir):
    """Move the tracks of a download folder into workdir and remove the folder.

    A track that workdir holds already stays when it is the same; a different earlier version is kept beside it as
    `<name>.<hash>`, which is not a track name, so no downloaded caption file is ever lost.
    """
    for name in _captions(download):
        source, target = os.path.join(download, name), os.path.join(workdir, name)
        if os.path.exists(target):
            with open(source, 'rb') as new, open(target, 'rb') as old:
                new_body, old_body = new.read(), old.read()
            if new_body == old_body:
                continue
            os.replace(target, f'{target}.{hashlib.sha256(old_body).hexdigest()[:12]}')
        os.replace(source, target)
    shutil.rmtree(download, ignore_errors=True)  # what is left is a duplicate or a partial download


def _download(url, download, run, fetcher, which):
    """Download the original tracks into the download folder, else the manual ones; return the title or None."""
    options = ['--sleep-subtitles', '5', '--sleep-requests', '2', '--sub-format', 'vtt',
               '-o', os.path.join(download, '%(id)s')]
    if which('node'):
        options += ['--js-runtimes', 'node']
    downloads = (['--write-auto-sub', '--sub-langs', ORIGINAL_TRACKS], ['--write-sub', '--sub-langs', MANUAL_TRACKS])
    failure = None
    try:
        with fetcher.paced(VIDEO_PACE_KEY):
            for tracks in downloads:
                try:
                    run(['yt-dlp', '--skip-download', *tracks, *options, url], capture_output=True, check=True,
                        timeout=VIDEO_TIMEOUT)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                    failure = error
                if _captions(download):
                    break
                if isinstance(failure, subprocess.TimeoutExpired):
                    raise failure
                if failure is not None and b'HTTP Error 429' in _output(failure):
                    raise ExtractError(f'rate limited: YouTube answered HTTP 429 for {url}; retry later') from failure
            if not _captions(download):
                if failure is not None:
                    raise ExtractError(f'yt-dlp failed for {url}: {failure.stderr!r}') from failure
                raise ExtractError(f'{url} has no captions')
            try:
                title = run(['yt-dlp', '--skip-download', '--print', 'title', url], capture_output=True,
                            check=False, timeout=VIDEO_TIMEOUT).stdout
            except subprocess.TimeoutExpired:  # the tracks are there: the video is read without its title
                title = None
    except FileNotFoundError as error:
        raise ExtractError('yt-dlp is not installed; install it to read video sources') from error
    except subprocess.TimeoutExpired as error:
        raise ExtractError(f'yt-dlp timed out after {error.timeout} seconds for {url}') from error
    return (title or b'').decode('utf-8', 'replace').strip() or None


def extract_video(url: str, workdir: str, run=subprocess.run, fetcher=None, which=shutil.which,
                  refresh=False) -> Extracted:
    """Captions of a video with timestamps, from the tracks kept in workdir, the cache folder of the video.

    The tracks a read downloads are kept, and `tracks.json` in workdir lists them with the title of the video.
    When that manifest exists and every track it lists is there, the tracks are read from it without asking
    YouTube, unless `refresh`. Only the tracks of the manifest are read: other caption files in workdir, such as
    the translations that an earlier version fetched, are ignored, and no caption file is ever removed.

    yt-dlp is asked for the original automatic tracks (`<language>-orig`) only; when it writes none, once more
    for the manual subtitles only. Machine translations are never asked for. It writes into a fresh folder in
    workdir, so the tracks of this read are told from those of earlier reads, and they are moved into workdir.
    `text` is the preferred track, `full_text` every track as its own paragraph, so a quote in another
    language is still found and cut from the lines of its own track.

    A call that fails or times out after it wrote tracks still counts: what was written is read. Without any
    track, an `HTTP Error 429` in the output of yt-dlp is a distinct error (`rate limited: …`), a timeout is
    `timed out`, and no further call is made; any other failure is `yt-dlp failed`, no failure `has no captions`.
    A read without any track writes no manifest. The title is asked for only when there are tracks.

    Polite to YouTube: a pause between the downloads of all processes (the pace of the fetcher), and the pauses
    of yt-dlp between its requests.
    """
    os.makedirs(workdir, exist_ok=True)
    cached = None if refresh else _manifest_tracks(workdir)
    if cached is not None:
        names, title = cached
    else:
        download = tempfile.mkdtemp(dir=workdir, prefix='.download-')
        try:
            title = _download(url, download, run, fetcher or Fetcher(), which)
            names = sorted(_captions(download), key=track_rank)
        finally:
            _keep(download, workdir)
        manifest = {'url': url, 'tracks': names, 'title': title, 'fetched': fetch.now().isoformat()}
        fetch._write_atomic(os.path.join(workdir, TRACKS_MANIFEST),
                            (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    tracks = []
    for name in sorted(names, key=track_rank):
        with open(os.path.join(workdir, name), encoding='utf-8') as handle:
            lines = parse_vtt(handle.read())
        if lines:
            tracks.append('\n'.join(lines))
    if not tracks:
        raise ExtractError(f'{url} has empty captions')
    return Extracted(text=tracks[0], full_text='\n\n'.join(tracks), title=title, date=None)
