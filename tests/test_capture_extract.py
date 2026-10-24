import contextlib
import datetime
import json
import os
import pathlib
import subprocess

import pytest

from scripts.lib.capture.extract import (
    ExtractError, adapter_for, decode, extract, extract_commit, extract_github_issue, extract_github_profile,
    extract_google_doc, extract_html, extract_pdf, extract_video, extract_volto)
from scripts.lib.capture.fetch import FetchError, Raw

FIXTURES = pathlib.Path(__file__).parent / 'fixtures' / 'capture'
NOW = datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc)


def raw(body, content_type='text/html', url='https://example.org/a'):
    return Raw(url=url, status=200, content_type=content_type, body=body, fetched=NOW)


def test_extract_html_drops_navigation():
    result = extract_html(raw((FIXTURES / 'article.html').read_bytes()))
    assert 'Zest Software' in result.text
    assert 'Privacy policy' not in result.text


def test_extract_html_keeps_sidebar_in_full_text():
    result = extract_html(raw((FIXTURES / 'article.html').read_bytes()))
    assert 'Acme Corporation' in result.full_text


def test_extract_html_full_text_keeps_paragraphs():
    """A quote found only in the full text is cut as its paragraph, so the full text must have paragraphs."""
    result = extract_html(raw((FIXTURES / 'article.html').read_bytes()))
    paragraphs = result.full_text.split('\n\n')
    assert 'About the author: Jane Doe leads the Plone team at Acme Corporation.' in paragraphs
    assert 'Privacy policy' in paragraphs
    assert not any('<' in p or 'charset' in p for p in paragraphs)


def test_extract_html_full_text_line_breaks():
    html = (b'<html><head><style>p {color: red}</style><script>var x = 1;</script></head><body>'
            b'<div>One\n   line<br>next line<br><br>new  paragraph<!-- hidden --></div>tail text</body></html>')
    assert extract_html(raw(html)).full_text == 'One line\nnext line\n\nnew paragraph\n\ntail text'


def test_extract_html_title_and_date():
    result = extract_html(raw((FIXTURES / 'article.html').read_bytes()))
    assert result.title == 'Plone sprint report'
    assert result.date == datetime.date(2015, 3, 12)


def test_extract_html_decodes_declared_charset():
    html = (FIXTURES / 'article.html').read_text(encoding='utf-8')
    html = html.replace('<meta charset="utf-8">', '<meta charset="iso-8859-1">')
    html = html.replace('He works for Zest Software', 'He works in Jyväskylä for Zest Software')
    result = extract_html(raw(html.encode('latin-1')))
    assert 'Jyväskylä' in result.text


def test_decode_prefers_header_charset():
    assert decode(raw('Jyväskylä'.encode('latin-1'), 'text/html; charset=ISO-8859-1')) == 'Jyväskylä'


def test_decode_http_equiv_meta():
    body = '<meta http-equiv="Content-Type" content="text/html; charset=windows-1252">Jyväskylä'
    assert 'Jyväskylä' in decode(raw(body.encode('cp1252')))


def test_decode_falls_back_to_cp1252():
    assert decode(raw('“quoted” Jyväskylä'.encode('cp1252'))) == '“quoted” Jyväskylä'


def test_decode_defaults_to_utf8():
    assert decode(raw('Jyväskylä'.encode('utf-8'))) == 'Jyväskylä'


def test_extract_pdf_runs_pdftotext():
    calls = []

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout=b'Alexander Limi, Plone Solutions', stderr=b'')

    result = extract_pdf(raw(b'%PDF-1.4', 'application/pdf'), run=run)
    assert result.text == 'Alexander Limi, Plone Solutions'
    assert result.full_text == result.text
    assert calls[0][0] == ['pdftotext', '-enc', 'UTF-8', '-', '-']
    assert calls[0][1]['input'] == b'%PDF-1.4'


def test_extract_pdf_without_pdftotext():
    def run(cmd, **kwargs):
        raise FileNotFoundError('pdftotext')

    with pytest.raises(ExtractError, match='pdftotext'):
        extract_pdf(raw(b'%PDF', 'application/pdf'), run=run)


def test_extract_dispatches_by_type_and_url():
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=b'from pdf', stderr=b'')

    assert extract(raw(b'x', 'application/pdf'), run=run).text == 'from pdf'
    assert extract(raw(b'x', 'application/octet-stream', 'https://example.org/f.pdf'), run=run).text == 'from pdf'
    html = (FIXTURES / 'article.html').read_bytes()
    assert 'Zest Software' in extract(raw(html), run=run).text


def test_decode_treats_iso_8859_1_as_windows_1252():
    body = b'\x93quoted\x94 \x96 dash'
    assert decode(raw(body, 'text/html; charset=iso-8859-1')) == '\u201cquoted\u201d \u2013 dash'
    meta = b'<meta charset="ISO-8859-1">' + body
    assert '\u201cquoted\u201d' in decode(raw(meta))


# --- site adapters ---


@pytest.mark.parametrize('url, expected', [
    ('https://plone.org/foundation/members', 'volto'),
    ('https://2024.ploneconf.org/speakers', 'volto'),
    ('https://2021.ploneconf.org/speakers', 'generic'),
    ('https://github.com/jensens', 'github-profile'),
    ('https://github.com/plone', 'github-profile'),
    ('https://github.com/jensens/', 'github-profile'),
    ('https://github.com/search?q=plone', 'generic'),
    ('https://github.com/plone/Products.CMFPlone', 'generic'),
    ('https://github.com/plone/Products.CMFPlone/commit/abc1234', 'commit'),
    ('https://github.com/plone/plone-contributor-statistics/issues/142', 'github-issue'),
    ('https://github.com/plone/plone-contributor-statistics/pull/153#issuecomment-6297324385', 'github-issue'),
    ('https://github.com/plone/Products.CMFPlone/pull/9/', 'github-issue'),
    ('https://github.com/plone/Products.CMFPlone/pull/9/files', 'generic'),
    ('https://github.com/plone/Products.CMFPlone/issues', 'generic'),
    ('https://www.youtube.com/watch?v=x', 'video'),
    ('https://youtu.be/x', 'video'),
    ('https://vimeo.com/123', 'video'),
    ('https://web.archive.org/web/20150312000000/https://github.com/jensens', 'generic'),
    ('https://web.archive.org/web/20150312000000id_/https://www.youtube.com/watch?v=x', 'generic'),
    ('https://web.archive.org/web/2015/https://plone.org/', 'generic'),
    ('https://example.org/a', 'generic'),
    ('https://docs.google.com/document/d/X1/edit', 'google-doc'),
    ('https://docs.google.com/document/d/X1', 'google-doc'),
    ('https://docs.google.com/spreadsheets/d/X1/edit', 'generic'),
    ('https://web.archive.org/web/20150312000000/https://docs.google.com/document/d/X1/edit', 'generic'),
])
def test_adapter_for(url, expected):
    assert adapter_for(url) == expected


