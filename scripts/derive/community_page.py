#!/usr/bin/env python3
"""Derive the data of the community page into derived/community-page.json.

Every number the page shows is computed here from committed data; the page only
renders this file. The definitions are explained in
docs/explanation/community-page.md.
"""

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict

from scripts.lib import community, paths, people
from scripts.lib.mappings import organisation_names
from scripts.lib.years import RECOGNITION_YEAR
from scripts.report import generate_community_recognition_report as recognition

FIRST_YEAR = 2003
# Not organisations for "organisations active": unmapped people and individuals
NOT_ORGANISATIONS = {'', recognition.UNMAPPED, 'Plone Foundation (community volunteer)'}


def slug(name):
    plain = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', plain.lower()).strip('-')


def is_organisation(name):
    return name not in NOT_ORGANISATIONS and not name.endswith('(independent)')


def read_rows(path):
    if not path.exists():
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def code_work(year):
    """(username, commits, pull requests) of everyone with code work in the year."""
    for row in read_rows(paths.contributors_file(year)):
        commits, pulls = int(row['total_commits']), int(row['total_pull_requests'])
        if commits or pulls:
            yield row['username'], commits, pulls


def organisation_code_work(year):
    """(organisation, commits, pull requests) per organisation with code work in the year."""
    for row in read_rows(paths.organisation_contributors_file(year)):
        commits, pulls = int(row['total_commits']), int(row['total_pull_requests'])
        if commits or pulls:
            yield row['organisation'], commits, pulls


def code_key(index, username):
    # Commit authors without a GitHub account are recorded by name
    return index.key(name=username) if ' ' in username else username.casefold()


def people_of_year(year, index, records):
    found = defaultdict(lambda: {'commits': 0, 'pull_requests': 0, 'roles': set()})
    for username, commits, pulls in code_work(year):
        key = code_key(index, username)
        if key is None:
            continue
        person = found[key]
        person['commits'] += commits
        person['pull_requests'] += pulls
    for record in records:
        key = index.key(record.person, record.handle, community.split(record.organisation))
        if key:
            found[key]['roles'].add(record.label)
    return [{'id': key, 'commits': value['commits'], 'pull_requests': value['pull_requests'],
             'roles': sorted(value['roles'])} for key, value in sorted(found.items())]


def organisations_of_year(year, records, events):
    found = {organisation for organisation, _, _ in organisation_code_work(year)}
    found.update(o for record in records for o in community.split(record.organisation))
    found.update(o for event in events for o in event.organisations)
    return {o for o in found if is_organisation(o)}


def event_data(event):
    return {'kind': event.kind, 'name': event.name, 'level': event.level,
            'organisations': [o for o in event.organisations if o != recognition.UNMAPPED],
            'sources': list(event.sources)}


def merged(contributions):
    """Equal contributions as one, e.g. a training whose organisation cell names one organisation twice."""
    points = {}
    for c in contributions:
        key = (c.text, c.file, c.line, c.source, c.rows)
        points[key] = points.get(key, 0) + c.points
    merged = []
    for (text, file, line, source, rows), value in points.items():
        contribution = {'text': text, 'points': rounded(value), 'file': file, 'line': line, 'source': source}
        if rows:
            contribution['rows'] = [[label, str(path), row] for label, path, row in rows]
        merged.append(contribution)
    return merged


def levels_data(levels):
    return [{'name': level['name'], 'min': level['min_points'],
             'max': None if level['max_points'] == float('inf') else level['max_points']} for level in levels]


def rounded(points):
    return round(points, 4)


def organisation_data(name, categories, found, levels, history_years, per_year):
    total = sum(categories.values())
    level = recognition.get_recognition_level(total, levels)
    higher = [lvl for lvl in levels if lvl['min_points'] > total]
    next_level = min(higher, key=lambda lvl: lvl['min_points']) if higher else None
    return {
        'name': name,
        'level': level,
        'points': rounded(total),
        'next_level': next_level['name'] if next_level else None,
        'points_to_next': rounded(next_level['min_points'] - total) if next_level else None,
        'categories': {
            category: {
                'points': rounded(points),
                'contributions': merged(found.get(category, [])),
            } for category, points in sorted(categories.items())},
        'history': {str(year): per_year[year].get(name, {'commits': 0, 'pull_requests': 0, 'roles': 0, 'events': 0})
                    for year in history_years},
    }


