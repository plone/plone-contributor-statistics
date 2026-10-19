#!/usr/bin/env python3
"""Render the community page from derived/community-page.json.

Writes a static page with Jinja2 into a folder (default: _site); make site also
builds the docs into its docs/ folder. The page loads nothing from other sites.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from scripts.lib import paths

SITE = Path(__file__).parent / 'site'
REPOSITORY = 'https://github.com/plone/plone-contributor-statistics'
URL = re.compile(r'https?://[^\s;,)"\'<>]+')
# The buckets of the anonymous distributions in the People tab: (label, lowest, highest)
BUCKETS = [('1', 1, 1), ('2–9', 2, 9), ('10–49', 10, 49), ('50+', 50, None)]
# The areas of an organisation's yearly contribution graph
AREAS = [('commits', 'Commits'), ('pull_requests', 'Merged pull requests'), ('roles', 'Community roles'),
         ('events', 'Events')]


def number(value):
    return f'{value:,}'


def points(value):
    """Points without trailing zeros: 12, 1.5, 0.86."""
    return f'{value:.2f}'.rstrip('0').rstrip('.')


def links(source):
    """The URLs in a source cell, which can hold several, e.g. "https://…; Board: https://…"."""
    return URL.findall(source or '')


def host(url):
    return re.sub(r'^https?://(www\.)?', '', url).split('/')[0]


def labelled_links(source):
    """The URLs of a source cell with a label each: the host, numbered when a host repeats."""
    seen = {}
    labelled = []
    for url in links(source):
        name = host(url)
        seen[name] = seen.get(name, 0) + 1
        labelled.append((url, name if seen[name] == 1 else f'{name} ({seen[name]})'))
    return labelled


def data_link(file, line=None):
    """A link to a data file, or one of its rows, on GitHub."""
    if line:
        return f'{REPOSITORY}/blob/main/{file}#L{line}'
    kind = 'blob' if Path(file).suffix else 'tree'
    return f'{REPOSITORY}/{kind}/main/{file}'


def bars(history, years, area, width=4, gap=1, height=28):
    """The bars of a small graph: one per year, scaled to the largest value of the area."""
    values = [history.get(str(year), {}).get(area, 0) for year in years]
    highest = max(values) or 1
    return [{'x': index * (width + gap), 'height': round(value / highest * height, 1), 'year': year,
             'value': value} for index, (year, value) in enumerate(zip(years, values))]


def distribution(people, field):
    """How many people fall into each bucket of a field, e.g. merged pull requests."""
    return [sum(1 for p in people if p[field] >= low and (high is None or p[field] <= high))
            for _, low, high in BUCKETS]


def environment():
    env = Environment(loader=FileSystemLoader(SITE / 'templates'), autoescape=select_autoescape(['html']),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(number=number, points=points, links=labelled_links)
    env.globals.update(data_link=data_link, bars=bars, areas=AREAS, repository=REPOSITORY, buckets=BUCKETS,
                       distribution=distribution)
    return env


def render(data, out_dir, docs_url='docs/'):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # The people data feeds the search; "</" must not end the script element
    people = json.dumps({'years': data['people'], 'names': data.get('people_names', {})},
                        separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    years = sorted(int(year) for year in data['history'])
    html = environment().get_template('index.html').render(
        data=data, docs_url=docs_url, history_years=years, people_json=Markup(people),
        data_url=data_link(str(paths.COMMUNITY_PAGE)))
    (out_dir / 'index.html').write_text(html, encoding='utf-8')
    shutil.copytree(SITE / 'static', out_dir / 'static', dirs_exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Render the community page from derived/community-page.json')
    parser.add_argument('--out', default='_site', help='Folder to write the page to (default: _site)')
    args = parser.parse_args()
    render(json.loads(paths.COMMUNITY_PAGE.read_text(encoding='utf-8')), Path(args.out))
    print(f'Wrote {args.out}/index.html')


if __name__ == '__main__':
    main()
