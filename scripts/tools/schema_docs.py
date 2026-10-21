"""Write docs/reference/curated-files.md from the data package and the Table Schemas of the curated files.

Run from the repository root: python -m scripts.tools.schema_docs
Add --check to compare the committed page with the generated one instead of writing it.
"""

import argparse
import json
import sys
from pathlib import Path

from frictionless import Package

from scripts.lib import paths
from scripts.lib.model.checks import SetKeys, checks_for

PAGE = Path('docs/reference/curated-files.md')

# Group -> (what it holds, [(kind, title)]), in the order of the page
GROUPS = [
    ('Registers', 'People, identities, affiliations and organisations, in `curated/mappings/`.', [
        ('people', 'People'),
        ('identities', 'Identities'),
        ('affiliations', 'Affiliations'),
        ('organisations', 'Organisations'),
        ('affiliation-proposals', 'Affiliation proposals'),
        ('rejected-proposals', 'Rejected proposals'),
    ]),
    ('Lists', 'Accounts and repositories that the collectors treat in a special way, in `curated/mappings/`.', [
        ('bot-accounts', 'Bot accounts'),
        ('excluded-repositories', 'Excluded repositories'),
    ]),
    ('Community data', 'Community work per year and kind, in `curated/community-contributions/`.', [
        ('board-of-directors', 'Board of Directors'),
        ('team-leaders', 'Team leaders'),
        ('release-managers', 'Release managers'),
        ('podcasts', 'Podcasts'),
        ('plone-conference-trainings', 'Plone Conference trainings'),
        ('world-plone-day-talks', 'World Plone Day talks'),
        ('sprints', 'Sprints'),
        ('plone-conference', 'Plone Conference'),
        ('world-plone-day-event', 'World Plone Day events'),
    ]),
    ('Recognition files and PLIPs',
     'The recognition tables, see {doc}`recognition-files`, and the PLIPs from before GitHub.', [
         ('community-recognition-levels', 'Community recognition levels'),
         ('community-recognition-points', 'Community recognition points'),
         ('plips-before-github', 'PLIPs before GitHub'),
     ]),
]

ONE_ROW_IS = {
    'people': 'one person.',
    'identities': 'one string that denotes a person in a source: a name, a commit address or a second login.',
    'affiliations': 'one person, one organisation and one period.',
    'organisations': 'one organisation.',
    'affiliation-proposals': 'one affiliation that a source states and that no accepted record confirms yet.'
                             ' No script reads the file.',
    'rejected-proposals': 'one proposal that a reviewer turned down, with the reason and a link to the review;'
                          ' the tools that propose affiliations leave those years out.',
    'bot-accounts': 'one GitHub account that is a bot.',
    'excluded-repositories': 'one repository of the `plone` organisation that the statistics skip.',
    'board-of-directors': 'one member of the Board of Directors whose term ends in the year.',
    'team-leaders': 'one team leader and team.',
    'release-managers': 'one release manager.',
    'podcasts': 'one host of a Plone podcast or live series.',
    'plone-conference-trainings': 'one training at the Plone Conference.',
    'world-plone-day-talks': 'one video of a World Plone Day.',
    'sprints': 'one Plone sprint of the year.',
    'plone-conference': 'one organising organisation of the Plone Conference.',
    'world-plone-day-event': 'one local World Plone Day event.',
    'community-recognition-levels': 'one recognition level.',
    'community-recognition-points': 'one kind of contribution and its points.',
    'plips-before-github': 'one PLIP from before the PLIPs moved to GitHub issues,'
                           ' as the plone.org roadmap or a Trac ticket recorded it.',
}

INTRO = """\
(reference-curated-files)=

# Curated files

This page describes every file that people edit by hand under `curated/`.
The registers and lists are in `curated/mappings/`.
The community data is in `curated/community-contributions/`, and the PLIPs from before GitHub are in `curated/plips/`.

The format of a file is its Table Schema, in `curated/schemas/<kind>.json`.
`curated/datapackage.json` lists every file with its schema; `python -m scripts.tools.datapackage` writes it.
This page is generated from them with `python -m scripts.tools.schema_docs`, so edit the schema, not the page.
Run `python -m scripts.tools.check` or `make check` to validate the files.
It reports the file, the row and the column of every error.

A column that holds the ids of several rows of a register has several ids separated by semicolons.
Quote a value that contains a comma.
Save the files as UTF-8 with Unix line endings.
{doc}`/explanation/attribution` and {doc}`/explanation/curated-community-data` explain the rules behind the data.
"""

