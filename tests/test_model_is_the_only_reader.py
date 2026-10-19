"""scripts/lib/model is the only code that reads curated/ (#139)."""

import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'

# Where curated/ is named in code
CONSTANTS = ('COMMUNITY', 'MAPPINGS_DIR', 'PEOPLE', 'IDENTITIES', 'AFFILIATIONS', 'ORGANISATIONS',
             'AFFILIATION_PROPOSALS', 'RECOGNITION_LEVELS', 'BOT_ACCOUNTS', 'EXCLUDED_REPOSITORIES',
             'PLIPS_BEFORE_GITHUB', 'SCHEMAS_DIR', 'DATAPACKAGE')
CURATED_MARKERS = re.compile(r'\bpaths\.(' + '|'.join(CONSTANTS) + r')\b|[\'"]curated/')

# Code that may read curated/ itself
ALLOWED_PREFIXES = (
    'scripts/lib/model/',  # the model: the one reader
    'scripts/tools/migrate_data/',  # the migration from the old files, archived after the merge
)
# The other files that name a curated path, and which markers each may use
ALLOWED = {
    'scripts/tools/migrate_data_structure.py': None,  # the migration from the old files: anything
    'scripts/lib/paths.py': None,  # says where every file lives
    # check.py and datapackage.py validate and describe the curated files against their schemas
    'scripts/tools/check.py': {'paths.SCHEMAS_DIR', 'paths.DATAPACKAGE', "'curated/", '"curated/'},
    'scripts/tools/datapackage.py': {'paths.SCHEMAS_DIR', 'paths.DATAPACKAGE', "'curated/", '"curated/'},
    # Reads the recognition levels, which only this script uses; community files come through the model
    'scripts/report/generate_community_recognition_report.py': {'paths.RECOGNITION_LEVELS'},
    # Names the two files that the model's loaders read, so that the tests can write them
    'scripts/collect/plone_contributors.py': {'paths.BOT_ACCOUNTS', 'paths.EXCLUDED_REPOSITORIES'},
}


def offences(relative, text):
    """The markers of curated paths in the text of a script that it may not use, sorted."""
    if relative.startswith(ALLOWED_PREFIXES):
        return []
    found = {match.group(0) for match in CURATED_MARKERS.finditer(text)}
    allowed = ALLOWED.get(relative, set())
    return [] if allowed is None else sorted(found - allowed)


def test_only_the_model_reads_curated():
    found = {}
    for path in sorted(SCRIPTS.rglob('*.py')):
        relative = path.relative_to(SCRIPTS.parent).as_posix()
        bad = offences(relative, path.read_text(encoding='utf-8'))
        if bad:
            found[relative] = bad
    assert not found, f'read curated/ without the model: {found}'


def test_the_checker_flags_what_a_file_may_not_use():
    report = 'scripts/report/generate_community_recognition_report.py'
    text = 'levels = paths.RECOGNITION_LEVELS\nrows = csv.DictReader(open(paths.COMMUNITY / "x.csv"))\n'
    assert offences(report, text) == ['paths.COMMUNITY']
    assert offences(report, 'levels = paths.RECOGNITION_LEVELS\n') == []
    assert offences('scripts/derive/new.py', "open('curated/mappings/people.csv')") == ["'curated/"]
    assert offences('scripts/lib/model/new.py', 'paths.PEOPLE') == []
