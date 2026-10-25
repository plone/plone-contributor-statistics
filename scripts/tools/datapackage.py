"""Generate curated/datapackage.json: a Frictionless Data Package of every curated CSV file and its schema.

Run from the repository root: python -m scripts.tools.datapackage
"""

import argparse
import json
from pathlib import Path

from scripts.lib import paths
from scripts.lib.model.schema import kind_of, schema_path

PACKAGE_NAME = 'plone-contributor-statistics-curated'


def _curated_files(root):
    """(path relative to curated/, kind or None when no schema exists for it) of every curated CSV file, sorted."""
    curated = Path(root) / paths.DATAPACKAGE.parent
    found = []
    for csv_file in sorted(curated.rglob('*.csv')):
        relative = csv_file.relative_to(curated)
        try:
            found.append((relative, kind_of(paths.DATAPACKAGE.parent / relative)))
        except ValueError:
            found.append((relative, None))
    return found


def without_schema(root=Path('.')):
    """The curated CSV files that have no schema: the package leaves them out, and nothing reads them."""
    return [paths.DATAPACKAGE.parent / relative for relative, kind in _curated_files(root) if kind is None]


def build_package(root=Path('.')):
    """The descriptor of the package: one resource per curated CSV file that has a schema (see without_schema)."""
    resources = []
    for relative, kind in _curated_files(root):
        if kind is None:
            continue
        resources.append(
            {
                'name': relative.stem.replace('_', '-'),
                'path': relative.as_posix(),
                'schema': schema_path(kind).relative_to(paths.DATAPACKAGE.parent).as_posix(),
                'format': 'csv',
                'encoding': 'utf-8',
                'dialect': {'csv': {'delimiter': ','}},
            }
        )
    resources.sort(key=lambda resource: resource['path'])
    return {'name': PACKAGE_NAME, 'resources': resources}


def main(argv=None):
    argparse.ArgumentParser(description='Write curated/datapackage.json').parse_args(argv)
    with open(paths.DATAPACKAGE, 'w', encoding='utf-8') as f:
        json.dump(build_package(), f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')


if __name__ == '__main__':
    main()
