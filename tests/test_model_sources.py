import datetime

from scripts.lib import paths
from scripts.lib.model import (
    Source,
    add_passage,
    excerpt_path,
    load_sources,
    normalize_url,
    passages,
    read_excerpt,
    source_id,
    split_archive_url,
    write_source,
)


def test_source_id_ignores_url_noise():
    ids = {source_id(u) for u in ('https://github.com/fredvd', 'http://github.com/fredvd/',
                                  'https://GitHub.com:443/fredvd#top')}
    assert len(ids) == 1
    assert source_id('https://a.org/x?searchterm=None') != source_id('https://a.org/x')
    assert len(source_id('https://a.org/x')) == 12


def test_split_archive_url_accepts_every_flag():
    for url in ('https://web.archive.org/web/20051017042508/http://ploneconf2005.bluedynamics.net:80/speakers',
                'http://web.archive.org/web/20051017042508id_/http://ploneconf2005.bluedynamics.net:80/speakers',
                'https://web.archive.org/web/20051017042508if_/ploneconf2005.bluedynamics.net:80/speakers'):
        original, ts = split_archive_url(url)
        assert ts == '20051017042508'
        assert normalize_url(original) == 'ploneconf2005.bluedynamics.net/speakers'
    assert split_archive_url('https://plone.org/foundation') is None


def test_archived_and_live_copies_are_different_sources():
    assert source_id('https://limi.net/about') != source_id('https://limi.net/about', '20100125023558')


def test_normalize_url_keeps_query_and_bare_host():
    assert normalize_url('https://github.com/fredvd') == 'github.com/fredvd'
    assert normalize_url('HTTP://Example.org/') == 'example.org'
    assert normalize_url('https://www.a.org:80/x/?q=1#f') == 'www.a.org/x?q=1'


def test_load_sources_reads_the_register(tmp_repo):
    sid = source_id('https://limi.net/about', '20100125023558')
    paths.SOURCES.write_text(
        'id,kind,title,date,url,archive_url,fetched,notes\n'
        f'{sid},page,About Limi,2010-01-25,https://limi.net/about,'
        'https://web.archive.org/web/20100125023558/http://limi.net:80/about,2026-10-22T14:03:51Z,\n',
        encoding='utf-8')
    source = load_sources()[sid]
    assert source.date == datetime.date(2010, 1, 25)
    assert source.fetched.tzinfo is not None
    assert excerpt_path(sid) == paths.EXCERPTS_DIR / f'{sid}.md'


def _source(sid, title='A page'):
    return Source(sid, 'page', title, datetime.date(2010, 1, 25), 'https://limi.net/about', None,
                  datetime.datetime(2026, 10, 22, 14, 3, 51, tzinfo=datetime.timezone.utc), None)


def test_write_source_keeps_rows_sorted(tmp_repo):
    write_source(_source('bbbbbbbbbbbb'))
    write_source(_source('aaaaaaaaaaaa'))
    assert list(load_sources()) == ['aaaaaaaaaaaa', 'bbbbbbbbbbbb']
    write_source(_source('aaaaaaaaaaaa', title='A new title'))
    sources = load_sources()
    assert list(sources) == ['aaaaaaaaaaaa', 'bbbbbbbbbbbb']
    assert sources['aaaaaaaaaaaa'].title == 'A new title'
    text = paths.SOURCES.read_text(encoding='utf-8')
    assert '2026-10-22T14:03:51Z' in text
    assert text.count('\n') == 3


def test_add_passage_is_idempotent(tmp_repo):
    assert read_excerpt('aaaaaaaaaaaa') == ''
    assert add_passage('aaaaaaaaaaaa', 'He works for Zest.') is True
    assert add_passage('aaaaaaaaaaaa', 'He  works for\nZest.') is False
    assert add_passage('aaaaaaaaaaaa', 'Nowadays he works for kitconcept.') is True
    assert passages('aaaaaaaaaaaa') == ['He works for Zest.', 'Nowadays he works for kitconcept.']
    assert read_excerpt('aaaaaaaaaaaa').endswith('kitconcept.\n')


def test_load_sources_memo_sees_external_edits(tmp_repo):
    header = 'id,kind,title,date,url,archive_url,fetched,notes\n'
    one = 'aaaaaaaaaaaa,page,One,2010-01-25,https://a.org/1,,2026-10-22T09:30:00Z,\n'
    two = 'bbbbbbbbbbbb,page,Two,2010-01-25,https://a.org/2,,2026-10-22T09:30:00Z,\n'
    paths.SOURCES.write_text(header + one, encoding='utf-8')
    assert list(load_sources()) == ['aaaaaaaaaaaa']
    paths.SOURCES.write_text(header + one + two, encoding='utf-8')
    assert list(load_sources()) == ['aaaaaaaaaaaa', 'bbbbbbbbbbbb']
    paths.SOURCES.write_text(header + two, encoding='utf-8')
    assert list(load_sources()) == ['bbbbbbbbbbbb']


def test_comment_fragments_are_kept():
    pr = 'https://github.com/plone/plone-contributor-statistics/pull/153'
    first, second = f'{pr}#issuecomment-6297324385', f'{pr}#issuecomment-6297324386'
    assert len({source_id(first), source_id(second), source_id(pr)}) == 3
    assert source_id(f'{pr}#top') == source_id(pr) == source_id(f'{pr}/')
    assert normalize_url(f'{pr}#discussion_r12') != normalize_url(f'{pr}#pullrequestreview-12')
    assert source_id(first) == source_id(first.replace('https://', 'http://').replace('github.com', 'GitHub.com'))
    assert source_id('https://example.org/x#issuecomment-1') == source_id('https://example.org/x')
