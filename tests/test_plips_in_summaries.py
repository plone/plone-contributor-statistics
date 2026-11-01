"""The multi-year summaries count PLIPs as the community page and the recognition do (#104)."""

import pandas as pd

from scripts.derive import multi_year_summary
from scripts.lib import paths
from scripts.lib.model import UNMAPPED

PLIPS = 'number,title,author,state,created_at,updated_at,closed_at,repository,html_url\n'
YEARS = [2023, 2024, 2025]


def plip(number, author, closed, state='closed'):
    return (f'{number},A PLIP,{author},{state},{closed[:4]}-01-01,{closed},{closed if state == "closed" else ""},'
            f'plone/volto,https://github.com/plone/volto/issues/{number}\n')


def organisations():
    return pd.DataFrame([
        {'organisation': 'kitconcept GmbH', 'total_pull_requests': 20, 'total_commits': 90,
         'contributors_count': 2, 'contributors': 'robgietema, tisto',
         'repositories_count': 1, 'repositories': 'volto'},
        {'organisation': UNMAPPED, 'total_pull_requests': 5, 'total_commits': 9,
         'contributors_count': 1, 'contributors': 'stranger', 'repositories_count': 1, 'repositories': 'volto'},
    ])


def summary(write_registers):
    write_registers([('timo', 'tisto'), ('rob', 'robgietema')],
                    [('timo', 'kitconcept', 2024, None), ('rob', 'kitconcept', 2000, None)],
                    [('kitconcept', 'kitconcept GmbH')])
    for year in YEARS:
        paths.contributors_file(year).write_text('username,total_commits,total_pull_requests\n', encoding='utf-8')
    paths.PLIPS_DETAILED.parent.mkdir(parents=True, exist_ok=True)
    paths.PLIPS_DETAILED.write_text(
        PLIPS + plip(1, 'tisto', '2023-05-01') + plip(2, 'tisto', '2024-05-01') + plip(3, 'tisto', '2025-05-01')
        + plip(4, 'robgietema', '2025-06-01') + plip(5, 'stranger', '2025-07-01')
        + plip(6, 'tisto', '2022-05-01') + plip(7, 'tisto', '2025-08-01', state='open'), encoding='utf-8')
    _, txt_file = multi_year_summary.save_summary(organisations(), YEARS)
    return txt_file.read_text(encoding='utf-8')


def test_summary_counts_the_plips_closed_in_the_years(tmp_repo, write_registers):
    text = summary(write_registers)
    assert '- 5 PLIPs closed\n' in text


def test_summary_lists_the_contributors_by_plips(tmp_repo, write_registers):
    text = summary(write_registers)
    section = text.split('## Top 10 contributors by PLIPs (2023-2025)\n\n')[1].split('\n\n')[0]
    # The open PLIP and the one closed in 2022 don't count; equal counts by login
    assert section.splitlines() == ['1. tisto - 3 PLIPs', '2. robgietema - 1 PLIPs', '3. stranger - 1 PLIPs']


def test_summary_lists_the_organisations_by_plips_in_the_year_of_closing(tmp_repo, write_registers):
    text = summary(write_registers)
    section = text.split('## Top 10 organisations by PLIPs (2023-2025)\n\n')[1]
    # tisto belongs to kitconcept from 2024: the PLIP of 2023 is not mapped, like stranger's
    assert section.splitlines()[:3] == ['1. kitconcept GmbH: 3 PLIPs', '', 'Not mapped to an organisation: 2 PLIPs']


def test_summary_without_a_plip_file_has_no_plip_sections(tmp_repo):
    for year in YEARS:
        paths.contributors_file(year).write_text('username,total_commits,total_pull_requests\n', encoding='utf-8')
    _, txt_file = multi_year_summary.save_summary(organisations(), YEARS)
    assert 'PLIPs' not in txt_file.read_text(encoding='utf-8')
