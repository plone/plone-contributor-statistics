import shutil
from pathlib import Path

import pytest

from scripts.lib.model import affiliation_id
from scripts.lib.model.names import fold, slugify
from scripts.lib.model.sources import source_id
from scripts.tools import check, datapackage

REPO = Path(__file__).resolve().parent.parent
TRAININGS = 'community-contributions/2023-plone-conference-trainings.csv'
PEOPLE = 'id,name\npbauer,Philip Bauer\ntschorr,Timo Stollenwerk\n'


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


def test_name_fold_rejects_near_duplicate(tmp_package):
    root = tmp_package(
        {
            'mappings/organisations.csv': (
                'id,name,kind,github,aliases,notes\n'
                'ecreall,Ecréall,organisation,,,\necreall-2,Ecreall,organisation,,,\n'
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


ACME = 'id,name,kind,github,aliases,notes\nacme,Acme,organisation,,,\n'
BETA = ACME + 'beta,Beta,organisation,,,\n'
ZETA = ACME + 'zeta,Zeta,organisation,,,\n'
AFFILIATIONS = 'id,person,organisation,from,to,status,checked,notes\n'
CITATIONS = 'affiliation,source,snippet,supersedes,notes\n'
SOURCES_HEADER = 'id,kind,title,date,url,archive_url,fetched,notes\n'
RECORD = 'https://example.org/record'
RECORD_PAGE = (RECORD, 'page', '2026-01-01', 'Philip Bauer works at Acme.')
DECISION_A = 'https://github.com/plone/plone-contributor-statistics/pull/1#issuecomment-1'
DECISION_B = 'https://github.com/plone/plone-contributor-statistics/pull/2#issuecomment-2'


def sources(*pages):
    """sources.csv and the excerpt files of the pages, each (url, kind, date, excerpt)."""
    rows = sorted((source_id(url), kind, on, url, text) for url, kind, on, text in pages)
    files = {'sources/sources.csv': SOURCES_HEADER + ''.join(
        f'{sid},{kind},A page,{on},{url},,2026-10-22T10:00:00Z,\n' for sid, kind, on, url, _ in rows)}
    files.update({f'sources/excerpts/{sid}.md': f'{text}\n' for sid, _, _, _, text in rows})
    return files


def affiliations(*rows, person='pbauer', organisations=ACME, citations=None, pages=(RECORD_PAGE,)):
    """The registers with affiliations of the person, each (organisation, from, to[, status[, checked]]).

    Every affiliation cites the record, unless `citations` gives the rows of citations.csv.
    """
    lines = []
    for organisation, start, end, *rest in rows:
        status, checked = (list(rest) + ['stated', ''][len(rest):])[:2]
        aid = affiliation_id(person, organisation, start, end)
        lines.append(f'{aid},{person},{organisation},{start},{"" if end is None else end},{status},{checked},')
    if citations is None:
        citations = sorted(f'{line.split(",")[0]},{source_id(RECORD)},,,' for line in lines)
    return {'mappings/people.csv': PEOPLE, 'mappings/organisations.csv': organisations,
            'mappings/affiliations.csv': AFFILIATIONS + ''.join(f'{line}\n' for line in lines),
            'mappings/citations.csv': CITATIONS + ''.join(f'{row}\n' for row in citations),
            **sources(*pages)}


def test_foreign_key_error_hints_nearest_ids(tmp_package):
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2016), person='pbaur')))
    assert len(errors) == 1
    assert errors[0][:2] == ('curated/mappings/affiliations.csv', 2)
    assert errors[0][3].endswith('nearest: pbauer')


def test_people_are_sorted_by_id(tmp_package):
    errors = check.validate(tmp_package({'mappings/people.csv': 'id,name\nb,B\na,A\n'}))
    assert [(file, row) for file, row, _, _ in errors] == [('curated/mappings/people.csv', 3)]


def test_an_affiliation_may_not_end_before_it_starts(tmp_package):
    errors = check.validate(tmp_package(affiliations(('acme', 2016, 2010))))
    assert [(row, message) for _, row, _, message in errors] == [
        (2, 'The row at position 2 has an error: from 2016 is after to 2010')]


def test_an_affiliation_of_one_year_is_fine(tmp_package):
    assert check.validate(tmp_package(affiliations(('acme', 2016, 2016)))) == []


def test_an_open_ended_affiliation_needs_checked(tmp_package):
    errors = check.validate(tmp_package(affiliations(('acme', 2016, None))))
    assert len(errors) == 1
    assert errors[0][1] == 2 and 'needs checked' in errors[0][3]


def test_an_open_ended_affiliation_with_checked_is_fine(tmp_package):
    assert check.validate(tmp_package(affiliations(('acme', 2016, None, 'stated', '2026-10-19')))) == []