class FakeFetcher:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_extract_volto_renders_blocks():
    page = {
        'title': 'Jane Doe', 'description': 'Speaker at the conference',
        'blocks': {
            'a': {'@type': 'slate', 'value': [
                {'type': 'p', 'children': [{'text': 'Jane works for '}, {'text': 'Acme', 'bold': True}]}]},
            'b': {'@type': 'text', 'text': {'blocks': [{'text': 'Second paragraph'}]}},
            'c': {'@type': 'slate', 'value': [{'type': 'ul', 'children': [
                {'type': 'li', 'children': [{'text': 'Item one'}]}]}]},
        },
        'blocks_layout': {'items': ['b', 'a', 'c']},
    }
    fetcher = FakeFetcher(raw(json.dumps(page).encode(), 'application/json'))
    result = extract_volto(fetcher, 'https://plone.org/foundation/jane')
    assert fetcher.urls == ['https://plone.org/++api++/foundation/jane']
    assert result.title == 'Jane Doe'
    assert result.text.split('\n\n') == [
        'Jane Doe', 'Speaker at the conference', 'Second paragraph', 'Jane works for Acme', 'Item one']


def test_extract_volto_keeps_query_out_of_api_path():
    page = {'title': 'T', 'blocks': {'a': {'@type': 'text', 'text': {'blocks': [{'text': 'Body'}]}}}}
    fetcher = FakeFetcher(raw(json.dumps(page).encode()))
    extract_volto(fetcher, 'https://2023.ploneconf.org/talks/x?a=1')
    assert fetcher.urls == ['https://2023.ploneconf.org/++api++/talks/x']


@pytest.mark.parametrize('first', [
    Raw(url='u', status=404, content_type='text/html', body=b'', fetched=NOW),
    raw(b'not json'),
    raw(b'{"blocks": {}}'),
    FetchError('boom'),
])
def test_extract_volto_falls_back_to_html(first):
    html = (FIXTURES / 'article.html').read_bytes()
    fetcher = FakeFetcher(first, raw(html))
    result = extract_volto(fetcher, 'https://2022.ploneconf.org/x')
    assert fetcher.urls[1] == 'https://2022.ploneconf.org/x'
    assert 'Zest Software' in result.text


class FakeGitHubResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self.headers = {}
        self.text = json.dumps(data)

    def json(self):
        return self.data


class FakeGitHubSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        return self.responses.pop(0)


def test_extract_github_profile_lines():
    session = FakeGitHubSession(FakeGitHubResponse({
        'login': 'jane', 'name': 'Jane Doe', 'company': '@kitconcept', 'bio': None,
        'location': '', 'blog': 'https://jane.example'}))
    result = extract_github_profile('jane', session)
    assert session.urls == ['https://api.github.com/users/jane']
    assert result.text.splitlines() == [
        'Login: jane', 'Name: Jane Doe', 'Company: @kitconcept', 'Blog: https://jane.example']
    assert 'Bio' not in result.text and 'Location' not in result.text
    assert result.date == datetime.datetime.now(datetime.timezone.utc).date()
    assert result.title == 'Jane Doe'


def test_extract_github_profile_without_other_fields_has_a_login_line():
    session = FakeGitHubSession(FakeGitHubResponse({
        'login': 'Taito', 'name': None, 'company': None, 'bio': None, 'location': None, 'blog': ''}))
    assert extract_github_profile('taito', session).text == 'Login: Taito'
    session = FakeGitHubSession(FakeGitHubResponse({}))
    assert extract_github_profile('taito', session).text == 'Login: taito'


class FakeRun:
    def __init__(self, stdout=b'', returncode=0):
        self.calls = []
        self.stdout = stdout
        self.returncode = returncode

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        return subprocess.CompletedProcess(command, self.returncode, stdout=self.stdout, stderr=b'')


def test_extract_commit_prefers_the_clone(tmp_path, monkeypatch):
    """The clones are those of the collectors, in the cache shared by the worktrees of the checkout."""
    monkeypatch.setenv('PLONE_STATS_CACHE', str(tmp_path))
    clone = tmp_path / 'repositories' / 'plone' / 'Products.CMFPlone.git'
    clone.mkdir(parents=True)
    run = FakeRun(b'Jane Doe <jane@example.org>\n2015-03-12T10:00:00+01:00\n\nFix the thing\n\nLonger text\n')
    session = FakeGitHubSession()
    result = extract_commit('plone', 'Products.CMFPlone', 'abc1234', run=run, session=session)
    assert session.urls == []
    assert run.calls[0][:3] == ['git', '--git-dir', str(clone)]
    assert result.text.splitlines()[:3] == [
        'Author: Jane Doe <jane@example.org>', 'Date: 2015-03-12T10:00:00+01:00', '']
    assert 'Fix the thing' in result.text
    assert result.date == datetime.date(2015, 3, 12)