def organisation_history(year, records, events):
    """Yearly counts per organisation: commits, merged pull requests, roles and events."""
    found = defaultdict(lambda: {'commits': 0, 'pull_requests': 0, 'roles': 0, 'events': 0})
    for organisation, commits, pulls in organisation_code_work(year):
        found[organisation]['commits'] += commits
        found[organisation]['pull_requests'] += pulls
    for record in records:
        for organisation in community.split(record.organisation):
            found[organisation]['roles'] += 1
    for event in events:
        for organisation in event.organisations:
            found[organisation]['events'] += 1
    return found


def history_of_year(year, people_list, records, events):
    commits = sum(c for _, c, _ in code_work(year))
    pulls = sum(p for _, _, p in code_work(year))
    return {
        'people_active': len(people_list),
        'commits': commits,
        # Plone moved to GitHub around 2010: earlier years have no pull requests at all
        'pull_requests': pulls or None,
        'board': [{'name': r.person, 'organisation': r.organisation, 'source': r.source or None}
                  for r in records if r.kind == 'board-of-directors'],
        'team_leads': [{'name': r.person, 'team': r.detail, 'organisation': r.organisation,
                        'source': r.source or None} for r in records if r.kind == 'team-leaders'],
        'events': [event_data(event) for event in events],
    }


def build_page_data(year=RECOGNITION_YEAR):
    all_years = list(range(FIRST_YEAR, year + 1))
    window = list(recognition.five_years(year))
    records = {y: community.community_records(y) for y in all_years}
    events = {y: community.events(y) for y in all_years}
    index = people.build_person_index([r for y in all_years for r in records[y]],
                                      organisations=set(organisation_names().values()))

    per_person = {y: people_of_year(y, index, records[y]) for y in all_years}
    per_organisation = {y: organisation_history(y, records[y], events[y]) for y in all_years}

    found = {}
    org_points, _ = recognition.calculate_community_recognition_points(year=year, contributions=found)
    levels = recognition.load_recognition_levels()
    organisations = {}
    wall = defaultdict(list)
    for name in sorted(org_points, key=str.casefold):
        data = organisation_data(name, org_points[name], found.get(name, {}), levels, all_years, per_organisation)
        if data['level'] == 'No Level':
            continue
        organisations[slug(name)] = data
        wall[data['level']].append({'name': name, 'slug': slug(name), 'points': data['points']})

    def people_in(years_):
        return len({p['id'] for y in years_ for p in per_person[y]})

    def organisations_in(years_):
        return len(set().union(*(organisations_of_year(y, records[y], events[y]) for y in years_)))

    return {
        'year': year,
        'years': window,
        'headline': {
            'year': {'people': people_in([year]), 'organisations': organisations_in([year]),
                     'events': len(events[year])},
            'five_years': {'people': people_in(window), 'organisations': organisations_in(window),
                           'events': sum(len(events[y]) for y in window)},
            'since_2003': {'people': people_in(all_years)},
        },
        'levels': levels_data(levels),
        'wall': [{'level': level['name'], 'organisations': wall[level['name']]}
                 for level in sorted(levels, key=lambda lvl: -lvl['min_points']) if wall[level['name']]],
        'organisations': organisations,
        'people': {str(y): per_person[y] for y in all_years},
        # Names in the community data that the data links to a login, for the people search
        'people_names': {name: login for name, login in sorted(index.logins_by_name.items())
                         if name in {people.normalise(r.person) for y in all_years for r in records[y]}},
        'history': {str(y): history_of_year(y, per_person[y], records[y], events[y]) for y in all_years},
    }


def main():
    parser = argparse.ArgumentParser(description='Derive the data of the community page')
    parser.add_argument('--year', type=int, default=RECOGNITION_YEAR,
                        help=f'Recognition year (default: {RECOGNITION_YEAR})')
    args = parser.parse_args()
    data = build_page_data(args.year)
    with open(paths.COMMUNITY_PAGE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {paths.COMMUNITY_PAGE}')


if __name__ == '__main__':
    main()
