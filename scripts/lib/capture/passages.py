"""Find a quote in a text and cut the paragraph around it.

Pure text functions, no I/O. The repository stores only the passages it cites,
so a captured source keeps the paragraph around the quote, in the page's own
spelling. See docs/how-to/capture-a-source.md for the reasons.
"""

import re
import unicodedata

_CHAR_MAP = {
    **dict.fromkeys('‘’‚‛′', "'"),
    **dict.fromkeys('“”„″', '"'),
    **dict.fromkeys('–—‐‑−', '-'),
    '…': '...',
}
_PARAGRAPH_BREAK = re.compile(r'\n[^\S\n]*(?:\n[^\S\n]*)+')


def _normalize_with_map(text: str, offset: int = 0) -> tuple[str, list[int]]:
    """Return the normalized text and, per normalized char, its index in the original."""
    chars: list[str] = []
    index: list[int] = []
    pending_space = False
    for i, original in enumerate(text):
        for char in unicodedata.normalize('NFKC', original):
            char = _CHAR_MAP.get(char, char)
            for out in char:
                if out.isspace():
                    pending_space = True
                    continue
                if pending_space and chars:
                    chars.append(' ')
                    index.append(i + offset)
                pending_space = False
                chars.append(out)
                index.append(i + offset)
    return ''.join(chars), index


def normalize_text(text: str) -> str:
    """NFKC, straight quotes and dashes, one space per whitespace run, case kept."""
    return _normalize_with_map(text)[0]


def _paragraphs(text: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for match in _PARAGRAPH_BREAK.finditer(text):
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, len(text)))
    return spans


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Span of the quote in the original text, compared after normalization.

    A quote with ``...`` or ``…`` matches when its parts occur in order within
    one paragraph.
    """
    parts = [p.strip() for p in normalize_text(quote).split('...')]
    parts = [p for p in parts if p]
    if not parts:
        return None
    for p_start, p_end in _paragraphs(text):
        normalized, index = _normalize_with_map(text[p_start:p_end], p_start)
        first_start = None
        pos = 0
        last_end = 0
        for part in parts:
            found = normalized.find(part, pos)
            if found < 0:
                break
            if first_start is None:
                first_start = found
            pos = last_end = found + len(part)
        else:
            return index[first_start], index[last_end - 1] + 1
    return None


def cut_passage(text: str, span: tuple[int, int], limit: int = 1000) -> str:
    """The paragraph containing the span; a window around it if longer than limit."""
    start, end = span
    p_start, p_end = next(
        ((a, b) for a, b in _paragraphs(text) if a <= start < b or (a <= start <= b and a == b)),
        (0, len(text)),
    )
    # trim whitespace around the paragraph
    while p_start < p_end and text[p_start].isspace():
        p_start += 1
    while p_end > p_start and text[p_end - 1].isspace():
        p_end -= 1
    if p_end - p_start <= limit:
        return text[p_start:p_end]
    side = max(0, (limit - (end - start)) // 2)
    w_start = max(p_start, start - side)
    w_end = min(p_end, end + side)
    while w_start > p_start and not text[w_start - 1].isspace() and not text[w_start].isspace():
        w_start -= 1
    while w_end < p_end and not text[w_end].isspace() and not text[w_end - 1].isspace():
        w_end += 1
    passage = text[w_start:w_end].strip()
    if w_start > p_start:
        passage = '…' + passage
    if w_end < p_end:
        passage += '…'
    return passage
