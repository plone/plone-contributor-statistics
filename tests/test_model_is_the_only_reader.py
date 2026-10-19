"""scripts/lib/model is the only code that reads curated/ (#139)."""

import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'

# Where curated/ is named in code
CURATED_MARKERS = re.compile(
    r'''\bpaths\.(COMMUNITY|MAPPINGS_DIR|PEOPLE|IDENTITIES|AFFILIATIONS|ORGANISATIONS|AFFILIATION_PROPOSALS)\b'''
    r'''|['"]curated/''')

# Code that may read curated/ itself
ALLOWED_PREFIXES = (
    'scripts/lib/model/',  # the model: the one reader
    'scripts/tools/migrate_data/',  # the migration from the old files, archived after the merge
)
# Files that name a curated path without reading a register
ALLOWED_FILES = {
    'scripts/tools/migrate_data_structure.py',  # the migration from the old files
    'scripts/lib/paths.py',  # says where every file lives
    'scripts/tools/check.py',  # checks the curated files against their schemas
    'scripts/tools/datapackage.py',  # describes the curated files in the data package
    # Passes paths.COMMUNITY on as the default folder to the model's items(); it reads nothing itself
    'scripts/report/generate_community_recognition_report.py',
}


def test_only_the_model_reads_curated():
    offenders = {}
    for path in sorted(SCRIPTS.rglob('*.py')):
        relative = path.relative_to(SCRIPTS.parent).as_posix()
        if relative in ALLOWED_FILES or relative.startswith(ALLOWED_PREFIXES):
            continue
        text = path.read_text(encoding='utf-8')
        found = sorted({match.group(0) for match in CURATED_MARKERS.finditer(text)})
        if found:
            offenders[relative] = found
    assert not offenders, f'read curated/ without the model: {offenders}'