def test_extract_commit_falls_back_to_api(tmp_path, monkeypatch):
    monkeypatch.setenv('PLONE_STATS_CACHE', str(tmp_path))
    run = FakeRun()
    session = FakeGitHubSession(FakeGitHubResponse({'commit': {
        'author': {'name': 'Jane Doe', 'email': 'jane@example.org', 'date': '2015-03-12T09:00:00Z'},
        'message': 'Fix the thing'}}))
    result = extract_commit('plone', 'plone.api', 'abc1234', run=run, session=session)
    assert run.calls == []
    assert session.urls == ['https://api.github.com/repos/plone/plone.api/commits/abc1234']
    assert result.text == 'Author: Jane Doe <jane@example.org>\nDate: 2015-03-12T09:00:00Z\n\nFix the thing'
    assert result.date == datetime.date(2015, 3, 12)


VTT = """WEBVTT
Kind: captions
Language: en

NOTE this is a comment

STYLE
::cue { color: red }

00:04:36.000 --> 00:04:38.000 align:start position:0%
currently working at Onna

00:04:38.000 --> 00:04:40.000 align:start position:0%
currently working at Onna
<00:04:38.500><c>and</c><00:04:39.000><c> before</c> that Zest

00:04:40.000 --> 00:04:42.000
and before that Zest
Plone Foundation

01:02:03.000 --> 01:02:05.000
Later in the talk
"""


