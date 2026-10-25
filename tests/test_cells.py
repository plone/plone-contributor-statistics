"""The parser of free-text source cells."""

from scripts.lib.cells import Cited, parse_segment, quotes_of, split_segments

SPEAKER = 'https://2017.ploneconf.org/people/jane-doe.html'
ARCHIVED = 'https://web.archive.org/web/20171020000000/https://2017.ploneconf.org/people/jane-doe.html'


def test_split_segments_respects_quotes():
    cell = '"Works at Acme; before that at Beta", speaker page: https://a.org/p; Profile: https://github.com/x'
    assert split_segments(cell) == ['"Works at Acme; before that at Beta", speaker page: https://a.org/p',
                                    'Profile: https://github.com/x']


def test_split_segments_survives_a_quote_cut_short():
    # The migration cut long labels with "…:"; the quote it opened has no end
    cell = ('signature "Jane Doe | Owner at …: https://a.org/one ; https://a.org/two; '
            '"Jane works at Acme.", speaker page: https://a.org/three')
    assert split_segments(cell) == ['signature "Jane Doe | Owner at …: https://a.org/one', 'https://a.org/two',
                                    '"Jane works at Acme.", speaker page: https://a.org/three']


def test_parse_segment_quote_label_url():
    segment = '"He works at X.", Plone Conference 2017 speaker page: https://a.org/p'
    assert parse_segment(segment) == [Cited('https://a.org/p', ('He works at X.',),
                                            'Plone Conference 2017 speaker page')]


def test_quote_attaches_to_every_url_of_its_segment():
    segment = f'"Jane works at Acme.", Plone Conference 2017 speaker page: {SPEAKER} (archived: {ARCHIVED})'
    cited = parse_segment(segment)
    assert [c.url for c in cited] == [SPEAKER, ARCHIVED]
    assert {c.quotes for c in cited} == {('Jane works at Acme.',)}
    assert {c.label for c in cited} == {'Plone Conference 2017 speaker page'}


def test_segment_without_quote():
    assert parse_segment('example commit: https://github.com/plone/a/commit/abc.') == [
        Cited('https://github.com/plone/a/commit/abc', (), 'example commit')]
    assert parse_segment('confirmed in #90 (https://github.com/plone/x/pull/90): did no Plone projects') == [
        Cited('https://github.com/plone/x/pull/90', (), 'confirmed in #90')]
    assert parse_segment('no address here') == []


def test_every_quote_before_the_first_url_counts_and_quoted_urls_are_not_cited():
    segment = ('"Small business digital services", "Copyright 2002 Jane Doe", her own site: '
               'http://web.archive.org/web/20030919111622/http://jane.example/')
    assert parse_segment(segment) == [Cited('http://web.archive.org/web/20030919111622/http://jane.example/',
                                            ('Small business digital services', 'Copyright 2002 Jane Doe'),
                                            'her own site')]
    signature = 'signature "Acme Ltd, http://acme.example" in her messages: 2007: https://a.org/m/1'
    assert parse_segment(signature) == [Cited('https://a.org/m/1', ('Acme Ltd, http://acme.example',),
                                              'signature in her messages: 2007')]


def test_a_quote_cut_short_keeps_its_beginning():
    segment = 'signature "Jane Doe | Owner at …: https://a.org/one'
    assert parse_segment(segment) == [Cited('https://a.org/one', ('Jane Doe | Owner at',), 'signature')]
    assert parse_segment('lists "Jane Doe ... …: https://a.org/team')[0].quotes == ('Jane Doe',)


def test_quotes_of_gives_every_distinct_quote_in_order():
    assert quotes_of('"One", see https://a.org/x; "Two" and "One"; signature "Cut short …: https://a.org/y') == [
        'One', 'Two', 'Cut short']
