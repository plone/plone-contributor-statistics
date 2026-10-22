import datetime

from scripts.lib import paths
from scripts.lib.model import excerpt_path, load_sources, normalize_url, source_id, split_archive_url


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