def test_affiliations_are_sorted_by_person_year_and_organisation(tmp_package):
    files = affiliations(('beta', 2010, 2011, 'assumed'), ('acme', 2010, 2011), organisations=BETA)
    errors = check.validate(tmp_package(files))
    assert [(row, 'sorts before' in message) for _, row, _, message in errors] == [(3, True)]


def test_an_affiliation_id_is_unique_and_its_status_one_of_four(tmp_package):
    files = affiliations(('acme', 2010, 2011, 'guessed'), ('acme', 2012, 2013))
    header, first, second = files['mappings/affiliations.csv'].splitlines()
    files['mappings/affiliations.csv'] = '\n'.join([header, first, first.split(',')[0] + second[9:]]) + '\n'
    errors = check.validate(tmp_package(files))
    assert [(row, field) for file, row, field, _ in errors if file.endswith('affiliations.csv')] == [
        (2, 'status'), (3, 'id'), (3, None)]


def test_an_affiliation_needs_a_citation_unless_it_is_a_proposal(tmp_package):
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2011), ('beta', 2014, 2015, 'proposed'),
                                                     organisations=BETA, citations=[])))
    assert [(file, row) for file, row, _, _ in errors] == [('curated/mappings/affiliations.csv', 2)]
    assert 'no citation' in errors[0][3]


def test_an_assumed_range_does_not_reach_back_past_a_record_of_another_organisation(tmp_package):
    errors = check.validate(tmp_package(affiliations(
        ('acme', 2002, 2009, 'assumed'), ('zeta', 2010, 2015), ('acme', 2016, None, 'assumed', '2026-10-19'),
        organisations=ZETA)))
    assert [e[3] for e in errors] == [
        'The row at position 2 has an error: the assumed years 2002-2009 of acme lie before the record of zeta '
        'in row 3, and acme returns later']
    # A stated return is a real boomerang, and an assumed range that comes back after another is not a record
    assert check.validate(tmp_package(affiliations(
        ('acme', 2002, 2009), ('zeta', 2010, 2015), ('acme', 2016, None, 'assumed', '2026-10-19'),
        organisations=ZETA))) == []
    assert check.validate(tmp_package(affiliations(
        ('acme', 2002, 2009, 'assumed'), ('zeta', 2010, 2015, 'assumed'), ('acme', 2016, None, 'assumed', '2026-10-19'),
        organisations=ZETA))) == []


def test_overlapping_affiliations_are_fine_when_a_rule_decides(tmp_package):
    # Stated beats assumed in 2012-2013
    assert check.validate(tmp_package(affiliations(('acme', 2010, 2015, 'assumed'), ('beta', 2012, 2013),
                                                   organisations=BETA))) == []


def test_an_unresolved_conflict_is_an_error(tmp_package):
    # 2012-2013: two stated records, no change year, no record of the year, no commits
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2014), ('beta', 2012, 2013), organisations=BETA)))
    assert errors == [('curated/mappings/affiliations.csv', None, None,
                       f'General table error: pbauer, {year}: no attribution rule decides between acme, beta; '
                       f'record a decision') for year in (2012, 2013)]


def decisions(supersedes):
    """Two decisions for pbauer in 2012: acme, then beta, whose citation names the earlier one, or not."""
    first, later = affiliation_id('pbauer', 'acme', 2012, 2012), affiliation_id('pbauer', 'beta', 2012, 2012)
    a, b = source_id(DECISION_A), source_id(DECISION_B)
    pages = [(DECISION_A, 'decision', '2026-01-01', 'Acme in 2012.'), (DECISION_B, 'decision', '2026-02-01', 'Beta.')]
    rows = sorted([f'{first},{a},,,', f'{later},{b},,{supersedes},'])
    return affiliations(('acme', 2012, 2012), ('beta', 2012, 2012), organisations=BETA, citations=rows, pages=pages)


def test_a_later_decision_must_name_the_earlier_one(tmp_package):
    errors = check.validate(tmp_package(decisions('')))
    assert len(errors) == 1
    assert errors[0][:3] == ('curated/mappings/affiliations.csv', None, None)
    assert 'does not name the earlier decision' in errors[0][3] and 'for 2012' in errors[0][3]
    assert check.validate(tmp_package(decisions(source_id(DECISION_A)))) == []


def test_supersedes_names_sources(tmp_package):
    errors = check.validate(tmp_package(decisions(f'{source_id(DECISION_A)};ffffffffffff')))
    assert [(file, row, field) for file, row, field, _ in errors] == [
        ('curated/mappings/citations.csv', 3, 'supersedes')]
    assert '"ffffffffffff" is not in the register' in errors[0][3]


