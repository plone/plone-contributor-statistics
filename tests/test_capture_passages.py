import pytest

from scripts.lib.capture.passages import cut_passage, find_name, find_quote, normalize_text

TEXT = 'Intro.\n\nMaurits has been a Plone programmer for Zest Software since 2005.\nMore.\n\nOutro.'


def test_normalize_text():
    assert normalize_text('  a  b\n\tc “x” ‘y’ – … ') == 'a b c "x" \'y\' - ...'


def test_find_quote_normalizes():
    span = find_quote(TEXT, 'has been a Plone programmer for Zest Software since 2005')
    assert TEXT[span[0]:span[1]] == 'has been a Plone programmer for Zest Software since 2005'
    assert find_quote('He said “Nowadays” – ok', '"Nowadays" - ok') is not None
    assert find_quote(TEXT, 'Zest Software since 2006') is None


def test_find_quote_across_line_break_and_nbsp():
    text = 'A Plone\nprogrammer\u00a0for Zest'
    span = find_quote(text, 'Plone programmer for Zest')
    assert text[span[0]:span[1]] == 'Plone\nprogrammer\u00a0for Zest'


COMPOSED = 'Jyv\u00e4skyl\u00e4'
DECOMPOSED = 'Jyva\u0308skyla\u0308'


def test_find_quote_decomposed_text_composed_quote():
    """pdftotext writes accents as combining marks; a quote typed with composed letters must still match."""
    text = f'He lives in {DECOMPOSED} now.'
    span = find_quote(text, COMPOSED)
    assert text[span[0]:span[1]] == DECOMPOSED
    span = find_quote(text, f'in {COMPOSED} now')
    assert text[span[0]:span[1]] == f'in {DECOMPOSED} now'


def test_find_quote_composed_text_decomposed_quote():
    text = f'He lives in {COMPOSED} now.'
    span = find_quote(text, DECOMPOSED)
    assert text[span[0]:span[1]] == COMPOSED


@pytest.mark.parametrize('text, quote, expected', [
    ('So the \ufb01nal release came.', 'the final release', 'the \ufb01nal release'),
    ('It was\u2026 done, he said.', 'was... done', 'was\u2026 done'),
    ('He said \u201cNowadays\u201d and left.', '"Nowadays" and', '\u201cNowadays\u201d and'),
    ('A \ufb01 B', '\ufb01', '\ufb01'),
    ('the last word is \ufb01', 'is fi', 'is \ufb01'),
    ('Add \u00bd cup.', '1\u20442 cup', '\u00bd cup'),
])
def test_find_quote_span_is_exact_when_normalization_changes_length(text, quote, expected):
    span = find_quote(text, quote)
    assert text[span[0]:span[1]] == expected


def test_find_quote_is_case_sensitive():
    assert find_quote(TEXT, 'zest software') is None


def test_find_quote_with_ellipsis():
    span = find_quote(TEXT, 'Maurits has been … since 2005')
    assert TEXT[span[0]:span[1]].startswith('Maurits') and TEXT[span[0]:span[1]].endswith('2005')
    assert find_quote(TEXT, 'Maurits has been ... since 2005') == span
    assert find_quote(TEXT, 'Intro … Outro') is None  # parts in different paragraphs
    assert find_quote(TEXT, 'since 2005 … Maurits') is None  # wrong order


def test_cut_passage_returns_the_paragraph():
    span = find_quote(TEXT, 'since 2005')
    assert cut_passage(TEXT, span) == 'Maurits has been a Plone programmer for Zest Software since 2005.\nMore.'


def test_cut_passage_windows_a_long_paragraph():
    long = ' '.join(['word'] * 600) + ' QUOTE HERE ' + ' '.join(['word'] * 600)
    passage = cut_passage(long, find_quote(long, 'QUOTE HERE'), limit=200)
    assert 'QUOTE HERE' in passage and len(passage) <= 210
    assert passage.startswith('…') and passage.endswith('…')


def test_find_name_ignores_case_and_accents():
    text = 'Intro.\n\nThe sprint was held in Jyväskylä with Annette and Ann.'
    span = find_name(text, 'jyvaskyla')
    assert text[span[0]:span[1]] == 'Jyväskylä'
    span = find_name(text, 'ann')
    assert text[span[0]:span[1]] == 'Ann'
    assert text.index('Ann.') == span[0]  # not the one inside Annette
    assert find_name('Annette only', 'Ann') is None
    assert find_name('anything', '  ') is None


def test_find_name_maps_decomposed_text_back_whole():
    text = 'Müller wrote this'
    span = find_name(text, 'muller')
    assert text[span[0]:span[1]] == 'Müller'
