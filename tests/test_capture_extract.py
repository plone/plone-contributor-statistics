import datetime
import json
import os
import pathlib
import subprocess

import pytest

from scripts.lib.capture.extract import (
    ExtractError, adapter_for, decode, extract, extract_commit, extract_github_profile, extract_html, extract_pdf,
    extract_video, extract_volto)
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
    ('https://www.youtube.com/watch?v=x', 'video'),
    ('https://youtu.be/x', 'video'),
    ('https://vimeo.com/123', 'video'),
    ('https://web.archive.org/web/20150312000000/https://github.com/jensens', 'generic'),
    ('https://web.archive.org/web/20150312000000id_/https://www.youtube.com/watch?v=x', 'generic'),
    ('https://web.archive.org/web/2015/https://plone.org/', 'generic'),
    ('https://example.org/a', 'generic'),
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
    fetcher = FakeFetcher(raw(json.dumps({'title': 'T', 'blocks': {'a': {'@type': 'text', 'text': {'blocks': [{'text': 'Body'}]}}}}).encode()))
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
    assert result.text.splitlines() == ['Name: Jane Doe', 'Company: @kitconcept', 'Blog: https://jane.example']
    assert 'Bio' not in result.text and 'Location' not in result.text
    assert result.date == datetime.datetime.now(datetime.timezone.utc).date()
    assert result.title == 'Jane Doe'


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
        (tmp_path / 'abc.en.vtt').write_text(VTT, encoding='utf-8')
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
            (tmp_path / 'abc.en.vtt').write_text(VTT, encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout=b'T\n', stderr=b'')
    extract_video('https://youtu.be/abc', str(tmp_path), run=run)
    download = next(c for c in calls if '--print' not in c)
    assert download[0] == 'yt-dlp' and '--skip-download' in download
    assert download[download.index('--sub-langs') + 1] == 'en.*,de.*,es.*,pt.*,it.*,nl.*,fr.*'
    assert download[download.index('-o') + 1] == os.path.join(str(tmp_path), '%(id)s')


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
