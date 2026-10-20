import shutil
from pathlib import Path

import pytest

from scripts.lib.model.names import fold, slugify
from scripts.tools import check, datapackage

REPO = Path(__file__).resolve().parent.parent
TRAININGS = 'community-contributions/2023-plone-conference-trainings.csv'
PEOPLE = (
    'id,name,github,source\n'
    'pbauer,Philip Bauer,pbauer,https://github.com/pbauer\n'
    'tschorr,Timo Stollenwerk,tschorr,https://github.com/tschorr\n'
)


@pytest.fixture
def tmp_package(tmp_repo):
    """Write the given register files under curated/ and the data package that describes them."""

    def build(files):
        shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
        for relative, text in files.items():
            target = tmp_repo / 'curated' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        datapackage.main([])
        return tmp_repo

    return build


def trainings(trainers):
    return {
        'mappings/people.csv': PEOPLE,
        TRAININGS: f'title,trainers,source,notes\nPlone 6,{trainers},https://example.org/t,\n',
    }


def test_fold_and_slugify():
    assert fold('Ecréall ') == fold('ecreall')
    assert slugify('Víctor Fernández de Alba') == 'victor-fernandez-de-alba'


def test_set_keys_rejects_empty_element(tmp_package):
    root = tmp_package(trainings('pbauer;;tschorr'))
    errors = check.validate(root)
    assert len(errors) == 1
    file, row, field, message = errors[0]
    assert (file, row, field) == ('curated/' + TRAININGS, 2, 'trainers')


def test_set_keys_rejects_unknown_key(tmp_package):
    errors = check.validate(tmp_package(trainings('pbauer;nobody')))
    assert len(errors) == 1
    assert 'nobody' in errors[0][3]


