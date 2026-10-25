#!/usr/bin/env python3
"""The work list of the sources the community files cite, for `python -m scripts.tools.capture --batch`.

Migration code for plan 3b, which captures the sources of the curated community data: it is archived to archive/
after its last use.

It reads every `source` cell of the community files (not the `video` column, not `notes`) through the model and
splits it into segments and addresses (scripts.lib.cells). The work list has one item per distinct address:
`{url, quotes, names, kind}`. The quotes are those of the address's own segment, then every other quote of its cell
(the capture keeps only the quotes it finds in a source). The names are the display names and `name` identities
of the people of the row (speakers, trainers, organisers, person) and the names and aliases of its organisations,
to look for when no quote is found. The kind is `video` for the video hosts and `speaker-page` when the label says
speaker page, else None: the capture adapters decide then. Addresses that are in the source register are listed
too; the batch mode makes no request for those whose quotes are stored.
"""

import argparse
import json
import re
import sys

from scripts.lib.cells import add_new, parse_segment, quotes_of, split_segments
from scripts.lib.model import (ROLE_KINDS, community_folder, community_years, items, load_registry, load_sources,
                               normalize_url)
from scripts.lib.model.community import VIDEO_HOSTS

# The kinds of rows with a source cell, in the order of the yearly files they came from
KINDS = tuple(sorted((*ROLE_KINDS, 'world-plone-day-event')))


def is_video(url):
    """Whether the address is on a video host (a playlist or channel page too: the capture refuses it)."""
    parts = re.match(r'https?://([^/?#:]+)', url.strip(), re.IGNORECASE)
    host = parts.group(1).lower() if parts else ''
    return any(host == h or host.endswith('.' + h) for h in VIDEO_HOSTS)


def kind_hint(url, label):
    """`video` for a video host, `speaker-page` when the label names one, else None."""
    if is_video(url):
        return 'video'
    return 'speaker-page' if 'speaker page' in label.casefold() else None


def _names(registry, item):
    names = []
    for person_id in item.people:
        person = registry.people.get(person_id)
        if person:
            add_new(names, [person.name])
        add_new(names, [i.value for i in registry.identities if i.person == person_id and i.kind == 'name'])
    for organisation_id in item.organisations:
        organisation = registry.organisations.get(organisation_id)
        if organisation:
            add_new(names, [organisation.name, *organisation.aliases])
    return names


def work_list(registry=None, community_dir=None):
    """One item {url, quotes, names, kind} per distinct address of the source cells, sorted by address."""
    registry = registry or load_registry()
    folder = community_folder(community_dir)
    found = {}
    for year, kind in ((year, kind) for year in community_years(folder) for kind in KINDS):
        for item in items(year, kind, folder):
            names = _names(registry, item)
            pool = quotes_of(item.source)
            for segment in split_segments(item.source):
                for cited in parse_segment(segment):
                    quotes = list(cited.quotes)
                    add_new(quotes, pool)
                    entry = found.setdefault(cited.url, {'url': cited.url, 'quotes': [], 'names': [], 'kind': None})
                    add_new(entry['quotes'], quotes)
                    add_new(entry['names'], names)
                    entry['kind'] = entry['kind'] or kind_hint(cited.url, cited.label)
    return [found[url] for url in sorted(found)]


def registered(urls):
    """The addresses of the list that the source register holds."""
    try:
        known = {normalize_url(source.url) for source in load_sources().values()}
    except FileNotFoundError:
        known = set()
    return [url for url in urls if normalize_url(url) in known]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Write the work list of the sources the community files cite.')
    parser.add_argument('--worklist', required=True, metavar='PATH', help='JSON lines file of the work list')
    only = parser.add_mutually_exclusive_group()
    only.add_argument('--videos-only', action='store_true', help='list only the addresses on video hosts')
    only.add_argument('--no-videos', action='store_true', help='list only the addresses that are no videos')
    args = parser.parse_args(argv)
    everything = work_list()
    chosen = [item for item in everything
              if not (args.videos_only and item['kind'] != 'video') and not (args.no_videos and item['kind'] == 'video')]
    with open(args.worklist, 'w', encoding='utf-8') as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + '\n' for item in chosen)
    print(f'{len(chosen)} items, {sum(item["kind"] == "video" for item in chosen)} videos, '
          f'{len(registered(item["url"] for item in chosen))} already registered')
    return 0


if __name__ == '__main__':
    sys.exit(main())
