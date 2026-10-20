"""The audit of the regenerated outputs of the migration (#139), on a miniature repository.

`main` holds the old curated files and the outputs the old code made of them; the branch holds the registers
and the keyed community files; the work tree holds the regenerated outputs. In 2025 Sam Speaker gave a talk for
Beta Corp, which the migration deferred (Sam has no affiliation); Jane Doe (Acme) organised a sprint of Beta
Corp; Bob Roe led a team, in a row that said Unmapped while the old mapping gave Beta Corp. Each test changes one
regenerated value and checks the class the audit gives it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from scripts.derive import community_page
from scripts.lib.model import load_registry
from scripts.lib.model.names import slugify
from scripts.report import generate_community_recognition_report as recognition
from scripts.tools import migrate_data_structure
from scripts.tools.migrate_data import audit

REPO = Path(__file__).resolve().parent.parent
LEVELS_FILE = REPO / 'curated/community-contributions/community-recognition-levels.csv'
LEVELS = recognition.load_recognition_levels(LEVELS_FILE)
TALKS = 'curated/community-contributions/2025-world-plone-day-talks.csv'
TRAININGS = 'curated/community-contributions/2025-plone-conference-trainings.csv'

OLD_CURATED = {
    'curated/mappings/organisations.csv': 'Organisation,Team\nAcme,janedoe\nBeta Corp,bobroe\nDelta,\n',
    'curated/mappings/organisation_mapping_overrides.csv': 'github_username,organisation,from_year,to_year,source\n',
    TALKS: ('Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID,Source,Notes\n'
            'Deferred Talk,Sam Speaker,Beta Corp,Online,Talk,vid1,https://example.org/v,\n'),
    'curated/community-contributions/2025-sprints.csv': (
        'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source\n'
        'Beta Sprint,,,Town,Jane Doe,Beta Corp,strategic,https://example.org/s\n'),
    'curated/community-contributions/2025-team-leaders.csv': (
        'Name,Team,Organisation,Source\n'
        'Bob R.,Docs Team,Unmapped,https://example.org/t; organisation from the organisation mapping: '
        'https://github.com/bobroe\n'),
}
NEW_CURATED = {
    'curated/mappings/people.csv': ('id,name,github,source\n'
                                    'bob-roe,Bob Roe,bobroe,https://github.com/bobroe\n'
                                    'jane-doe,Jane Doe,janedoe,https://github.com/janedoe\n'
                                    'sam-speaker,Sam Speaker,,https://example.org/v\n'),
    'curated/mappings/identities.csv': 'person,kind,value,source\nbob-roe,name,Bob R.,https://example.org/t\n',
    'curated/mappings/affiliations.csv': ('person,organisation,from,to,source,checked,notes\n'
                                          'bob-roe,beta-corp,2025,2025,https://example.org/bob,,\n'
                                          'jane-doe,acme,2020,,https://example.org/jane,2026-10-18,\n'),
    'curated/mappings/organisations.csv': ('id,name,kind,aliases,notes\n'
                                           'acme,Acme,organisation,,\n'
                                           'beta-corp,Beta Corp,organisation,,\n'
                                           'delta,Delta,organisation,,\n'),
    'curated/mappings/affiliation_proposals.csv': ('person,organisation,from,to,evidence\n'
                                                   f'sam-speaker,beta-corp,2025,2025,{TALKS}:2; '
                                                   'https://example.org/v\n'),
    TALKS: ('title,speakers,organisations,type,location,source,notes\n'
            'Deferred Talk,sam-speaker,,Talk,Online,https://example.org/v,\n'),
    'curated/community-contributions/2025-sprints.csv': (
        'sprint,start,end,location,organisers,organisations,level,source,notes\n'
        'Beta Sprint,,,Town,jane-doe,beta-corp,strategic,https://example.org/s,\n'),
    'curated/community-contributions/2025-team-leaders.csv': ('person,team,source,notes\n'
                                                              'bob-roe,Docs Team,https://example.org/t,\n'),
    'curated/community-contributions/community-recognition-levels.csv': LEVELS_FILE.read_text(encoding='utf-8'),
}
TALK = {'file': TALKS, 'line': 2, 'points': 1, 'source': 'https://www.youtube.com/watch?v=vid1',
        'text': 'Deferred Talk'}
POINTS = {
    'old': {'Acme': {'PR Contributions': 4.0}, 'Beta Corp': {'Training Session': 2.0, 'WPD Talk': 1.0},
            'Delta': {'Training Session': 2.5}},
    'new': {'Acme': {'PR Contributions': 4.0}, 'Beta Corp': {'Training Session': 2.0},
            'Delta': {'Training Session': 2.5}},
}
DETAILS = {
    'old': {'Acme': {'PR Contributions': ['Active Member (25.0 PRs/year)']},
            'Beta Corp': {'Training Session': ['Intro Training'], 'WPD Talk': ['Deferred Talk']},
            'Delta': {'Training Session': ['Delta Training']}},
    'new': {'Acme': {'PR Contributions': ['Active Member (25.0 PRs/year)']},
            'Beta Corp': {'Training Session': ['Intro Training']},
            'Delta': {'Training Session': ['Delta Training']}},
}
CONTRIBUTIONS = {
    'Acme': {'PR Contributions': [{'file': 'derived/organisation-contributors', 'line': None, 'points': 4,
                                   'source': None, 'text': 'Active Member (25.0 PRs/year)'}]},
    'Beta Corp': {'Training Session': [{'file': TRAININGS, 'line': 2, 'points': 2.0, 'source': 'https://example.org/tr',
                                        'text': 'Intro Training'}],
                  'WPD Talk': [TALK]},
    'Delta': {'Training Session': [{'file': TRAININGS, 'line': 3, 'points': 2.5, 'source': 'https://example.org/d',
                                    'text': 'Delta Training'}]},
}
ROLES = {'old': {'Acme': 0, 'Beta Corp': 2, 'Delta': 0}, 'new': {'Acme': 1, 'Beta Corp': 1, 'Delta': 0}}


def organisation(name, side):
    """A page entry as the community page writes it."""
    categories = {category: {'points': points,
                             'contributions': [c for c in CONTRIBUTIONS[name][category]]}
                  for category, points in POINTS[side][name].items()}
    total = sum(POINTS[side][name].values())
    higher = [lvl for lvl in LEVELS if lvl['min_points'] > total]
    next_level = min(higher, key=lambda lvl: lvl['min_points'])
    return {'name': name, 'level': recognition.get_recognition_level(total, LEVELS), 'points': total,
            'next_level': next_level['name'], 'points_to_next': next_level['min_points'] - total,
            'categories': categories,
            'history': {'2025': {'commits': 0, 'pull_requests': 0, 'roles': ROLES[side][name],
                                 'events': 1 if name == 'Beta Corp' else 0}}}


def page(side, registry=None):
    organisations = {slugify(name): organisation(name, side) for name in sorted(POINTS[side])}
    wall = {}
    for entry in organisations.values():
        wall.setdefault(entry['level'], []).append({'name': entry['name'], 'slug': slugify(entry['name']),
                                                    'points': entry['points']})
    holder = ({'name': 'Bob R.', 'organisation': 'Unmapped', 'team': 'Docs Team',
               'source': 'https://example.org/t; organisation from the organisation mapping: https://github.com/bobroe'}
              if side == 'old' else
              {'name': 'Bob Roe', 'organisation': 'Beta Corp', 'team': 'Docs Team', 'source': 'https://example.org/t'})
    people = ([{'id': 'bobroe', 'roles': ['Team lead']}, {'id': 'janedoe', 'roles': ['Sprint organiser']},
               {'id': 'name:sam speaker', 'roles': ['Talk']}] if side == 'old' else
              [{'id': 'bob-roe', 'name': 'Bob Roe', 'roles': ['Team lead']},
               {'id': 'jane-doe', 'name': 'Jane Doe', 'roles': ['Sprint organiser']},
               {'id': 'sam-speaker', 'name': 'Sam Speaker', 'roles': ['Talk']}])
    for person in people:
        person.update(commits=0, pull_requests=0)
    return {
        'year': 2025, 'years': [2021, 2022, 2023, 2024, 2025],
        'headline': {'year': {'people': 3, 'organisations': 2, 'events': 1}},
        'levels': community_page.levels_data(LEVELS),
        'wall': [{'level': level['name'], 'organisations': wall[level['name']]}
                 for level in sorted(LEVELS, key=lambda lvl: -lvl['min_points']) if level['name'] in wall],
        'organisations': organisations,
        'people': {'2025': people},
        'people_names': ({'bob r.': 'bobroe', 'jane doe': 'janedoe'} if side == 'old'
                         else community_page.people_names(registry)),
        'history': {'2025': {'board': [], 'commits': 0, 'people_active': 3, 'pull_requests': None,
                             'events': [{'kind': 'sprints', 'level': 'strategic', 'name': 'Beta Sprint',
                                         'organisations': ['Beta Corp'], 'sources': ['https://example.org/s']}],
                             'team_leads': [holder]}},
    }


def write(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding='utf-8')


def write_outputs(root, side, registry=None, page_change=None, csv_change=None, md_change=None):
    data = page(side, registry)
    if page_change:
        page_change(data)
    (root / 'derived').mkdir(exist_ok=True)
    with open(root / audit.PAGE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    csv_file = root / 'derived/community-recognition/2025-community-recognition-report.csv'
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    results = recognition.write_csv_report(POINTS[side], LEVELS, csv_file)
    md_file = root / audit.RECOGNITION_MD
    recognition.write_markdown_report(POINTS[side], DETAILS[side], results, LEVELS, str(md_file), year=2025)
    for path, change in ((csv_file, csv_change), (md_file, md_change)):
        if change:
            path.write_text(change(path.read_text(encoding='utf-8')), encoding='utf-8')


def git(root, *args):
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', '-c',
                    'commit.gpgsign=false', *args], cwd=root, check=True, capture_output=True)


def audited(root, old_mapping=None, old_page_change=None, **changes):
    """{excerpt: class} of the audit of the miniature repository, with one change to the new outputs."""
    git(root, 'init', '-q', '-b', 'main')
    old = dict(OLD_CURATED)
    if old_mapping is not None:
        old['curated/mappings/organisations.csv'] = old_mapping
    write(root, old)
    write_outputs(root, 'old', page_change=old_page_change)
    git(root, 'add', '.')
    git(root, 'commit', '-q', '-m', 'old')
    git(root, 'checkout', '-q', '-b', 'migration')
    git(root, 'rm', '-q', '-r', 'curated')
    write(root, NEW_CURATED)
    git(root, 'add', '.')
    git(root, 'commit', '-q', '-m', 'registers')
    write_outputs(root, 'new', load_registry(root / 'curated/mappings'), **changes)
    found = audit.audit(root, base='main', from_rev='HEAD')
    return {excerpt.split(': ', 1)[1].strip(): kind for _, kind, excerpt in found}


def unexplained(found):
    return {excerpt for excerpt, kind in found.items() if kind == audit.UNEXPLAINED}


@pytest.fixture(scope='module')
def baseline(tmp_path_factory):
    return audited(tmp_path_factory.mktemp('audit'))


def test_the_genuine_changes_are_all_explained(baseline):
    assert not unexplained(baseline)


def test_the_deferred_talk_is_deferred(baseline):
    assert baseline['Beta Corp,Bronze Contributor,0,0,0,0,0,0,1.0,0,2.0,0,0,3.0'] == 'deferred'
    assert baseline['Beta Corp,Community Contributor,0,0,0,0,0,0,0,0,2.0,0,0,2.0'] == 'deferred'
    assert baseline['"level": "Community Contributor",'] == 'deferred'
    assert baseline['| WPD Talk | 1.0 | • Deferred Talk |'] == 'deferred'
    assert baseline['- **Total Points Awarded**: 8.5'] == 'deferred'


def test_an_organiser_role_counts_for_the_persons_organisation(baseline):
    # Acme: no role before, Jane's sprint now
    assert baseline['"roles": 0'] == 'organiser-role'


def test_the_role_count_of_several_causes_names_them_all(baseline):
    assert baseline['"roles": 2'] == 'deferred+organiser-role+unmapped-cell'


def test_people_keyed_by_id_are_key_shape(baseline):
    assert baseline['"id": "sam-speaker",'] == 'key-shape'
    assert baseline['"id": "name:sam speaker",'] == 'key-shape'
    assert baseline['"bob r.": "bobroe",'] == 'key-shape'


def test_a_spelling_shown_by_the_display_name_is_display_name(baseline):
    assert baseline['"name": "Bob R.",'] == 'display-name'


def test_a_rank_moved_by_a_deferred_organisation_is_reordered(baseline):
    assert baseline['| 2 | Delta | Community Contributor | 2.5 |'] == 'reordered'


def test_an_unmapped_cell_the_old_mapping_filled_is_unmapped_cell(baseline):
    assert baseline['"organisation": "Unmapped",'] == 'unmapped-cell'
    assert baseline['"source": "https://example.org/t",'] == 'source-cut'


def test_an_unmapped_cell_without_the_old_mapping_is_unexplained(tmp_path):
    found = audited(tmp_path, old_mapping='Organisation,Team\nAcme,janedoe\nBeta Corp,\nDelta,\n')
    assert found['"organisation": "Unmapped",'] == audit.UNEXPLAINED


def change_beta(**values):
    def change(data):
        data['organisations']['beta-corp'].update(values)
    return change


@pytest.mark.parametrize('changes, wanted', [
    # the points of a category the deferral did not touch
    ({'page_change': lambda d: d['organisations']['beta-corp']['categories']['Training Session'].update(points=3.0)},
     '"points": 3.0'),
    # the total of a deferred organisation
    ({'page_change': change_beta(points=2.5)}, '"points": 2.5,'),
    # a line of the section of a deferred organisation that the deferral did not touch
    ({'md_change': lambda t: t.replace('| Training Session | 2.0 | • Intro Training |',
                                       '| Training Session | 3.0 | • Intro Training |')},
     '| Training Session | 3.0 | • Intro Training |'),
    # a line of the section of an organisation that is not deferred
    ({'md_change': lambda t: t.replace('| PR Contributions | 4.0 |', '| PR Contributions | 5.0 |')},
     '| PR Contributions | 5.0 | • Active Member (25.0 PRs/year) |'),
    # a count of the summary
    ({'md_change': lambda t: t.replace('**Total Organizations**: 3', '**Total Organizations**: 4')},
     '- **Total Organizations**: 4'),
    # a rank of the leaderboard
    ({'md_change': lambda t: t.replace('| 2 | Delta |', '| 5 | Delta |')},
     '| 5 | Delta | Community Contributor | 2.5 |'),
    # the level of a deferred row of the recognition CSV
    ({'csv_change': lambda t: t.replace('Beta Corp,Community Contributor', 'Beta Corp,Bronze Contributor')},
     'Beta Corp,Bronze Contributor,0,0,0,0,0,0,0,0,2.0,0,0,2.0'),
])
def test_a_number_the_deferral_does_not_give_is_unexplained(tmp_path, changes, wanted):
    found = audited(tmp_path, **changes)
    assert wanted in unexplained(found), sorted(unexplained(found))


def test_wall_points_other_than_the_page_points_are_unexplained(tmp_path):
    def change(data):
        for level in data['wall']:
            for entry in level['organisations']:
                if entry['name'] == 'Beta Corp':
                    entry['points'] = 2.5

    found = audited(tmp_path, page_change=change)
    assert '"points": 2.5,' in unexplained(found), sorted(unexplained(found))


@pytest.fixture
def with_gamma(monkeypatch):
    """Gamma, whose only credit is a second talk of Sam Speaker, deferred: it drops out of everything."""
    talk = {'file': TALKS, 'line': 3, 'points': 1, 'source': 'https://www.youtube.com/watch?v=vid2',
            'text': 'Gamma Talk'}
    monkeypatch.setitem(OLD_CURATED, TALKS, OLD_CURATED[TALKS]
                        + 'Gamma Talk,Sam Speaker,Gamma,Online,Talk,vid2,https://example.org/g,\n')
    monkeypatch.setitem(NEW_CURATED, TALKS,
                        NEW_CURATED[TALKS] + 'Gamma Talk,sam-speaker,,Talk,Online,https://example.org/g,\n')
    monkeypatch.setitem(NEW_CURATED, 'curated/mappings/organisations.csv',
                        NEW_CURATED['curated/mappings/organisations.csv'] + 'gamma,Gamma,organisation,,\n')
    monkeypatch.setitem(NEW_CURATED, 'curated/mappings/affiliation_proposals.csv',
                        NEW_CURATED['curated/mappings/affiliation_proposals.csv']
                        + f'sam-speaker,gamma,2025,2025,{TALKS}:3; https://example.org/g\n')
    monkeypatch.setitem(POINTS['old'], 'Gamma', {'WPD Talk': 1.0})
    monkeypatch.setitem(DETAILS['old'], 'Gamma', {'WPD Talk': ['Gamma Talk']})
    monkeypatch.setitem(CONTRIBUTIONS, 'Gamma', {'WPD Talk': [talk]})
    monkeypatch.setitem(ROLES['old'], 'Gamma', 1)


def test_an_organisation_whose_only_credit_is_deferred_drops_out(tmp_path, with_gamma):
    found = audited(tmp_path)
    assert not unexplained(found), sorted(unexplained(found))
    assert found['"gamma": {'] == 'deferred'
    assert found['Gamma,Community Contributor,0,0,0,0,0,0,1.0,0,0,0,0,1.0'] == 'deferred'
    assert found['### Gamma'] == 'deferred'
    assert found['| 4 | Gamma | Community Contributor | 1.0 |'] == 'deferred'


def test_a_dropped_organisation_with_other_commits_is_unexplained(tmp_path, with_gamma):
    def change(data):
        data['organisations']['gamma']['history']['2025']['commits'] = 5

    found = audited(tmp_path, old_page_change=change)
    assert '"commits": 5,' in unexplained(found), sorted(unexplained(found))


AUDIT_REGISTERS = {
    'curated/mappings/people.csv': 'id,name,github,source\n',
    'curated/mappings/identities.csv': 'person,kind,value,source\n',
    'curated/mappings/affiliations.csv': 'person,organisation,from,to,source,checked,notes\n',
    'curated/mappings/organisations.csv': 'id,name,kind,aliases,notes\n',
    'curated/mappings/affiliation_proposals.csv': 'person,organisation,from,to,evidence\n',
}


def committed_repo(root, files):
    """A git repository with empty registers and the files committed on main."""
    git(root, 'init', '-q', '-b', 'main')
    write(root, {**AUDIT_REGISTERS, **files})
    git(root, 'add', '.')
    git(root, 'commit', '-q', '-m', 'base')


def test_nothing_to_compare_exits_1(tmp_path, capsys):
    committed_repo(tmp_path, {'reports/r.md': 'A report.\n'})
    with pytest.raises(SystemExit) as stop:
        migrate_data_structure.main(['audit', '--root', str(tmp_path), '--from', 'HEAD'])
    assert stop.value.code == 1
    assert 'Nothing to compare' in capsys.readouterr().out


OLD_SENTENCE = 'Names that no mapping file links to a person yet are shown as written.'
NEW_SENTENCE = 'Names that no identity links to a person yet are shown as written.'
HEADERS = ('| Rank | Contributor | PRs | Commits | Repositories |',
           '| Rank | Organization | PRs | Commits | Contributors | Repositories |')


def reworded(root, old_code, new_code, old_report, new_report):
    """The audit, over its default range (the merge base with main), of a branch that changed the report code
    and then the report."""
    committed_repo(root, {'scripts/report/gen.py': old_code, 'reports/r.md': old_report})
    git(root, 'checkout', '-q', '-b', 'feature')
    write(root, {'scripts/report/gen.py': new_code})
    git(root, 'commit', '-q', '-a', '-m', 'reword')
    write(root, {'reports/r.md': new_report})
    return {excerpt.split(': ', 1)[1]: kind for _, kind, excerpt in audit.audit(root)}


def test_a_sentence_the_code_reworded_is_wording(tmp_path):
    found = reworded(tmp_path, f'lines.append("{OLD_SENTENCE}")\n', f'lines.append("{NEW_SENTENCE}")\n',
                     f'# Report\n{OLD_SENTENCE}\n', f'# Report\n{NEW_SENTENCE}\n')
    assert found == {OLD_SENTENCE: 'wording', NEW_SENTENCE: 'wording'}


def test_a_line_swapped_for_another_literal_is_unexplained(tmp_path):
    code = f'a = "{HEADERS[0]}"\nb = "{HEADERS[1]}"\n'
    found = reworded(tmp_path, code, code + '# a comment\n', f'# Report\n{HEADERS[0]}\n',
                     f'# Report\n{HEADERS[1]}\n')
    assert found == {HEADERS[0]: audit.UNEXPLAINED, HEADERS[1]: audit.UNEXPLAINED}


def test_the_audit_finds_a_person_by_a_one_word_display_name(tmp_repo):
    # The registry no longer matches "Danny" by the display name; the old files named him so all the same
    (tmp_repo / 'curated/mappings/people.csv').write_text(
        'id,name,github,source\ndanny,Danny,,https://example.org/d\njane-doe,Jane Doe,,https://example.org/j\n',
        encoding='utf-8')
    ctx = audit.Context(tmp_repo, base='main')
    assert ctx.registry.person_for(name='Danny') is None
    assert ctx.person_for_name('danny').id == 'danny'
    assert ctx.person_for_name('Jane Doe').id == 'jane-doe'
    assert ctx.person_for_name('Nobody') is None