def test_extract_video_parses_vtt(tmp_path):
    def run(command, **kwargs):
        if '--print' in command:
            return subprocess.CompletedProcess(command, 0, stdout=b'My talk\n', stderr=b'')
        (out(command) / 'abc.en.vtt').write_text(VTT, encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    result = extract_video('https://youtu.be/abc', str(tmp_path), run=run)
    assert result.text.splitlines() == [
        '[04:36] currently working at Onna',
        '[04:38] and before that Zest',
        '[04:40] Plone Foundation',
        '[1:02:03] Later in the talk']
    assert result.title == 'My talk'
    assert result.full_text == result.text


def test_extract_video_command(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if '--print' not in command:
            (out(command) / 'abc.en.vtt').write_text(VTT, encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout=b'T\n', stderr=b'')
    extract_video('https://youtu.be/abc', str(tmp_path), run=run, which=lambda name: '/usr/bin/node')
    downloads = [c for c in calls if '--print' not in c]
    assert len(downloads) == 1  # the original tracks were found: no call for manual subtitles
    download = downloads[0]
    assert download[0] == 'yt-dlp' and '--skip-download' in download
    # only the original automatic tracks: a plain language code selects a machine translation
    assert '--write-auto-sub' in download and '--write-sub' not in download
    assert download[download.index('--sub-langs') + 1] == '.*-orig'
    assert download[download.index('--sleep-subtitles') + 1] == '5'
    assert download[download.index('--sleep-requests') + 1] == '2'
    assert download[download.index('--js-runtimes') + 1] == 'node'
    # a fresh folder in the workdir per read, so the files of this read are told from those of earlier reads
    assert os.path.dirname(os.path.dirname(download[download.index('-o') + 1])) == str(tmp_path)
    assert os.path.basename(download[download.index('-o') + 1]) == '%(id)s'


def test_extract_video_without_captions_raises(tmp_path):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=b'T\n', stderr=b'')
    with pytest.raises(ExtractError):
        extract_video('https://youtu.be/abc', str(tmp_path), run=run)


def test_extract_video_without_yt_dlp_raises(tmp_path):
    def run(command, **kwargs):
        raise FileNotFoundError('yt-dlp')
    with pytest.raises(ExtractError):
        extract_video('https://youtu.be/abc', str(tmp_path), run=run)


def test_extract_html_main_text_keeps_the_spelling_of_the_page():
    """No Markdown: underscores and asterisks stay, bold and headings add nothing, one paragraph per block."""
    html = (b'<html><head><title>T</title></head><body><article><h1>The sprint</h1>'
            b'<p>It took a_long_time to fix the release process of Plone, but it worked out well in the end.</p>'
            b'<p>The sprint was held in <b>Rotterdam</b> at the office of Zest Software in the spring.</p>'
            b'<ul><li>item *one* of the list that the sprint team worked on</li>'
            b'<li>item two of the same list, also done during that week</li></ul>'
            b'</article></body></html>')
    text = extract_html(raw(html)).text
    paragraphs = text.split('\n\n')
    assert 'It took a_long_time to fix the release process of Plone, but it worked out well in the end.' in paragraphs
    assert 'The sprint was held in Rotterdam at the office of Zest Software in the spring.' in paragraphs
    assert any(p.endswith('item *one* of the list that the sprint team worked on') for p in paragraphs)
    assert '\\' not in text and '**' not in text and '#' not in text
    assert all(p and p == p.strip() for p in paragraphs)


def out(command):
    """The folder that a fake yt-dlp writes its tracks to: that of its `-o` template."""
    return pathlib.Path(os.path.dirname(command[command.index('-o') + 1]))


def vtt(*lines):
    cues = [f'00:00:{second:02d}.000 --> 00:00:{second + 1:02d}.000\n{line}' for second, line in enumerate(lines)]
    return 'WEBVTT\n\n' + '\n\n'.join(cues) + '\n'


def caption_run(workdir, tracks, calls=None):
    def run(command, **kwargs):
        if calls is not None:
            calls.append((command, kwargs))
        if '--print' in command:
            return subprocess.CompletedProcess(command, 0, stdout=b'T\n', stderr=b'')
        for name, text in tracks.items():
            (out(command) / name).write_text(text, encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    return run


def test_extract_video_prefers_the_original_track(tmp_path):
    """yt-dlp names auto-translations by their language, the original auto-captions `-orig`."""
    tracks = {'x.de.vtt': vtt('Ich arbeite bei Zest'), 'x.en-orig.vtt': vtt('I work for Zest')}
    result = extract_video('https://youtu.be/x', str(tmp_path), run=caption_run(tmp_path, tracks))
    assert result.text == '[00:00] I work for Zest'
    assert result.full_text.split('\n\n') == ['[00:00] I work for Zest', '[00:00] Ich arbeite bei Zest']


@pytest.mark.parametrize('names, preferred', [
    (['x.de.vtt', 'x.en.vtt'], 'x.en.vtt'),
    (['x.fr.vtt', 'x.de-DE.vtt'], 'x.de-DE.vtt'),
    (['x.de.vtt', 'x.en-US.vtt', 'x.nl.vtt'], 'x.en-US.vtt'),
    (['x.en.vtt', 'x.nl-orig.vtt'], 'x.nl-orig.vtt'),
])
def test_extract_video_language_order(tmp_path, names, preferred):
    tracks = {name: vtt(f'line of {name}') for name in names}
    result = extract_video('https://youtu.be/x', str(tmp_path), run=caption_run(tmp_path, tracks))
    assert result.text == f'[00:00] line of {preferred}'
    assert len(result.full_text.split('\n\n')) == len(names)


def test_extract_video_skips_an_empty_track(tmp_path):
    tracks = {'x.en-orig.vtt': 'WEBVTT\n', 'x.de.vtt': vtt('Ich arbeite bei Zest')}
    result = extract_video('https://youtu.be/x', str(tmp_path), run=caption_run(tmp_path, tracks))
    assert result.text == result.full_text == '[00:00] Ich arbeite bei Zest'


def test_extract_video_has_a_timeout(tmp_path):
    calls = []
    extract_video('https://youtu.be/x', str(tmp_path), run=caption_run(tmp_path, {'x.en.vtt': vtt('a')}, calls))
    assert [kwargs.get('timeout') for _, kwargs in calls] == [600, 600]


def test_extract_video_timeout_raises(tmp_path):
    def run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs.get('timeout'))
    with pytest.raises(ExtractError, match='timed out'):
        extract_video('https://youtu.be/x', str(tmp_path), run=run)


def issue_session(*responses):
    return FakeGitHubSession(*[FakeGitHubResponse(data) for data in responses])


@pytest.mark.parametrize('fragment, path', [
    ('issuecomment-77', 'issues/comments/77'),
    ('discussion_r77', 'pulls/comments/77'),
    ('pullrequestreview-77', 'pulls/5/reviews/77'),
])
def test_extract_issue_comment(fragment, path):
    stamp = {'submitted_at': '2026-10-01T10:00:00Z'} if 'review' in fragment else {'created_at': '2026-10-01T10:00:00Z'}
    session = issue_session({'user': {'login': 'jane'}, 'body': 'Fred is at Zest.\r\nSure.', **stamp})
    result = extract_github_issue('plone', 'x', '5', fragment, session)
    assert session.urls == [f'https://api.github.com/repos/plone/x/{path}']
    assert result.text == 'Author: jane\nDate: 2026-10-01T10:00:00Z\n\nFred is at Zest.\nSure.'
    assert result.date == datetime.date(2026, 10, 1)


def test_extract_issue_with_comments_paginates():
    comment = {'user': {'login': 'bob'}, 'body': 'again', 'created_at': '2026-10-03T00:00:00Z'}
    session = issue_session(
        {'title': 'Map Fred', 'user': {'login': 'jane'}, 'body': 'Please.', 'created_at': '2026-10-01T00:00:00Z'},
        [comment] * 100,
        [{'user': {'login': 'amy'}, 'body': None, 'created_at': '2026-10-04T00:00:00Z'}])
    calls = []
    original = session.get
    session.get = lambda url, params=None, timeout=None: (calls.append(params), original(url, params, timeout))[1]
    result = extract_github_issue('plone', 'x', '5', '', session)
    assert calls == [None, {'per_page': 100, 'page': 1}, {'per_page': 100, 'page': 2}]
    blocks = result.text.split('\n\n')
    assert blocks[0] == 'Title: Map Fred\nAuthor: jane\nDate: 2026-10-01T00:00:00Z'
    assert blocks[1] == 'Please.'
    assert result.text.count('Author: bob') == 100
    assert result.text.endswith('Author: amy\nDate: 2026-10-04T00:00:00Z\n\n')
    assert result.title == 'Map Fred' and result.date == datetime.date(2026, 10, 1)


def test_extract_google_doc():
    body = '\ufeffSprint participants\r\nJane Doe, Acme\r\n\r\n  John Roe, Beta  \r\n'.encode()
    fetcher = FakeFetcher(raw(body, 'text/plain'))
    result = extract_google_doc(fetcher, 'X1')
    assert fetcher.urls == ['https://docs.google.com/document/d/X1/export?format=txt']
    assert result.title == 'Sprint participants'
    assert result.text.split('\n\n') == ['Sprint participants', 'Jane Doe, Acme', 'John Roe, Beta']
    assert result.date is None


def test_private_google_doc_raises():
    private = Raw(url='u', status=401, content_type='text/html', body=b'<html>login</html>', fetched=NOW)
    with pytest.raises(ExtractError, match='not a public document'):
        extract_google_doc(FakeFetcher(private), 'X1')


def test_private_google_doc_redirected_to_a_login_page_raises():
    login = Raw(url='https://docs.google.com/document/d/X1/export?format=txt', status=200,
                content_type='text/html; charset=utf-8', body=b'<html>Sign in</html>', fetched=NOW,
                final_url='https://accounts.google.com/v3/signin/identifier?continue=https://docs.google.com/')
    with pytest.raises(ExtractError, match='not a public document'):
        extract_google_doc(FakeFetcher(login), 'X1')


def test_volto_text7_block_renders_title_and_content():
    """plone.org shows people with a `text7` block: a title and draft.js `content` (from a real page)."""
    text7 = {
        '@type': 'text7', 'title': 'Sébastien Verbois', 'img_column_width': '3',
        'url': 'https://plone.org/news-and-events/news/news-for-2026/x/sebastien-verbios.jpeg',
        'image_scales': {'image': [{'content-type': 'image/jpeg', 'filename': 'sebastien-verbios.jpeg'}]},
        'content': {'entityMap': {}, 'blocks': [
            {'data': {}, 'depth': 0, 'entityRanges': [], 'inlineStyleRanges': [], 'key': '3674r',
             'type': 'unstyled', 'text': 'Sébastien has been working with Plone since 2004.'},
            {'data': {}, 'depth': 0, 'entityRanges': [], 'inlineStyleRanges': [], 'key': '41cpm',
             'type': 'unstyled', 'text': 'Sébastien works as an Enterprise Architect at IMIO.'}]},
    }
    page = {'title': 'New members', 'blocks': {'t': {'@type': 'title'}, 'p': text7},
            'blocks_layout': {'items': ['t', 'p']}}
    result = extract_volto(FakeFetcher(raw(json.dumps(page).encode(), 'application/json')),
                           'https://plone.org/news-and-events/news/news-for-2026/x')
    assert result.text.split('\n\n') == [
        'New members', 'Sébastien Verbois', 'Sébastien has been working with Plone since 2004.',
        'Sébastien works as an Enterprise Architect at IMIO.']


def test_extract_video_without_node_has_no_js_runtime(tmp_path):
    calls = []
    extract_video('https://youtu.be/x', str(tmp_path), run=caption_run(tmp_path, {'x.en.vtt': vtt('a')}, calls),
                  which=lambda name: None)
    assert all('--js-runtimes' not in command for command, _ in calls)


def test_extract_video_downloads_are_paced_across_videos(tmp_path):
    from scripts.lib.capture.fetch import Fetcher
    sleeps, now = [], [1000.0]
    fetcher = Fetcher(cache=str(tmp_path / 'cache'), sleep=sleeps.append, clock=lambda: now[0])
    for name in ('a', 'b'):
        workdir = tmp_path / name
        workdir.mkdir()
        extract_video(f'https://youtu.be/{name}', str(workdir), run=caption_run(workdir, {f'{name}.en.vtt': vtt('x')}),
                      fetcher=fetcher)
        now[0] += 10
    assert sleeps == [20.0]
    # another fetcher on the same cache (another process) keeps the pace too
    other = Fetcher(cache=str(tmp_path / 'cache'), sleep=sleeps.append, clock=lambda: now[0])
    workdir = tmp_path / 'c'
    workdir.mkdir()
    extract_video('https://youtu.be/c', str(workdir), run=caption_run(workdir, {'c.en.vtt': vtt('x')}), fetcher=other)
    assert sleeps == [20.0, 20.0]


def test_extract_video_title_call_runs_inside_the_pace(tmp_path):
    from scripts.lib.capture.fetch import Fetcher
    fetcher = Fetcher(cache=str(tmp_path / 'cache'), sleep=lambda seconds: None, clock=lambda: 1000.0)
    inside, plain = [], caption_run(tmp_path, {'x.en.vtt': vtt('a')})
    original = fetcher.paced

    class Spy:
        def __enter__(self):
            self.context = original('youtube.com')
            inside.append(True)
            return self.context.__enter__()

        def __exit__(self, *exc):
            inside.clear()
            return self.context.__exit__(*exc)
    fetcher.paced = lambda key: Spy()
    seen = []

    def run(command, **kwargs):
        seen.append(bool(inside))
        return plain(command, **kwargs)
    extract_video('https://youtu.be/x', str(tmp_path), run=run, fetcher=fetcher)
    assert seen == [True, True]


def test_extract_video_rate_limit_is_named(tmp_path):
    def run(command, **kwargs):
        raise subprocess.CalledProcessError(
            1, command, stderr=b'ERROR: Unable to download: HTTP Error 429: Too Many Requests')
    with pytest.raises(ExtractError, match='^rate limited:'):
        extract_video('https://youtu.be/x', str(tmp_path), run=run)


def video_run(workdir, auto=None, manual=None, calls=None, fail=None, info=b'T\n'):
    """yt-dlp writing the automatic tracks for `--write-auto-sub`, the manual ones for `--write-sub`;
    `fail` (stderr) makes a download exit non-zero after writing its tracks; `info` is what `--print` prints.
    `manual` may map a `--sub-langs` value to the tracks that it writes."""
    def run(command, **kwargs):
        if calls is not None:
            calls.append(command)
        if '--print' in command:
            return subprocess.CompletedProcess(command, 0, stdout=info, stderr=b'')
        tracks = (auto if '--write-auto-sub' in command else manual) or {}
        if tracks and all(isinstance(value, dict) for value in tracks.values()):
            tracks = tracks.get(command[command.index('--sub-langs') + 1], {})
        for name, text in tracks.items():
            (out(command) / name).write_text(text, encoding='utf-8')
        if fail is not None:
            raise subprocess.CalledProcessError(1, command, stderr=fail)
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    return run


def test_extract_video_without_original_tracks_asks_once_for_manual_subtitles(tmp_path):
    calls = []
    run = video_run(tmp_path, manual={'x.en.vtt': vtt('I work for Zest')}, calls=calls)
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run, which=lambda name: '/usr/bin/node')
    assert result.text == '[00:00] I work for Zest'
    downloads = [c for c in calls if '--print' not in c]
    assert len(downloads) == 2
    manual = downloads[1]
    assert '--write-sub' in manual and '--write-auto-sub' not in manual
    assert manual[manual.index('--sub-langs') + 1] == 'all'
    for flag, value in (('--sleep-subtitles', '5'), ('--sleep-requests', '2'), ('--js-runtimes', 'node'),
                        ('-o', downloads[0][downloads[0].index('-o') + 1])):
        assert manual[manual.index(flag) + 1] == value
    assert calls[0][:3] == ['yt-dlp', '--skip-download', '--print']  # the title and language first