WEB_ADDRESS = '.*https?://.*'


def _descriptor(kind):
    return json.loads((paths.SCHEMAS_DIR / f'{kind}.json').read_text(encoding='utf-8'))


def _files_by_kind():
    """Kind -> the paths of its files, relative to curated/, as the data package lists them."""
    package = json.loads(Path(paths.DATAPACKAGE).read_text(encoding='utf-8'))
    result = {}
    for entry in package['resources']:
        result.setdefault(Path(entry['schema']).stem, []).append(entry['path'])
    return result


def _pattern(files):
    """The file pattern of a kind: the one file, or the yearly files with YYYY."""
    first = files[0]
    if len(files) == 1:
        return f'curated/{first}'
    name = first.rsplit('/', 1)
    stem = name[1][5:] if name[1][:4].isdigit() else name[1]
    return f'curated/{name[0]}/YYYY-{stem}'


def _escape(text):
    return text.replace('|', '\\|')


def _constraints(field, foreign_keys, primary_key):
    parts = []
    constraints = field.get('constraints', {})
    if constraints.get('required'):
        parts.append('required')
    if constraints.get('unique') or primary_key == [field['name']]:
        parts.append('unique')
    if 'enum' in constraints:
        parts.append('one of ' + ', '.join(f'`{value}`' for value in constraints['enum']))
    if 'minimum' in constraints:
        parts.append(f'at least {constraints["minimum"]}')
    pattern = constraints.get('pattern')
    if pattern == WEB_ADDRESS:
        parts.append('contains a web address')
    elif pattern:
        parts.append(f'pattern `{pattern}`')
    for key in foreign_keys:
        if key['fields'] == [field['name']]:
            reference = key['reference']
            parts.append(f'id of a row of `{reference["resource"]}`')
    if field.get('x-set'):
        parts.append(f'ids of rows of `{field["x-set"]}` separated by semicolons')
    return _escape('; '.join(parts))


def _table(descriptor):
    foreign_keys = descriptor.get('foreignKeys', [])
    primary_key = descriptor.get('primaryKey', [])
    lines = ['| Field | Type | Constraints | Description |', '|---|---|---|---|']
    for field in descriptor['fields']:
        constraints = _constraints(field, foreign_keys, primary_key)
        description = _escape(field.get('description', ''))
        lines.append(f'| `{field["name"]}` | {field["type"]} | {constraints} | {description} |')
    return lines


def _check_lines(kind, package):
    names = {resource.name for resource in package.resources}
    resource_name = next(name for name in sorted(names) if name == kind or name.endswith(f'-{kind}'))
    lines = []
    for check in checks_for(resource_name, package):
        if isinstance(check, SetKeys):
            lines.append(f'- `{check.field}`: every element is the id of a row of the register, and none is repeated.')
        elif check.type == 'not-sorted':
            order = ', '.join(f'`{name}`' for name in check.fields)
            lines.append(f'- The rows are sorted by {order}' + (', ignoring case.' if check.casefold else '.'))
        elif check.type == 'unique-casefold':
            within = f' within its `{check.scope}`' if check.scope else ''
            lines.append(f'- `{check.field}` is unique{within}, ignoring case.')
        else:
            lines.append(f'- {check.__doc__.strip().splitlines()[0]}')
    return lines


def render():
    """The text of docs/reference/curated-files.md."""
    package = Package(str(paths.DATAPACKAGE))
    files = _files_by_kind()
    out = ['<!-- generated by python -m scripts.tools.schema_docs; do not edit -->', '', INTRO]
    for group, intro, kinds in GROUPS:
        out += [f'## {group}', '', intro, '']
        for kind, title in kinds:
            descriptor = _descriptor(kind)
            out += [f'### {title}', '', f'File: `{_pattern(files[kind])}`', '', f'One row is {ONE_ROW_IS[kind]}', '']
            out += _table(descriptor)
            if descriptor.get('primaryKey'):
                key = ', '.join(f'`{name}`' for name in descriptor['primaryKey'])
                out += ['', f'Primary key: {key}.']
            checks = _check_lines(kind, package)
            if checks:
                out += ['', 'Checks beyond the schema:', ''] + checks
            out.append('')
    return '\n'.join(out).rstrip('\n') + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='fail if the committed page is not current')
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        if PAGE.read_text(encoding='utf-8') != text:
            sys.exit(f'{PAGE} is not current: run python -m scripts.tools.schema_docs')
        return
    PAGE.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
