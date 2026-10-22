import datetime
import pathlib
import subprocess

import pytest

from scripts.lib.capture.extract import ExtractError, decode, extract, extract_html, extract_pdf
from scripts.lib.capture.fetch import Raw

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
