#!/usr/bin/env python3
"""Capture a source once: its row in curated/sources/sources.csv and the passages around the given quotes.

Needs GITHUB_TOKEN in the environment for GitHub profiles, commits, issues, pull requests and comments.
See docs/how-to/capture-a-source.md.
"""

import argparse
import datetime
import json
import pathlib
import sys

from scripts.lib.capture import CaptureError, Fetcher, capture, github_session
from scripts.lib.model import load_sources
from scripts.lib.model.sources import SOURCE_KINDS


def main(argv=None):
    parser = argparse.ArgumentParser(description='Capture a source: its row in the source register and the '
                                                 'passages around the given quotes.')
    parser.add_argument('url', nargs='?', help='address of the page, a Wayback address is kept as it is')
    parser.add_argument('--quote', action='append', metavar='TEXT',
                        help='text to cite, as it stands on the page; repeat for several quotes')
    parser.add_argument('--name', action='append', default=[], metavar='TEXT',
                        help='a name to find when no quote is given or found: stores the passage around its '
                             'first occurrence; repeat for several names')
    parser.add_argument('--kind', choices=SOURCE_KINDS, help='kind of source, default: guessed from the address')
    parser.add_argument('--title', help='title, default: the title of the page')
    parser.add_argument('--date', type=datetime.date.fromisoformat, metavar='YYYY-MM-DD',
                        help='date of the source, default: the date of the page or the capture')
    parser.add_argument('--refresh', action='store_true', help='fetch the page again')
    parser.add_argument('--batch', type=pathlib.Path, metavar='WORKLIST',
                        help='capture every source of a JSON lines work list in one resumable run; needs --results')
    parser.add_argument('--results', type=pathlib.Path, metavar='RESULTS',
                        help='JSON lines file the results are appended to; sources already in it are skipped')
    args = parser.parse_args(argv)
    if bool(args.batch) != bool(args.results):
        parser.error('--batch and --results go together')
    if args.batch:
        if args.url or args.quote or args.name or args.kind or args.title or args.date or args.refresh:
            parser.error('--batch takes no address, --quote, --name, --kind, --title, --date or --refresh')
        return run_batch(args.batch, args.results)
    if not args.url:
        parser.error('give the address of the source')
    if not args.quote and not args.name:
        parser.error('give at least one --quote or --name')
    try:
        result = capture(args.url, quotes=args.quote or (), names=args.name, kind=args.kind, title=args.title,
                         date=args.date, refresh=args.refresh)
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


def _read_results(path):
    """The addresses already in the results file; a line that does not parse (an interrupted write) is ignored."""
    done = set()
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                done.add(json.loads(line)['url'])
            except (ValueError, KeyError, TypeError):
                pass
    return done


def _recorded(sid):
    """True when the source is in the register (read once while the file is unchanged)."""
    try:
        return sid in load_sources()
    except FileNotFoundError:
        return False


def run_batch(worklist, results_path):
    """Capture the sources of a work list, appending one result line each; return 0 when the end is reached.

    A result names its source only when the source is in the register: a new source none of whose quotes or
    names was found is not recorded, and its `source_id` is null. Any error of one source is recorded in its
    result, and the run goes on.
    """
    items = [json.loads(line) for line in worklist.read_text(encoding='utf-8').splitlines() if line.strip()]
    done = _read_results(results_path)
    todo = [item for item in items if item['url'] not in done]
    fetcher, session = Fetcher(), github_session()
    created = missing = errors = 0
    with results_path.open('a', encoding='utf-8') as out:
        if out.tell():  # an interrupted write leaves no newline; keep the next result on its own line
            with results_path.open('rb') as existing:
                existing.seek(-1, 2)
                if existing.read(1) != b'\n':
                    out.write('\n')
        for count, item in enumerate(todo, 1):
            url = item['url']
            error = None
            try:
                result = capture(url, quotes=item.get('quotes') or (), kind=item.get('kind'),
                                 names=item.get('names') or (), fetcher=fetcher, session=session)
            except CaptureError as caught:
                error = str(caught)
            except Exception as caught:  # one bad item must not stop the run, nor every resume after it
                error = f'unexpected: {type(caught).__name__}: {caught}'
            if error is None:
                row = {'url': url, 'source_id': result.source_id if _recorded(result.source_id) else None,
                       'created': result.created, 'added': list(result.added), 'missing': list(result.missing),
                       'unreachable': result.unreachable, 'error': None}
            else:
                row = {'url': url, 'source_id': None, 'created': False, 'added': [], 'missing': [],
                       'unreachable': False, 'error': error}
            created += row['created']
            missing += bool(row['missing'])
            errors += row['error'] is not None
            out.write(json.dumps(row, ensure_ascii=False) + '\n')
            out.flush()
            if count % 25 == 0:
                print(f'{count}/{len(todo)}  {created} new, {missing} with missing quotes, {errors} errors',
                      file=sys.stderr)
    return 0

if __name__ == '__main__':
    sys.exit(main())
