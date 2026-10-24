#!/usr/bin/env python3
"""Fill empty snippets from the quotes in the notes, once their source is captured.

A citation or identity without a snippet often keeps the words that cited its source in its notes, as
`cited as: "…"`; when the source was not read yet, those words could not be checked. After a capture (see
docs/how-to/capture-a-source.md), this finds each double-quoted quote of the notes (a pair of `"` with at least
eight characters between them) in the excerpt of the source, compared as the capture compares a quote. A quote
right after `talk`, `titled`, `title` or `called` is a title, not evidence, and is skipped. For a citation, the
first quote found fills its snippet and every further quote found adds a citation of the same affiliation and
source with the same notes; a quote whose place in the excerpt overlaps that of a snippet the affiliation already
cites from the source (the same words in another typography, or a part of them) is not cited again. For an
identity, the first quote found fills its snippet. Sources that were never read (`not captured on …`, `could not
be fetched on …`) are skipped: their excerpt is only that note.

Without --write, it prints every change it would make, with the person, the source, the snippet and the words of
the notes before the quote. A second run changes nothing.

    python -m scripts.tools.cite_snippets [--write]
"""

import argparse
import dataclasses
import re
import sys

from scripts.lib.capture.passages import find_quote
from scripts.lib.model import (is_uncaptured, load_citations, load_identities, load_registry, load_sources,
                               read_excerpt, write_citations, write_identities)

QUOTE = re.compile(r'"([^"]*)"')
MIN_QUOTE = 8  # characters between the two `"`; a shorter pair is a name or a word, not a quote
TITLE_WORDS = ('talk', 'titled', 'title', 'called')  # before a quote, they make it a title
TITLE_WINDOW = 12  # characters before the opening `"` in which a title word counts
CONTEXT = 40  # characters of the notes before the quote that the report shows


@dataclasses.dataclass(frozen=True)
class Quote:
    text: str
    context: str  # the notes before the quote, at most CONTEXT characters


def quotes(notes):
    """The double-quoted quotes of the notes, in order: the text between each pair of `"`, stripped, at least
    MIN_QUOTE characters long, and not right after a title word."""
    notes = notes or ''
    found = []
    for match in QUOTE.finditer(notes):
        text = match.group(1).strip()
        before = notes[max(0, match.start() - TITLE_WINDOW):match.start()].casefold()
        if len(text) < MIN_QUOTE or any(word in before for word in TITLE_WORDS):
            continue
        context = notes[:match.start()].strip()
        if len(context) > CONTEXT:
            context = '…' + context[-CONTEXT:].strip()
        found.append(Quote(text, context))
    return found


def quotes_in(notes):
    """The texts of the quotes of the notes."""
    return [quote.text for quote in quotes(notes)]


@dataclasses.dataclass
class Result:
    citations: list
    identities: list
    filled: list  # (citation as it is now, Quote) of each citation whose snippet was filled
    added: list  # (citation, Quote) of each citation added
    identities_filled: list  # (identity as it is now, Quote) of each identity whose snippet was filled


class _Excerpts:
    """The places of quotes in the excerpts of the captured sources, each excerpt read once."""

    def __init__(self, sources):
        self.sources = sources
        self.texts = {}

    def span(self, source, quote):
        """(start, end) of the quote in the excerpt of the source; None when it is not there or the source was
        never read."""
        if source not in self.sources or is_uncaptured(self.sources[source]):
            return None
        if source not in self.texts:
            self.texts[source] = read_excerpt(source)
        return find_quote(self.texts[source], quote)


def _overlaps(span, spans):
    return any(span[0] < end and start < span[1] for start, end in spans)


def fill(citations, identities, sources):
    """The registers with the snippets filled from the notes; see the module docstring."""
    excerpts = _Excerpts(sources)
    cited = {}  # (affiliation, source) -> the spans of the snippets of its citations

    def spans_of(citation):
        key = (citation.affiliation, citation.source)
        if key not in cited:
            cited[key] = [span for row in citations
                          if (row.affiliation, row.source) == key and row.snippet
                          for span in [excerpts.span(row.source, row.snippet)] if span is not None]
        return cited[key]

    new_citations, filled, added = [], [], []
    for citation in citations:
        if citation.snippet:
            new_citations.append(citation)
            continue
        chosen = []
        for quote in quotes(citation.notes):
            span = excerpts.span(citation.source, quote.text)
            if span is not None and not _overlaps(span, spans_of(citation)):
                spans_of(citation).append(span)
                chosen.append(quote)
        if not chosen:
            new_citations.append(citation)
            continue
        first = dataclasses.replace(citation, snippet=chosen[0].text)
        filled.append((first, chosen[0]))
        new_citations.append(first)
        for quote in chosen[1:]:
            row = dataclasses.replace(citation, snippet=quote.text, supersedes=None)
            added.append((row, quote))
            new_citations.append(row)
    new_identities, identities_filled = [], []
    for identity in identities:
        quote = None
        if not identity.snippet and identity.source:
            quote = next((quote for quote in quotes(identity.notes)
                          if excerpts.span(identity.source, quote.text) is not None), None)
        if quote is None:
            new_identities.append(identity)
            continue
        identity = dataclasses.replace(identity, snippet=quote.text)
        identities_filled.append((identity, quote))
        new_identities.append(identity)
    return Result(new_citations, new_identities, filled, added, identities_filled)


def report(result, person_of):
    """The lines that say what the run changes: the counts, then every change. `person_of` maps an affiliation id
    to its person."""
    lines = [f'citations filled: {len(result.filled)}', f'citation rows added: {len(result.added)}',
             f'identities filled: {len(result.identities_filled)}']
    for title, rows in (('citation filled', result.filled), ('citation row added', result.added)):
        lines.extend(f'{title}: {person_of.get(row.affiliation, "?")}, {row.affiliation}, source {row.source}: '
                     f'"{row.snippet}" (after: {quote.context})' for row, quote in rows)
    lines.extend(f'identity filled: {row.person}, {row.kind} {row.value}, source {row.source}: "{row.snippet}" '
                 f'(after: {quote.context})' for row, quote in result.identities_filled)
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true', help='write the snippets and rows (default: a dry run)')
    args = parser.parse_args(argv)
    result = fill(load_citations(), load_identities(), load_sources())
    person_of = {affiliation.id: affiliation.person for affiliation in load_registry().affiliations}
    for line in report(result, person_of):
        print(line)
    if not args.write:
        print('dry run: nothing written; use --write to write')
        return 0
    if result.filled or result.added:
        write_citations(result.citations)
    if result.identities_filled:
        write_identities(result.identities)
    return 0


if __name__ == '__main__':
    sys.exit(main())