def test_extract_video_without_any_track_raises_no_captions(tmp_path):
    calls = []
    with pytest.raises(ExtractError, match='has no captions'):
        extract_video('https://youtu.be/x', str(tmp_path), run=video_run(tmp_path, calls=calls))
    assert len([c for c in calls if '--print' not in c]) == 2


def test_extract_video_reads_only_the_tracks_of_this_read(tmp_path):
    """A machine translation left in the folder by an earlier read is not a track of the video, and stays."""
    (tmp_path / 'x.de.vtt').write_text(vtt('Ich arbeite bei Zest'), encoding='utf-8')
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('I work for Zest')})
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert result.full_text == '[00:00] I work for Zest'
    assert sorted(os.listdir(tmp_path)) == ['tracks.json', 'x.de.vtt', 'x.en-orig.vtt']


def no_run(command, **kwargs):
    raise AssertionError(f'yt-dlp was called: {command}')


class Unpaced:
    """A fetcher whose pace does not wait, for tests that download one video twice."""

    @contextlib.contextmanager
    def paced(self, key):
        yield


def test_extract_video_writes_the_manifest(tmp_path, monkeypatch):
    from scripts.lib.capture import fetch
    monkeypatch.setattr(fetch, 'now', lambda: NOW)
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('I work for Zest'), 'x.de-orig.vtt': vtt('Zest')})
    extract_video('https://youtu.be/x', str(tmp_path), run=run)
    manifest = json.loads((tmp_path / 'tracks.json').read_text(encoding='utf-8'))
    assert manifest == {'url': 'https://youtu.be/x', 'tracks': ['x.en-orig.vtt', 'x.de-orig.vtt'], 'title': 'T',
                        'language': None, 'fetched': '2026-10-22T00:00:00+00:00'}
    assert sorted(os.listdir(tmp_path)) == ['tracks.json', 'x.de-orig.vtt', 'x.en-orig.vtt']  # no download folder


