"""The review list of the decisions: needed or outdated, and the sources recorded after them."""

from scripts.lib import paths
from scripts.lib.model import load_registry
from scripts.tools import decisions_review

DECISION = 'https://github.com/plone/plone-contributor-statistics/issues/1#issuecomment-1'
SOURCES = {  # id: (kind, date)
    'd00000000001': ('decision', '2026-10-20'),
    'd00000000002': ('decision', '2026-10-21'),
    'p00000000001': ('page', '2020-06-01'),  # dated in no year of the rows: no record for rule 6d
    'p00000000002': ('page', '2011-03-01'),
    'p00000000003': ('page', '2011-05-01'),
    'p00000000004': ('profile', '2026-10-22'),  # recorded after the decisions
}
ROWS = [  # id, person, organisation, from, to, status, cited sources
    ('a00000001', 'p1', 'acme', 2010, 2011, 'stated', ['d00000000001', 'p00000000001']),
    ('a00000002', 'p1', 'beta', 2010, 2011, 'stated', ['p00000000001', 'p00000000004']),
    ('a00000003', 'p2', 'acme', 2011, 2011, 'stated', ['d00000000001']),
    ('a00000004', 'p2', 'beta', 2011, 2011, 'stated', ['p00000000002', 'p00000000003']),
    ('a00000005', 'p3', 'beta', 2014, 2016, 'stated', ['p00000000001']),
    ('a00000006', 'p3', 'acme', 2015, 2015, 'denied', ['d00000000002']),  # acme has no counting row in 2015
    ('a00000007', 'p3', 'zeta', 2016, 2016, 'stated', ['p00000000001']),
    ('a00000008', 'p3', 'zeta', 2016, 2016, 'denied', ['d00000000002']),  # without it, beta and zeta tie
]


def write(tmp_repo, rows=ROWS):
    paths.PEOPLE.write_text('id,name\np1,P One\np2,P Two\np3,P Three\n', encoding='utf-8')
    paths.ORGANISATIONS.write_text('id,name,kind,github,aliases,notes\nacme,Acme,organisation,,,\n'
                                   'beta,Beta,organisation,,,\nzeta,Zeta,organisation,,,\n', encoding='utf-8')
    paths.SOURCES.write_text('id,kind,title,date,url,archive_url,fetched,notes\n' + ''.join(
        f'{sid},{kind},A record,{on},{DECISION if kind == "decision" else "https://example.org/" + sid},,'
        f'2026-10-22T10:00:00Z,\n' for sid, (kind, on) in sorted(SOURCES.items())), encoding='utf-8')
    paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n' + ''.join(
        f'{aid},{person},{org},{start},{end},{status},,\n' for aid, person, org, start, end, status, _ in rows),
        encoding='utf-8')
    paths.CITATIONS.write_text('affiliation,source,snippet,supersedes,notes\n' + ''.join(
        f'{aid},{sid},,,\n' for aid, *_, cited in rows for sid in cited), encoding='utf-8')
    return load_registry()


def entries(registry):
    return [(e['decision'], e['person'], e['first'], e['last'], e['row'].id, e['status'], e['now'], e['rules'],
             e['later']) for e in decisions_review.review(registry, until=2026)]


def test_a_needed_and_an_outdated_decision(tmp_repo):
    found = entries(write(tmp_repo))
    # No rule decides p1's years: the decision is needed and counts; its years are joined
    assert ('d00000000001', 'p1', 2010, 2011, 'a00000001', 'needed', 'Acme (decision)', 'open',
            ['p00000000004']) in found
    # Two records of 2011 name beta: rule 6d decides, the decision is outdated and not applied
    assert ('d00000000001', 'p2', 2011, 2011, 'a00000003', 'outdated', 'Beta (records)', 'Beta (records)',
            []) in found


def test_a_decision_of_a_denied_row(tmp_repo):
    found = entries(write(tmp_repo))
    # Without the denial the year counts the same: the counting does not need the decision
    assert ('d00000000002', 'p3', 2015, 2015, 'a00000006', 'outdated', 'Beta (one organisation)',
            'Beta (one organisation)', []) in found
    # Without the denial beta and zeta tie: the decision is needed
    assert ('d00000000002', 'p3', 2016, 2016, 'a00000008', 'needed', 'Beta (one organisation)', 'open', []) in found
    assert len(found) == 4


def test_a_later_source_is_listed(tmp_repo):
    registry = write(tmp_repo)
    assert decisions_review.later_sources(registry, 'p1', 2010, registry.sources['d00000000001'].date) == [
        'p00000000004']
    assert decisions_review.later_sources(registry, 'p1', 2010, registry.sources['p00000000004'].date) == []


def test_the_markdown_table(tmp_repo, capsys):
    assert decisions_review.main([]) == 0
    assert capsys.readouterr().out.startswith('# Decisions to review\n\nNo affiliation cites a decision.')
    write(tmp_repo)
    decisions_review.main([])
    lines = capsys.readouterr().out.splitlines()
    assert lines[2] == ('| Decision | Person | Years | Row | Status | Counts now | Rules without the decision '
                        '| Sources after the decision |')
    assert (f'| [d00000000001]({DECISION}) (2026-10-20) | p1 | 2010-2011 | a00000001 stated Acme | needed '
            '| Acme (decision) | open | p00000000004 (2026-10-22, profile) |') in lines


def test_open_cases_are_listed_next_to_the_decisions(tmp_repo, capsys):
    rows = ROWS + [('a00000009', 'p2', 'acme', 2012, 2014, 'stated', []),
                   ('a00000010', 'p2', 'zeta', 2012, 2013, 'stated', [])]
    registry = write(tmp_repo, rows)
    # p2 2012-2013: acme and zeta, no rule decides; p1 2010-2011 is decided by a decision, no open case
    assert decisions_review.open_cases(registry, until=2026) == [('p2', 2012, 2013, ['acme', 'zeta'])]
    decisions_review.main([])
    out = capsys.readouterr().out
    assert '## Open cases' in out
    assert '- p2, 2012-2013: open: no rule decides between Acme and Zeta' in out.splitlines()