def test_a_snippet_is_in_the_excerpt_of_its_source(tmp_package):
    aid, record = affiliation_id('pbauer', 'acme', 2010, 2011), source_id(RECORD)
    # Whitespace does not matter
    rows = [f'{aid},{record},He founded Acme.,,', f'{aid},{record},Philip  Bauer works\tat Acme,,']
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2011), citations=rows)))
    assert [(file, row, field) for file, row, field, _ in errors] == [('curated/mappings/citations.csv', 2, 'snippet')]


def test_citations_point_to_affiliations_and_sources(tmp_package):
    aid, record = affiliation_id('pbauer', 'acme', 2010, 2011), source_id(RECORD)
    rows = sorted([f'{aid},0123456789ab,,,', f'{aid},{record},,,', f'a12345678,{record},,,'])
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2011), citations=rows)))
    assert [(row, field) for _, row, field, _ in errors] == [(2, 'affiliation'), (3, 'source')]


def test_citations_are_sorted(tmp_package):
    aid, record = affiliation_id('pbauer', 'acme', 2010, 2011), source_id(RECORD)
    rows = [f'{aid},{record},works at,,', f'{aid},{record},Philip Bauer,,']
    errors = check.validate(tmp_package(affiliations(('acme', 2010, 2011), citations=rows)))
    assert [(file, row) for file, row, _, _ in errors] == [('curated/mappings/citations.csv', 3)]


def identities(*rows, people=PEOPLE):
    """The registers with the identities, each `person,kind,value,source,snippet,notes` with RECORD for the record."""
    record = source_id(RECORD)
    return {'mappings/people.csv': people, **sources(RECORD_PAGE),
            'mappings/identities.csv': 'person,kind,value,source,snippet,notes\n' + ''.join(
                f'{row.replace("RECORD", record)}\n' for row in rows)}


def test_an_identity_cites_a_source_unless_an_early_address_says_what_it_rests_on(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,email,old@localhost,,,',
                                                   'pbauer,email,pb@localhost,,,the same SVN user as pbauer',
                                                   'pbauer,name,Phil B,,,')))
    assert [(row, field) for _, row, field, _ in errors] == [(2, 'source'), (4, 'source')]