def test_cached_tracks_are_reused_without_a_request(tmp_path):
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('I work for Zest')})
    first = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    again = extract_video('https://www.youtube.com/watch?v=x', str(tmp_path), run=no_run)
    assert again == first
    assert (again.text, again.title) == ('[00:00] I work for Zest', 'T')


def test_cached_tracks_are_not_paced(tmp_path):
    class NoPace:
        def paced(self, key):
            raise AssertionError('paced although the tracks are cached')
    extract_video('https://youtu.be/x', str(tmp_path), run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('a')}))
    extract_video('https://youtu.be/x', str(tmp_path), run=no_run, fetcher=NoPace())


def test_only_tracks_of_the_manifest_are_read(tmp_path):
    """A stray track beside the listed ones, such as a translation of the first adapter, is never read."""
    (tmp_path / 'x.it-orig.vtt').write_text(vtt('Lavoro per Zest'), encoding='utf-8')
    (tmp_path / 'x.en.vtt').write_text(vtt('I work for Zest'), encoding='utf-8')
    (tmp_path / 'tracks.json').write_text(json.dumps(
        {'url': 'https://youtu.be/x', 'tracks': ['x.it-orig.vtt'], 'title': 'Un talk', 'fetched': NOW.isoformat()}))
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert (result.text, result.full_text, result.title) == ('[00:00] Lavoro per Zest', '[00:00] Lavoro per Zest',
                                                             'Un talk')


def test_a_manifest_with_a_missing_track_is_downloaded_again(tmp_path):
    (tmp_path / 'tracks.json').write_text(json.dumps(
        {'url': 'https://youtu.be/x', 'tracks': ['x.it-orig.vtt'], 'title': 'Un talk', 'fetched': NOW.isoformat()}))
    calls = []
    result = extract_video('https://youtu.be/x', str(tmp_path),
                           run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('I work for Zest')}, calls=calls))
    assert result.text == '[00:00] I work for Zest' and calls
    assert json.loads((tmp_path / 'tracks.json').read_text())['tracks'] == ['x.en-orig.vtt']


def test_refresh_downloads_again_and_keeps_old_files(tmp_path):
    extract_video('https://youtu.be/x', str(tmp_path), fetcher=Unpaced(),
                  run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('old line'), 'x.de-orig.vtt': vtt('alt')}))
    (tmp_path / 'x.en.vtt').write_text(vtt('a stray translation'), encoding='utf-8')
    calls = []
    result = extract_video('https://youtu.be/x', str(tmp_path), refresh=True, fetcher=Unpaced(),
                           run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('new line')}, calls=calls))
    assert calls and result.full_text == '[00:00] new line'
    assert json.loads((tmp_path / 'tracks.json').read_text())['tracks'] == ['x.en-orig.vtt']
    names = sorted(os.listdir(tmp_path))
    # the earlier version of a track downloaded again is kept beside it, under a name that is not a track
    kept = [name for name in names if name.startswith('x.en-orig.vtt.')]
    assert len(kept) == 1 and not kept[0].endswith('.vtt')
    assert (tmp_path / kept[0]).read_text(encoding='utf-8') == vtt('old line')
    assert set(names) == {'tracks.json', 'x.de-orig.vtt', 'x.en.vtt', 'x.en-orig.vtt', kept[0]}


def test_a_track_downloaded_again_unchanged_is_kept_once(tmp_path):
    for refresh in (False, True):
        extract_video('https://youtu.be/x', str(tmp_path), refresh=refresh, fetcher=Unpaced(),
                      run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('same')}))
    assert sorted(os.listdir(tmp_path)) == ['tracks.json', 'x.en-orig.vtt']


def test_a_failed_read_writes_no_manifest(tmp_path):
    with pytest.raises(ExtractError, match='has no captions'):
        extract_video('https://youtu.be/x', str(tmp_path), run=video_run(tmp_path))
    assert os.listdir(tmp_path) == []


def test_tracks_written_before_a_failure_are_kept(tmp_path):
    """Even a read that fails keeps what yt-dlp wrote: an empty track is still a downloaded capture."""
    with pytest.raises(ExtractError, match='empty captions'):
        extract_video('https://youtu.be/x', str(tmp_path), run=video_run(tmp_path, auto={'x.en-orig.vtt': 'WEBVTT\n'}))
    assert sorted(os.listdir(tmp_path)) == ['tracks.json', 'x.en-orig.vtt']


