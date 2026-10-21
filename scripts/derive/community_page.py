#!/usr/bin/env python3
"""Derive the data of the community page into derived/community-page.json.

Every number the page shows is computed here from committed data; the page only
renders this file. The definitions are explained in
docs/explanation/community-page.md.
"""

import argparse
import csv
import json
from collections import defaultdict

from scripts.lib import paths
from scripts.lib.model import TALK_TYPES, UNMAPPED, events, items, load_registry, roles, talks
from scripts.lib.model.names import fold, slugify
from scripts.lib.model.registers import PERSON_PREFIX
from scripts.lib.years import RECOGNITION_YEAR
from scripts.report import generate_community_recognition_report as recognition

FIRST_YEAR = 2003


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


def code_key(registry, username):
    """Who a collected username is: the id of the registered person, else the login in lower case."""
    person = registry.person_for_username(username)
    return person.id if person else username.casefold()


def people_of_year(year, registry, year_roles, year_talks):
    """Everyone active in the year, one entry per person: code work, roles and talks together."""
    found = defaultdict(lambda: {'commits': 0, 'pull_requests': 0, 'roles': set(), 'talks': []})
    for username, commits, pulls in code_work(year):
        person = found[code_key(registry, username)]
        person['commits'] += commits
        person['pull_requests'] += pulls
    for role in year_roles:
        found[role.person]['roles'].add(role.label)
    for talk in year_talks:
        found[talk.person]['talks'].append({'title': talk.title, 'event': talk.event, 'video': talk.video})
    return [{'id': key, 'name': registry.display_name(f'{PERSON_PREFIX}{key}' if key in registry.people else key),
             'commits': value['commits'], 'pull_requests': value['pull_requests'],
             'roles': sorted(value['roles']),
             'talks': sorted(value['talks'], key=lambda t: (t['event'], t['title'])),
             # The organisation the affiliations give the person for the year; a login outside the register has none
             'organisation': registry.organisation_of(key, year)} for key, value in sorted(found.items())]


def talk_organisations(year, registry):
    """The names of the organisations named in the talks of the year, one per talk and organisation."""
    found = [registry.organisation_name(o) for item in items(year, 'world-plone-day-talks')
             if item.fields['type'] in TALK_TYPES for o in item.organisations]
    found += [registry.organisation_name(o) for item in items(year, 'conference-talks') for o in item.organisations]
    return found


def organisations_of_year(year, registry, year_roles, year_events):
    """The organisations active in the year: from code work, from the organisation of role holders, from events."""
    found = {organisation for organisation, _, _ in organisation_code_work(year)}
    found.update(registry.organisation_of(role.person, year) for role in year_roles)
    found.update(registry.organisation_name(o) for event in year_events for o in event.organisations)
    found.update(talk_organisations(year, registry))
    return {o for o in found if registry.is_counted_organisation(o)}


def event_data(registry, event):
    return {'kind': event.kind, 'name': event.name, 'level': event.level,
            'organisations': [name for name in (registry.organisation_name(o) for o in event.organisations)
                              if name != UNMAPPED],
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


def organisation_history(year, registry, year_roles, year_events):
    """Yearly counts per organisation: commits, merged pull requests, roles and events.

    A role counts for the organisation its person belonged to in the year, an event for each organisation named.
    """
    found = defaultdict(lambda: {'commits': 0, 'pull_requests': 0, 'roles': 0, 'events': 0})
    for organisation, commits, pulls in organisation_code_work(year):
        found[organisation]['commits'] += commits
        found[organisation]['pull_requests'] += pulls
    for role in year_roles:
        found[registry.organisation_of(role.person, year)]['roles'] += 1
    for event in year_events:
        for organisation in event.organisations:
            found[registry.organisation_name(organisation)]['events'] += 1
    for organisation in talk_organisations(year, registry):
        found[organisation]['roles'] += 1
    return found


def history_of_year(year, registry, people_list, year_roles, year_events):
    commits = sum(c for _, c, _ in code_work(year))
    pulls = sum(p for _, _, p in code_work(year))

    def holder(role, **extra):
        return {'name': registry.people[role.person].name, **extra,
                'organisation': registry.organisation_of(role.person, year), 'source': role.source or None}

    return {
        'people_active': len(people_list),
        'commits': commits,
        # Plone moved to GitHub around 2010: earlier years have no pull requests at all
        'pull_requests': pulls or None,
        'board': [holder(r) for r in year_roles if r.kind == 'board-of-directors'],
        'team_leads': [holder(r, team=r.detail) for r in year_roles if r.kind == 'team-leaders'],
        'events': [event_data(registry, event) for event in year_events],
    }


def people_names(registry):
    """{folded name or login: person id} of the registered people; a key that fits two people is left out."""
    keys = defaultdict(set)
    for person in registry.people.values():
        keys[fold(person.name)].add(person.id)
        if person.github:
            keys[fold(person.github)].add(person.id)
    for identity in registry.identities:
        if identity.kind in ('name', 'login'):
            keys[fold(identity.value)].add(identity.person)
    return {key: next(iter(ids)) for key, ids in sorted(keys.items()) if len(ids) == 1}


def build_page_data(year=RECOGNITION_YEAR):
    all_years = list(range(FIRST_YEAR, year + 1))
    window = list(recognition.five_years(year))
    registry = load_registry()
    year_roles = {y: roles(y) for y in all_years}
    year_events = {y: events(y) for y in all_years}
    year_talks = {y: talks(y) for y in all_years}

    per_person = {y: people_of_year(y, registry, year_roles[y], year_talks[y]) for y in all_years}
    per_organisation = {y: organisation_history(y, registry, year_roles[y], year_events[y]) for y in all_years}

    found = {}
    org_points, _ = recognition.calculate_community_recognition_points(year=year, registry=registry,
                                                                       contributions=found)
    levels = recognition.load_recognition_levels()
    organisations = {}
    wall = defaultdict(list)
    for name in sorted(org_points, key=str.casefold):
        data = organisation_data(name, org_points[name], found.get(name, {}), levels, all_years, per_organisation)
        if data['level'] == 'No Level':
            continue
        organisations[slugify(name)] = data
        wall[data['level']].append({'name': name, 'slug': slugify(name), 'points': data['points']})

    def people_in(years_):
        return len({p['id'] for y in years_ for p in per_person[y]})

    def organisations_in(years_):
        return len(set().union(*(organisations_of_year(y, registry, year_roles[y], year_events[y]) for y in years_)))

    return {
        'year': year,
        'years': window,
        'headline': {
            'year': {'people': people_in([year]), 'organisations': organisations_in([year]),
                     'events': len(year_events[year])},
            'five_years': {'people': people_in(window), 'organisations': organisations_in(window),
                           'events': sum(len(year_events[y]) for y in window)},
            'since_2003': {'people': people_in(all_years)},
        },
        'levels': levels_data(levels),
        'wall': [{'level': level['name'], 'organisations': wall[level['name']]}
                 for level in sorted(levels, key=lambda lvl: -lvl['min_points']) if wall[level['name']]],
        'organisations': organisations,
        'people': {str(y): per_person[y] for y in all_years},
        # Names of the people in the register, for the people search: the folded name finds the id
        'people_names': people_names(registry),
        'history': {str(y): history_of_year(y, registry, per_person[y], year_roles[y], year_events[y])
                    for y in all_years},
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