def test_an_identity_source_is_in_the_source_register(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,name,Phil B,0123456789ab,,')))
    assert [(file, row, field) for file, row, field, _ in errors] == [('curated/mappings/identities.csv', 2, 'source')]


def test_identities_are_sorted(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,name,Phil B,RECORD,,', 'pbauer,github,pbauer,RECORD,,')))
    assert [(row, 'sorts before' in message) for _, row, _, message in errors] == [(3, True)]


@pytest.mark.parametrize('kind,value,other', [('email', 'pb@example.org', 'PB@Example.org'),
                                              ('github', 'pbauer', 'PBauer'),
                                              ('github-alias', 'pbauer-old', 'PBAUER-OLD')])
def test_a_login_or_an_address_is_unique_within_its_kind_ignoring_case(tmp_package, kind, value, other):
    errors = check.validate(tmp_package(identities(f'pbauer,{kind},{value},RECORD,,',
                                                   f'tschorr,{kind},{other},RECORD,,')))
    assert [(row, field) for _, row, field, _ in errors] == [(3, 'value')]
    assert 'row 2' in errors[0][3]


def test_a_name_may_belong_to_two_people(tmp_package):
    # Homonyms without GitHub: the name finds neither of them, but both keep the public record of their name
    assert check.validate(tmp_package(identities('pbauer,name,Phil B,RECORD,,', 'tschorr,name,Phil B,RECORD,,',
                                                 'tschorr,name,phil b,RECORD,,'))) == []


def test_an_identity_is_unique_per_person_kind_and_value(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,name,Phil B,RECORD,,', 'pbauer,name,Phil B,RECORD,,')))
    assert [(row, field) for _, row, field, _ in errors] == [(3, None)]


def test_the_same_value_in_two_kinds_is_fine(tmp_package):
    # A login that is also a spelling in changelogs, of the same person
    assert check.validate(tmp_package(identities('pbauer,github,pbauer2,RECORD,,',
                                                 'pbauer,name,pbauer2,RECORD,,'))) == []


def test_a_person_has_one_github_identity(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,github,pbauer,RECORD,,', 'pbauer,github,pbauer2,RECORD,,')))
    assert len(errors) == 1
    assert errors[0][1:3] == (3, 'value') and 'github-alias' in errors[0][3]


def test_a_further_account_is_nobodys_github(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,github-alias,TSCHORR,RECORD,,',
                                                   'tschorr,github,tschorr,RECORD,,')))
    assert len(errors) == 1
    assert errors[0][1:3] == (2, 'value') and 'pbauer' in errors[0][3] and 'tschorr' in errors[0][3]


def test_a_further_account_of_the_person_itself_is_fine(tmp_package):
    assert check.validate(tmp_package(identities('pbauer,github,pbauer,RECORD,,',
                                                 'pbauer,github-alias,pbauer-old,RECORD,,'))) == []


def test_a_snippet_needs_a_source(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,email,pb@localhost,,Philip Bauer,an SVN user')))
    assert [(row, field) for _, row, field, _ in errors] == [(2, 'snippet')]
    assert 'no source' in errors[0][3]


def test_an_identity_snippet_is_in_the_excerpt_of_its_source(tmp_package):
    errors = check.validate(tmp_package(identities('pbauer,name,Philip Bauer,RECORD,Philip Bauer works,',
                                                   'tschorr,name,Timo,RECORD,Timo works,')))
    assert [(row, field) for _, row, field, _ in errors] == [(3, 'snippet')]


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


SOURCE_HEADER = 'id,kind,title,date,url,archive_url,fetched,notes\n'


def source_row(url='https://example.org/page', sid=None, timestamp=None):
    from scripts.lib.model.sources import source_id

    sid = sid or source_id(url, timestamp)
    return f'{sid},page,A page,2026-01-01,{url},,2026-10-22T10:00:00Z,\n', sid


def sources_files(row, excerpts):
    files = {'sources/sources.csv': SOURCE_HEADER + row}
    files.update({f'sources/excerpts/{name}.md': text for name, text in excerpts.items()})
    return files


def test_a_correct_source_has_no_errors(tmp_package):
    row, sid = source_row()
    assert check.validate(tmp_package(sources_files(row, {sid: 'A passage.\n'}))) == []


def test_source_id_must_match_its_url(tmp_package):
    row, sid = source_row(sid='0123456789ab')
    errors = check.validate(tmp_package(sources_files(row, {'0123456789ab': 'A passage.\n'})))
    assert len(errors) == 1
    assert errors[0][:3] == ('curated/sources/sources.csv', 2, None)
    assert '0123456789ab' in errors[0][3]


def test_source_id_of_an_archive_copy_uses_its_timestamp(tmp_package):
    archive = 'https://web.archive.org/web/20060101000000/http://example.org/page'
    row = f'{{}},page,A page,2026-01-01,http://example.org/page,{archive},2026-10-22T10:00:00Z,\n'
    from scripts.lib.model.sources import source_id

    sid = source_id('http://example.org/page', '20060101000000')
    files = sources_files(row.format(sid), {sid: 'A passage.\n'})
    assert check.validate(tmp_package(files)) == []


def test_source_without_excerpt_file_is_an_error(tmp_package):
    row, _ = source_row()
    errors = check.validate(tmp_package(sources_files(row, {})))
    assert len(errors) == 1
    assert errors[0][:2] == ('curated/sources/sources.csv', 2)
    assert 'excerpt' in errors[0][3]


def test_source_with_empty_excerpt_file_is_an_error(tmp_package):
    row, sid = source_row()
    errors = check.validate(tmp_package(sources_files(row, {sid: '\n  \n'})))
    assert len(errors) == 1
    assert 'passage' in errors[0][3]


def test_excerpt_file_without_a_row_is_an_error(tmp_package):
    row, sid = source_row()
    errors = check.validate(tmp_package(sources_files(row, {sid: 'A passage.\n', 'ffffffffffff': 'Orphan.\n'})))
    assert len(errors) == 1
    file, _, _, message = errors[0]
    assert file == 'curated/sources/sources.csv'
    assert 'ffffffffffff.md' in message


def test_sources_must_be_sorted_by_id(tmp_package):
    first, a = source_row('https://example.org/a')
    second, b = source_row('https://example.org/b')
    rows = sorted([(a, first), (b, second)], reverse=True)
    errors = check.validate(tmp_package(sources_files(''.join(r for _, r in rows), {a: 'x\n', b: 'y\n'})))
    assert [e[3] for e in errors if 'sorts before' in e[3]]


def test_the_attribution_checks_say_when_they_are_skipped(tmp_package):
    root = tmp_package(affiliations(('acme', 2010, 2014), ('beta', 2012, 2013), organisations=BETA))
    (root / 'curated/mappings/identities.csv').unlink()
    errors = [error for error in check.validate(root) if error[0] == 'curated/mappings/affiliations.csv']
    assert [message.split(': ', 1)[1] for _, _, _, message in errors] == [
        f'the {name} check was skipped: the registers cannot be read: {root}/curated/mappings/identities.csv is '
        f'missing' for name in ('conflict', 'decision')]


def test_unique_casefold_only_needs_a_scope():
    from scripts.lib.model.checks import UniqueCasefold

    with pytest.raises(ValueError, match='scope'):
        UniqueCasefold(field='value', only=('email',))
    assert UniqueCasefold(field='value', scope='kind', only=('email',)).only == ('email',)
