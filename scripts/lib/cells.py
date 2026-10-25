"""Parse a free-text source cell into the addresses it cites, each with its quotes and label.

A cell holds segments separated by "; " outside double quotes. A segment holds quotes, a label and one or more
addresses. Every address gets the quotes that stand in front of the first address of its segment. Copied from the
migration to citations (archive/migration-to-citations/cited_sources.py) and kept unchanged in behaviour.
"""

import dataclasses
import re

URL = re.compile(r'https?://[^\s;"<>]+')
QUOTE_MARK = re.compile(r'(?<!\\)"')  # a backslash-escaped quote mark is part of the quote
SEGMENT_END = re.compile(r';\s')
CUT_SHORT = '…:'  # the migration cut long labels with "…:", which leaves a quote without its end


@dataclasses.dataclass(frozen=True)
class Cited:
    """An address cited in a segment, with the quotes in front of the segment's first address and its label."""
    url: str
    quotes: tuple[str, ...]
    label: str


def _quote_spans(text):
    """(start, end, quote) of each quoted passage of the text; the span includes the quote marks.

    A quote mark pairs with the next one, unless the text up to there holds "…:": then the migration cut the
    quote short, and the quote is its text up to the "…", the span ending with it. A last unpaired quote mark
    that is not cut short is no quote mark.
    """
    marks = [match.start() for match in QUOTE_MARK.finditer(text)]
    spans, index = [], 0
    while index < len(marks):
        start = marks[index]
        end = marks[index + 1] if index + 1 < len(marks) else len(text)
        cut = text.find(CUT_SHORT, start, end)
        if cut != -1:
            spans.append((start, cut + 1, _clean(text[start + 1:cut]).rstrip(' .…')))
            index += 1
        elif index + 1 < len(marks):
            spans.append((start, end + 1, _clean(text[start + 1:end])))
            index += 2
        else:
            break
    return spans


def _clean(quote):
    return quote.replace('\\"', '"').strip()


def _inside(position, spans):
    return any(start <= position < end for start, end, _ in spans)


def quotes_of(text):
    """Every quote of the text, distinct, in order."""
    quotes = []
    add_new(quotes, [quote for _, _, quote in _quote_spans(text) if quote])
    return quotes


def split_segments(cell: str) -> list[str]:
    """The segments of a cell: its parts between a semicolon and whitespace, outside double quotes."""
    spans = _quote_spans(cell)
    segments, start = [], 0
    for match in SEGMENT_END.finditer(cell):
        if not _inside(match.start(), spans):
            segments.append(cell[start:match.start()])
            start = match.end()
    segments.append(cell[start:])
    return [segment.strip() for segment in segments if segment.strip()]


def _trim(url):
    """The address without the punctuation of the sentence around it."""
    while url and (url[-1] in '.,:' or (url[-1] == ')' and url.count('(') < url.count(')'))):
        url = url[:-1]
    return url


def parse_segment(segment: str) -> list[Cited]:
    """Every address of the segment that stands outside quotes, each with the segment's quotes and label.

    The quotes are those that end before the first address; the label is the rest of the text before it.
    """
    spans = _quote_spans(segment)
    found = [(match.start(), _trim(match.group())) for match in URL.finditer(segment)
             if not _inside(match.start(), spans)]
    if not found:
        return []
    first = found[0][0]
    quotes = []
    add_new(quotes, [quote for _, end, quote in spans if end <= first and quote])
    outside, position = [], 0
    for start, end, _ in spans:
        if end <= first:
            outside.append(segment[position:start])
            position = end
    outside.append(segment[position:first])
    label = re.sub(r'\s+', ' ', ' '.join(outside)).strip(' :,;').rstrip(' (:,;').lstrip(' ):,;')
    return [Cited(url, tuple(quotes), label) for _, url in found]


def add_new(values, new):
    """Append to the list each of the new values it does not hold yet."""
    for value in new:
        if value not in values:
            values.append(value)