@pytest.mark.parametrize('url, folder', [
    ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
    ('https://youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=42s', 'dQw4w9WgXcQ'),
    ('https://m.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
    ('https://youtu.be/dQw4w9WgXcQ?t=10', 'dQw4w9WgXcQ'),
    ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
    ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
    ('https://www.youtube.com/live/dQw4w9WgXcQ?si=abc', 'dQw4w9WgXcQ'),
    ('https://vimeo.com/123456', 'vimeo.com-123456'),
    ('https://vimeo.com/channels/plone/123456?x=1', 'vimeo.com-channels-plone-123456'),
    ('https://plone.tv/talks/my_talk', 'plone.tv-talks-my_talk'),
    ('https://www.youtube.com/playlist?list=PL1', 'youtube.com-playlist'),
])
def test_video_folder(url, folder):
    from scripts.lib.capture.extract import video_folder
    assert video_folder(url) == folder


def test_two_sources_of_one_video_share_the_folder():
    from scripts.lib.capture.extract import video_folder
    assert video_folder('https://youtu.be/dQw4w9WgXcQ') == video_folder(
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3m')


def test_extract_video_uses_the_tracks_written_before_a_failure(tmp_path):
    calls = []
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('I work for Zest')}, calls=calls,
                    fail=b'ERROR: Unable to download video subtitles for \'de-orig\': HTTP Error 429')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert result.text == '[00:00] I work for Zest'
    assert len([c for c in calls if '--print' not in c]) == 1


def test_extract_video_manual_tracks_written_before_a_failure(tmp_path):
    def run(command, **kwargs):
        if '--print' in command:
            return subprocess.CompletedProcess(command, 0, stdout=b'T\n', stderr=b'')
        if '--write-sub' in command:
            (out(command) / 'x.de.vtt').write_text(vtt('Ich arbeite bei Zest'), encoding='utf-8')
        raise subprocess.CalledProcessError(1, command, stderr=b'ERROR: something else')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert result.text == '[00:00] Ich arbeite bei Zest'


def test_extract_video_rate_limit_asks_no_more(tmp_path):
    """After a 429 without any track, no call for manual subtitles: YouTube asked us to wait."""
    calls = []
    with pytest.raises(ExtractError, match='^rate limited:'):
        extract_video('https://youtu.be/x', str(tmp_path),
                      run=video_run(tmp_path, calls=calls, fail=b'ERROR: HTTP Error 429: Too Many Requests'))
    assert len(calls) == 2  # the title and language, the original tracks


def test_extract_video_rate_limit_of_the_manual_call_is_named(tmp_path):
    def run(command, **kwargs):
        if '--write-sub' in command:
            raise subprocess.CalledProcessError(1, command, stderr=b'ERROR: HTTP Error 429: Too Many Requests')
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    with pytest.raises(ExtractError, match='^rate limited:'):
        extract_video('https://youtu.be/x', str(tmp_path), run=run)


def test_extract_video_failure_without_tracks_is_named(tmp_path):
    with pytest.raises(ExtractError, match='^yt-dlp failed'):
        extract_video('https://youtu.be/x', str(tmp_path),
                      run=video_run(tmp_path, fail=b'ERROR: Video unavailable'))


def test_extract_video_uses_the_tracks_written_before_a_timeout(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if '--print' in command:
            return subprocess.CompletedProcess(command, 0, stdout=b'My talk\nNA\n', stderr=b'')
        (out(command) / 'x.en-orig.vtt').write_text(vtt('I work for Zest'), encoding='utf-8')
        raise subprocess.TimeoutExpired(command, kwargs.get('timeout'))
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert (result.text, result.title) == ('[00:00] I work for Zest', 'My talk')
    assert len([c for c in calls if '--print' not in c]) == 1


def downloads_of(calls):
    return [command for command in calls if '--print' not in command]


def sub_langs(command):
    return command[command.index('--sub-langs') + 1]


def test_a_cache_hit_keeps_the_fetch_time_of_the_manifest(tmp_path):
    (tmp_path / 'x.it-orig.vtt').write_text(vtt('Lavoro per Zest'), encoding='utf-8')
    (tmp_path / 'tracks.json').write_text(json.dumps(
        {'url': 'https://youtu.be/x', 'tracks': ['x.it-orig.vtt'], 'title': 'T',
         'fetched': '2026-10-20T10:15:00+00:00'}))
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert result.fetched == datetime.datetime(2026, 10, 20, 10, 15, tzinfo=datetime.timezone.utc)


def test_a_download_records_its_fetch_time(tmp_path, monkeypatch):
    from scripts.lib.capture import fetch
    monkeypatch.setattr(fetch, 'now', lambda: NOW)
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('a')})
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert result.fetched == NOW


def test_known_language_asks_for_its_original_track_only(tmp_path):
    calls = []
    run = video_run(tmp_path, auto={'x.it-orig.vtt': vtt('Lavoro per Zest')}, calls=calls, info=b'Un talk\nit\n')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run, which=lambda name: '/usr/bin/node')
    assert calls[0] == ['yt-dlp', '--skip-download', '--print', 'title', '--print', 'language',
                        '--js-runtimes', 'node', 'https://youtu.be/x']
    assert [sub_langs(command) for command in downloads_of(calls)] == ['it-orig']
    assert (result.text, result.title) == ('[00:00] Lavoro per Zest', 'Un talk')
    manifest = json.loads((tmp_path / 'tracks.json').read_text())
    assert (manifest['language'], manifest['tracks'], manifest['title']) == ('it', ['x.it-orig.vtt'], 'Un talk')


@pytest.mark.parametrize('info', [b'T\nNA\n', b'T\n', b'T\nnone\n'])
def test_unknown_language_asks_for_every_original_track(tmp_path, info):
    calls = []
    run = video_run(tmp_path, auto={'x.en-orig.vtt': vtt('a')}, calls=calls, info=info)
    extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert [sub_langs(command) for command in downloads_of(calls)] == ['.*-orig']
    assert json.loads((tmp_path / 'tracks.json').read_text())['language'] is None


