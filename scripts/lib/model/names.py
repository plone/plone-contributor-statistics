"""The two text normalisations of the code base."""

import re
import unicodedata


def _strip_marks(text):
    """The text in decomposed form, without combining marks such as accents."""
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in decomposed if not unicodedata.combining(char))


def fold(text):
    """The text as a comparison key: accents, punctuation and case removed, whitespace collapsed.

    fold('Ecréall ') == fold('ecreall').
    """
    text = _strip_marks(text)
    text = ''.join(char if char.isalnum() or char.isspace() else '' for char in text)
    return ' '.join(text.casefold().split())


def slugify(text):
    """The text as an identifier made of lower-case ASCII letters, digits and hyphens."""
    text = _strip_marks(text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def unique_slug(text, taken):
    """The slug of the text, or slug-2, slug-3 when it is in `taken`; ValueError when the text gives no slug."""
    base = slugify(text)
    if not base:
        raise ValueError(f'"{text}" gives no id')
    candidate, number = base, 1
    while candidate in taken:
        number += 1
        candidate = f'{base}-{number}'
    return candidate
