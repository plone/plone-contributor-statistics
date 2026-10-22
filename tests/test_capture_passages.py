from scripts.lib.capture.passages import cut_passage, find_quote, normalize_text

TEXT = 'Intro.\n\nMaurits has been a Plone programmer for Zest Software since 2005.\nMore.\n\nOutro.'


def test_normalize_text():
    assert normalize_text('  a  b\n\tc “x” ‘y’ – … ') == 'a b c "x" \'y\' - ...'


def test_find_quote_normalizes():
    span = find_quote(TEXT, 'has been a Plone programmer for Zest Software since 2005')
    assert TEXT[span[0]:span[1]] == 'has been a Plone programmer for Zest Software since 2005'
    assert find_quote('He said “Nowadays” – ok', '"Nowadays" - ok') is not None
    assert find_quote(TEXT, 'Zest Software since 2006') is None


def test_find_quote_across_line_break_and_nbsp():
    text = 'A Plone\nprogrammer for Zest'
    span = find_quote(text, 'Plone programmer for Zest')
    assert text[span[0]:span[1]] == 'Plone\nprogrammer for Zest'


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