def test_known_language_falls_back_to_its_manual_subtitles(tmp_path):
    calls = []
    run = video_run(tmp_path, manual={'it': {'x.it.vtt': vtt('Lavoro per Zest')}}, calls=calls, info=b'T\nit\n')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    downloads = downloads_of(calls)
    assert [sub_langs(command) for command in downloads] == ['it-orig', 'it']
    assert '--write-sub' in downloads[1] and '--write-auto-sub' not in downloads[1]
    assert result.text == '[00:00] Lavoro per Zest'


def test_known_language_falls_back_to_all_manual_subtitles(tmp_path):
    calls = []
    run = video_run(tmp_path, manual={'all': {'x.en.vtt': vtt('I work for Zest')}}, calls=calls,
                    info=b'T\nit\n')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    downloads = downloads_of(calls)
    assert [sub_langs(command) for command in downloads] == ['it-orig', 'it', 'all']
    assert '--write-auto-sub' not in downloads[2]
    assert result.text == '[00:00] I work for Zest'  # no track in the language: every track that came


def test_the_info_call_runs_first_inside_the_pace(tmp_path):
    from scripts.lib.capture.fetch import Fetcher
    fetcher = Fetcher(cache=str(tmp_path / 'cache'), sleep=lambda seconds: None, clock=lambda: 1000.0)
    inside, order = [], []
    original = fetcher.paced

    @contextlib.contextmanager
    def paced(key):
        with original(key):
            inside.append(True)
            yield
            inside.clear()
    fetcher.paced = paced
    plain = video_run(tmp_path / 'v', auto={'x.it-orig.vtt': vtt('a')}, info=b'T\nit\n')

    def run(command, **kwargs):
        order.append(('print' if '--print' in command else 'download', bool(inside)))
        return plain(command, **kwargs)
    extract_video('https://youtu.be/x', str(tmp_path / 'v'), run=run, fetcher=fetcher)
    assert order == [('print', True), ('download', True)]


def test_a_rate_limited_info_call_asks_no_more(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'ERROR: HTTP Error 429: Too Many Requests')
    with pytest.raises(ExtractError, match='^rate limited:'):
        extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert len(calls) == 1 and not os.path.exists(tmp_path / 'tracks.json')


def test_a_failed_info_call_reads_with_unknown_language(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if '--print' in command:
            return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'ERROR: something')
        (out(command) / 'x.en-orig.vtt').write_text(vtt('a'), encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert [sub_langs(command) for command in downloads_of(calls)] == ['.*-orig'] and result.title is None


def write_manifest(folder, tracks, **fields):
    for name in tracks:
        (folder / name).write_text(vtt(f'line of {name}'), encoding='utf-8')
    (folder / 'tracks.json').write_text(json.dumps(
        {'url': 'https://youtu.be/x', 'tracks': list(tracks), 'title': 'T', 'fetched': NOW.isoformat(), **fields}))


def test_a_cache_hit_with_a_language_reads_only_its_tracks(tmp_path):
    write_manifest(tmp_path, ['x.en-orig.vtt', 'x.it-orig.vtt', 'x.de-DE-orig.vtt'], language='it')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert result.full_text == '[00:00] line of x.it-orig.vtt'


def test_a_cache_hit_without_a_language_reads_every_listed_track(tmp_path):
    write_manifest(tmp_path, ['x.it-orig.vtt', 'x.en-orig.vtt'])
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert result.full_text.split('\n\n') == ['[00:00] line of x.en-orig.vtt', '[00:00] line of x.it-orig.vtt']


def test_a_cache_hit_whose_language_has_no_track_reads_every_listed_track(tmp_path):
    write_manifest(tmp_path, ['x.en.vtt', 'x.de.vtt'], language='it')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert result.text == '[00:00] line of x.en.vtt' and len(result.full_text.split('\n\n')) == 2


def test_the_track_in_the_language_of_the_video_ranks_first():
    from scripts.lib.capture.extract import track_rank
    names = ['x.en-orig.vtt', 'x.it.vtt', 'x.it-orig.vtt', 'x.de.vtt']
    assert sorted(names, key=lambda name: track_rank(name, 'it')) == [
        'x.it-orig.vtt', 'x.it.vtt', 'x.en-orig.vtt', 'x.de.vtt']
    assert sorted(names, key=track_rank)[0] == 'x.en-orig.vtt'


def test_a_language_with_a_region_also_asks_for_the_language_without_it(tmp_path):
    calls = []
    run = video_run(tmp_path, manual={'pt-BR,pt': {'x.pt.vtt': vtt('Trabalho na Zest')}}, calls=calls,
                    info=b'T\npt-BR\n')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=run)
    assert [sub_langs(command) for command in downloads_of(calls)] == ['pt-BR-orig,pt-orig', 'pt-BR,pt']
    assert result.text == '[00:00] Trabalho na Zest'


def test_a_cache_hit_reads_the_track_of_the_language_without_its_region(tmp_path):
    write_manifest(tmp_path, ['x.en-orig.vtt', 'x.de-DE-orig.vtt'], language='en-US')
    result = extract_video('https://youtu.be/x', str(tmp_path), run=no_run)
    assert result.full_text == '[00:00] line of x.en-orig.vtt'


@pytest.mark.parametrize('printed', [b'T\nen+de\n', b'T\nen;rm -rf\n', b'T\n.*\n'])
def test_a_language_that_is_not_a_code_is_unknown(tmp_path, printed):
    calls = []
    extract_video('https://youtu.be/x', str(tmp_path),
                  run=video_run(tmp_path, auto={'x.en-orig.vtt': vtt('a')}, calls=calls, info=printed))
    assert [sub_langs(command) for command in downloads_of(calls)] == ['.*-orig']
