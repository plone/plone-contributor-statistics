"""scripts/lib/model is the only code that reads curated/ (#139)."""

import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'

# Where curated/ is named in code
CONSTANTS = ('COMMUNITY', 'MAPPINGS_DIR', 'PEOPLE', 'IDENTITIES', 'AFFILIATIONS', 'CITATIONS', 'ORGANISATIONS',
             'RECOGNITION_LEVELS', 'BOT_ACCOUNTS',
             'EXCLUDED_REPOSITORIES', 'PLIPS_BEFORE_GITHUB', 'SCHEMAS_DIR', 'DATAPACKAGE',
             'SOURCES_DIR', 'SOURCES', 'EXCERPTS_DIR')
CURATED_MARKERS = re.compile(r'\bpaths\.(' + '|'.join(CONSTANTS) + r')\b|[\'"]curated/')

# Code that may read curated/ itself
ALLOWED_PREFIXES = (
    'scripts/lib/model/',  # the model: the one reader
)
# The other files that name a curated path, and which markers each may use
ALLOWED = {
    'scripts/lib/paths.py': None,  # says where every file lives
    # check.py and datapackage.py validate and describe the curated files against their schemas
    'scripts/tools/check.py': {'paths.SCHEMAS_DIR', 'paths.DATAPACKAGE', "'curated/", '"curated/'},
    'scripts/tools/datapackage.py': {'paths.SCHEMAS_DIR', 'paths.DATAPACKAGE', "'curated/", '"curated/'},
    'scripts/tools/schema_docs.py': {'paths.SCHEMAS_DIR', 'paths.DATAPACKAGE', "'curated/", '"curated/'},
    # Names the two files that the model's loaders read, so that the tests can write them
    'scripts/collect/plone_contributors.py': {'paths.BOT_ACCOUNTS', 'paths.EXCLUDED_REPOSITORIES'},
    # Migration code of plan 2c, archived after its one use: reads the old registers, whose schemas the switch
    # removed, with plain csv, and writes the new ones
    'scripts/tools/migrate_registers.py': {'paths.MAPPINGS_DIR'},
    'scripts/tools/cited_sources.py': {'paths.MAPPINGS_DIR'},
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
    collector = 'scripts/collect/plone_contributors.py'
    text = 'bots = paths.BOT_ACCOUNTS\nrows = csv.DictReader(open(paths.COMMUNITY / "x.csv"))\n'
    assert offences(collector, text) == ['paths.COMMUNITY']
    assert offences(collector, 'bots = paths.BOT_ACCOUNTS\n') == []
    report = 'scripts/report/generate_community_recognition_report.py'
    assert offences(report, 'levels = paths.RECOGNITION_LEVELS\n') == ['paths.RECOGNITION_LEVELS']
    assert offences('scripts/derive/new.py', "open('curated/mappings/people.csv')") == ["'curated/"]
    assert offences('scripts/lib/model/new.py', 'paths.PEOPLE') == []
