#!/usr/bin/env python3
"""Fill empty snippets from the quotes in the notes, once their source is captured.

A citation or identity without a snippet often keeps the words that cited its source in its notes, as
`cited as: "…"`; when the source was not read yet, those words could not be checked. After a capture (see
docs/how-to/capture-a-source.md), this finds each double-quoted quote of the notes (a pair of `"` with at least
eight characters between them) in the excerpt of the source, compared as the capture compares a quote. For a
citation, the first quote found fills its snippet and every further quote found adds a citation of the same
affiliation and source with the same notes; a quote that a citation of the affiliation and source has as its
snippet already is not cited again. For an identity, the first quote found fills its snippet. Sources that were
never read (`not captured on …`, `could not be fetched on …`) are skipped: their excerpt is only that note.

Without --write, it prints what it would change. A second run changes nothing.

    python -m scripts.tools.cite_snippets [--write]
"""

import argparse
import dataclasses
import re
import sys

from scripts.lib.capture.passages import find_quote
from scripts.lib.model import (is_uncaptured, load_citations, load_identities, load_sources, read_excerpt,
                               write_citations, write_identities)

QUOTE = re.compile(r'"([^"]*)"')
MIN_QUOTE = 8  # characters between the two `"`; a shorter pair is a name or a word, not a quote
EXAMPLES = 5


def quotes_in(notes):
    """The double-quoted quotes of the notes, in order: the text between each pair of `"`, stripped, at least
    MIN_QUOTE characters long."""
    quotes = (match.strip() for match in QUOTE.findall(notes or ''))
    return [quote for quote in quotes if len(quote) >= MIN_QUOTE]


@dataclasses.dataclass
class Result:
    citations: list
    identities: list
    filled: list  # the citations whose snippet was filled, as they are now
    added: list  # the citations added
    identities_filled: list  # the identities whose snippet was filled, as they are now


def _excerpts(sources):
    """found(source id, quote): whether the quote is in the excerpt of a captured source."""
    cache = {}

    def found(source, quote):
        if source not in sources or is_uncaptured(sources[source]):
            return False
        if source not in cache:
            cache[source] = read_excerpt(source)
        return find_quote(cache[source], quote) is not None
    return found


def fill(citations, identities, sources):
    """The registers with the snippets filled from the notes; see the module docstring."""
    found = _excerpts(sources)
    cited = {}  # (affiliation, source) -> the snippets of its citations
    for citation in citations:
        if citation.snippet:
            cited.setdefault((citation.affiliation, citation.source), set()).add(citation.snippet)
    new_citations, filled, added = [], [], []
    for citation in citations:
        if citation.snippet:
            new_citations.append(citation)
            continue
        snippets = cited.setdefault((citation.affiliation, citation.source), set())
        quotes = []
        for quote in quotes_in(citation.notes):
            if quote not in snippets and quote not in quotes and found(citation.source, quote):
                quotes.append(quote)
        if not quotes:
            new_citations.append(citation)
            continue
        snippets.update(quotes)
        first = dataclasses.replace(citation, snippet=quotes[0])
        filled.append(first)
        new_citations.append(first)
        for quote in quotes[1:]:
            row = dataclasses.replace(citation, snippet=quote, supersedes=None)
            added.append(row)
            new_citations.append(row)
    new_identities, identities_filled = [], []
    for identity in identities:
        quote = None
        if not identity.snippet and identity.source:
            quote = next((quote for quote in quotes_in(identity.notes) if found(identity.source, quote)), None)
        if quote is None:
            new_identities.append(identity)
            continue
        identity = dataclasses.replace(identity, snippet=quote)
        identities_filled.append(identity)
        new_identities.append(identity)
    return Result(new_citations, new_identities, filled, added, identities_filled)


def report(result):
    """The lines that say what the run changes, with a few examples of each."""
    lines = [f'citations filled: {len(result.filled)}', f'citation rows added: {len(result.added)}',
             f'identities filled: {len(result.identities_filled)}']
    for title, rows, who in (('citations filled', result.filled, 'affiliation'),
                             ('citation rows added', result.added, 'affiliation'),
                             ('identities filled', result.identities_filled, 'person')):
        if rows:
            lines.append(f'{title}, for example:')
            lines.extend(f'  {getattr(row, who)} {row.source}: "{row.snippet}"' for row in rows[:EXAMPLES])
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true', help='write the snippets and rows (default: a dry run)')
    args = parser.parse_args(argv)
    result = fill(load_citations(), load_identities(), load_sources())
    for line in report(result):
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
