"""The alias table of the recognition script, frozen for the migration (#139).

A copy of `org_mapping` in `normalize_organization_name` of
`scripts/report/generate_community_recognition_report.py` as it was before the migration, so that the
migration can be re-run after the table is deleted there. The migration turns the entries into the
`aliases` column of `organisations.csv`; it drops the `Unmapped` entries and lists the targets that are
no organisation in its report. Edit nothing here.
"""

ORGANISATION_ALIASES = {
    'kitconcept': 'kitconcept GmbH',
    'py76': 'PY76',
    'eau-de-web': 'Eau de Web',
    'redturtle': 'RedTurtle',
    'kleinundpartner': 'Klein & Partner KG',
    'klein und partner': 'Klein & Partner KG',
    'nuclia': 'Nuclia',
    'starzel': 'Starzel',
    'codesyntax': 'CodeSyntax',
    'syslab': 'Syslab',
    'freitag': 'der Freitag',
    'kombinat': 'Kombinat',
    'agitator': 'Agitator',
    'derico': 'Derico',
    'rohberg': 'Rohberg',
    'vangheem': 'Vangheem',
    'serpro': 'SERPRO',
    'iskra': 'Iskra',
    'university-hospital-dresden': 'Uni. Hospital Dresden',
    'dbain': 'DBA Informatica Notariaal',
    'iham': 'IHAM',
    'pretaweb': 'Pretaweb',
    'zopyx': 'ZOPYX',
    'tkimnguyen': 'Kim Nguyen',
    'stevepiercy': 'Steve Piercy - Website Builder',
    # Unmapped contributors are not an organisation (#53)
    'independent': 'Unmapped',
    'unmapped': 'Unmapped',
    'mathematics institute unam': 'UNAM',
    'mathematics institute at unam': 'UNAM',
}