def test_affiliation_overlap_names_both_rows(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': PEOPLE,
            'mappings/organisations.csv': 'id,name,kind,aliases,notes\nacme,Acme,organisation,,\n',
            'mappings/affiliations.csv': (
                'person,organisation,from,to,source,checked,notes\n'
                'pbauer,acme,2010,2016,https://example.org/a,,\n'
                'pbauer,acme,2016,,https://example.org/b,2026-10-19,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert '2' in errors[0][3] and '3' in errors[0][3]


def test_name_fold_rejects_near_duplicate(tmp_package):
    root = tmp_package(
        {
            'mappings/organisations.csv': (
                'id,name,kind,aliases,notes\necreall,Ecréall,organisation,,\necreall-2,Ecreall,organisation,,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert 'Ecreall' in errors[0][3]
    assert errors[0][1] == 3


def test_check_main_prints_file_row_field(tmp_package, capsys):
    tmp_package(trainings('pbauer;;tschorr'))
    with pytest.raises(SystemExit) as exit_info:
        check.main([])
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert out.startswith('curated/community-contributions/2023-plone-conference-trainings.csv:2:trainers:')


def test_check_hints_nearest_ids(tmp_package, capsys):
    tmp_package(trainings('pbauer;pbaur'))
    with pytest.raises(SystemExit):
        check.main([])
    out = capsys.readouterr().out
    assert 'nearest:' in out and 'pbauer' in out.split('nearest:')[1]


def test_foreign_key_error_hints_nearest_ids(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': PEOPLE,
            'mappings/organisations.csv': 'id,name,kind,aliases,notes\nacme,Acme,organisation,,\n',
            'mappings/affiliations.csv': (
                'person,organisation,from,to,source,checked,notes\npbaur,acme,2010,2016,https://example.org/a,,\n'
            ),
        }
    )
    errors = check.validate(root)
    assert len(errors) == 1
    assert errors[0][1] == 2
    assert errors[0][3].endswith('nearest: pbauer')


def test_sorted_unique_github_and_identity_link(tmp_package):
    root = tmp_package(
        {
            'mappings/people.csv': (
                'id,name,github,source\nb,B,Same,https://example.org/b\na,A,same,https://example.org/a\n'
            ),
            'mappings/identities.csv': (
                'person,kind,value,source\na,email,a@example.org,\na,website,https://a.example.org,not a link\n'
            ),
        }
    )
    found = [(file.rsplit('/', 1)[1], row) for file, row, _, _ in check.validate(root)]
    assert found.count(('people.csv', 3)) == 2  # not sorted, and the login repeats
    assert found.count(('identities.csv', 3)) >= 1
    assert ('identities.csv', 2) not in found  # an email needs no link


def test_identity_link_may_follow_text(tmp_package):
    # As in every other source column, the link may come after the words that say what it shows
    root = tmp_package(
        {
            'mappings/people.csv': 'id,name,github,source\na,A,a,https://example.org/a\n',
            'mappings/identities.csv': 'person,kind,value,source\na,name,A B,example commit: https://example.org/c\n',
        }
    )
    assert check.validate(root) == []


def test_check_clean_prints_nothing(tmp_package, capsys):
    tmp_package(trainings('pbauer;tschorr'))
    check.main([])
    assert capsys.readouterr().out == ''


def test_a_file_the_descriptor_does_not_list_yet_is_validated(tmp_package):
    root = tmp_package(trainings('pbauer;tschorr'))
    # Added after the descriptor was written, as an editor adds the file of a new year
    (root / 'curated/community-contributions/2027-sprints.csv').write_text(
        'sprint,start,end,location,organisers,organisations,level,source,notes\n'
        'Sprint,2027-01-10,2027-01-12,Bonn,pbauer,,nonsense,https://example.org/s,\n', encoding='utf-8')
    errors = check.validate(root)
    assert ('curated/datapackage.json', None, None, check.STALE) in errors
    sprints = [error for error in errors if error[0] == 'curated/community-contributions/2027-sprints.csv']
    assert [(row, field) for _, row, field, _ in sprints] == [(2, 'level')]


def test_a_stale_descriptor_is_its_own_error_line(tmp_package, capsys):
    root = tmp_package(trainings('pbauer;tschorr'))
    (root / 'curated/datapackage.json').unlink()
    with pytest.raises(SystemExit):
        check.main([])
    assert capsys.readouterr().out == 'curated/datapackage.json::: stale — run python -m scripts.tools.datapackage\n'


ACME = 'id,name,kind,aliases,notes\nacme,Acme,organisation,,\n'
AFFILIATIONS = 'person,organisation,from,to,source,checked,notes\n'


def affiliations(*rows):
    return {'mappings/people.csv': PEOPLE, 'mappings/organisations.csv': ACME,
            'mappings/affiliations.csv': AFFILIATIONS + ''.join(f'{row}\n' for row in rows)}


def test_an_affiliation_may_not_end_before_it_starts(tmp_package):
    errors = check.validate(tmp_package(affiliations('pbauer,acme,2016,2010,https://example.org/a,,')))
    assert [(row, message) for _, row, _, message in errors] == [
        (2, 'The row at position 2 has an error: from 2016 is after to 2010')]


def test_an_affiliation_of_one_year_is_fine(tmp_package):
    assert check.validate(tmp_package(affiliations('pbauer,acme,2016,2016,https://example.org/a,,'))) == []


def test_an_open_ended_affiliation_needs_checked(tmp_package):
    errors = check.validate(tmp_package(affiliations('pbauer,acme,2016,,https://example.org/a,,')))
    assert len(errors) == 1
    assert errors[0][1] == 2 and 'needs checked' in errors[0][3]


def test_an_open_ended_affiliation_with_checked_is_fine(tmp_package):
    assert check.validate(tmp_package(affiliations('pbauer,acme,2016,,https://example.org/a,2026-10-19,'))) == []


def identities(*rows, people=PEOPLE):
    return {'mappings/people.csv': people,
            'mappings/identities.csv': 'person,kind,value,source\n' + ''.join(f'{row}\n' for row in rows)}


def test_an_identity_value_is_unique_within_its_kind_ignoring_case(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,name,Phil B,https://example.org/a',
                                                   'tschorr,name,phil b,https://example.org/b')))
    assert len(errors) == 1
    assert (errors[0][1], errors[0][2]) == (3, 'value') and 'row 2' in errors[0][3]


def test_the_same_value_in_two_kinds_is_fine(tmp_package):
    # A login that is also a spelling in changelogs, of the same person
    assert check.validate(tmp_package(identities('pbauer,login,pbauer2,https://example.org/a',
                                                 'pbauer,name,pbauer2,https://example.org/b'))) == []


def test_a_second_login_may_not_be_the_github_of_another_person(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,login,TSCHORR,https://example.org/a')))
    assert len(errors) == 1
    message = errors[0][3]
    assert 'pbauer' in message and 'tschorr' in message and 'people.csv' in message


def test_a_github_may_not_be_the_second_login_of_another_person(tmp_package):
    # Seen from people.csv: a new person gets the login that is already another person's second account
    people = PEOPLE + 'zoe,Zoe,zoe2,https://github.com/zoe2\n'
    errors = check.validate(tmp_package(identities('pbauer,login,pbauer-old,https://example.org/a',
                                                   'tschorr,login,zoe2,https://example.org/b', people=people)))
    assert len(errors) == 1
    assert 'tschorr' in errors[0][3] and 'zoe' in errors[0][3]


def test_a_second_login_of_the_person_itself_is_fine(tmp_package):
    assert check.validate(tmp_package(identities('pbauer,login,pbauer-old,https://example.org/a'))) == []


def test_fold_lower_cases_and_keeps_sharp_s():
    # The people search of the community page keys names the same way in JavaScript (toLowerCase)
    assert fold('Tamara Eßer') == 'tamara eßer'
    assert fold('  Víctor   Fernández-Alba ') == 'victor fernandezalba'


SITE_JS = REPO / 'scripts/report/site/static/site.js'


@pytest.mark.skipif(shutil.which('node') is None, reason='needs node')
def test_site_js_normalise_is_fold():
    import json
    import re
    import subprocess

    source = re.search(r'\n(\s*)function normalise\(text\) \{.*?\n\1\}', SITE_JS.read_text(), re.S).group(0)
    samples = ['Tamara Eßer', 'Víctor Fernández de Alba', 'Ecréall ', 'Sune Brøndum Wøller', "O'Brien  Jr.",
               'Benoît Suttor', 'ŁUKASZ Ąę', 'Ångström', 'Δημήτρης', 'ｆｕｌｌ ｗｉｄｔｈ']
    script = source + f'\nconsole.log(JSON.stringify({json.dumps(samples)}.map(normalise)));'
    out = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [fold(sample) for sample in samples]
