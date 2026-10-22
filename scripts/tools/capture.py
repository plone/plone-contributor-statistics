#!/usr/bin/env python3
"""Capture a source once: its row in curated/sources/sources.csv and the passages around the given quotes.

Needs GITHUB_TOKEN in the environment for GitHub profiles and commits. See docs/how-to/capture-a-source.md.
"""

import argparse
import datetime
import sys

from scripts.lib.capture import CaptureError, capture
from scripts.lib.model.sources import SOURCE_KINDS


def main(argv=None):
    parser = argparse.ArgumentParser(description='Capture a source: its row in the source register and the '
                                                 'passages around the given quotes.')
    parser.add_argument('url', help='address of the page, a Wayback address is kept as it is')
    parser.add_argument('--quote', action='append', metavar='TEXT',
                        help='text to cite, as it stands on the page; repeat for several quotes')
    parser.add_argument('--name', action='append', default=[], metavar='TEXT',
                        help='a name to find instead of a quote: stores the passage around its first '
                             'occurrence; repeat for several names, ignored when a quote is given')
    parser.add_argument('--kind', choices=SOURCE_KINDS, help='kind of source, default: guessed from the address')
    parser.add_argument('--title', help='title, default: the title of the page')
    parser.add_argument('--date', type=datetime.date.fromisoformat, metavar='YYYY-MM-DD',
                        help='date of the source, default: the date of the page or the capture')
    parser.add_argument('--refresh', action='store_true', help='fetch the page again')
    args = parser.parse_args(argv)
    if not args.quote and not args.name:
        parser.error('give at least one --quote or --name')
    try:
        result = capture(args.url, quotes=args.quote or (), names=args.name, kind=args.kind, title=args.title, date=args.date,
                         refresh=args.refresh)
    except CaptureError as error:
        print(f'! {error}', file=sys.stderr)
        return 1
    print(f'{result.source_id}  {args.url}')
    for passage in result.added:
        print(f'+ {passage[:80]}')
    for missing in result.missing:
        print(f'! not found: {missing}')
    if result.unreachable:
        print('! unreachable')
    return 1 if result.missing or result.unreachable else 0


if __name__ == '__main__':
    sys.exit(main())
