"""The migration of notes to data (plan 5): the fill rows go, their evidence moves to the records around them."""

from scripts.lib.model import (Affiliation, Citation, Organisation, Person, Registry, load_affiliations,
                               load_citations, write_affiliations, write_citations)
from scripts.tools import migrate_notes

S1, S2, S3 = '111111111111', '222222222222', '333333333333'


def row(id, start, end, notes=None, organisation='acme', status='stated', person='jane'):
    return Affiliation(id, person, organisation, start, end, status, None, notes)


def fill(id, start, end, before, after, organisation='acme'):
    return row(id, start, end, f'between records of {before} and {after} of the same organisation', organisation)


def cite(affiliation, source, snippet=None, notes=None):
    return Citation(affiliation, source, snippet, None, notes)


def counting(affiliations, citations, years):
    """{year: organisation} of jane, as the rules give it."""
    registry = Registry([Person('jane', 'Jane')], [], affiliations,
                        [Organisation('acme', 'Acme', 'organisation', None, (), None),
                         Organisation('other', 'Other', 'organisation', None, (), None)], citations)
    return {year: registry.organisation_of('jane', year) for year in years}


def test_a_fill_row_goes_and_its_notes_move_to_the_nearer_neighbour():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2014), row('a03', 2014, 2015, 'kept')]
    citations = [cite('a01', S1), cite('a02', S1), cite('a03', S2)]
    plan = migrate_notes.plan_fills(affiliations, citations)
    assert [(f.row.id, f.left.id, f.right.id, f.target.id) for f in plan.removed] == [('a02', 'a01', 'a03', 'a01')]
    assert plan.kept == []
    new_affiliations, new_citations = migrate_notes.apply_fills(affiliations, citations, plan)
    assert [a.id for a in new_affiliations] == ['a01', 'a03']
    assert new_affiliations[0].notes == 'bridged 2011-2011: between records of 2010 and 2014 of the same organisation'
    assert new_affiliations[1].notes == 'kept'
    # S1 is on the neighbour already: nothing to move
    assert new_citations == [cite('a01', S1), cite('a03', S2)]
    assert counting(new_affiliations, new_citations, range(2009, 2017)) == counting(
        affiliations, citations, range(2009, 2017))


def test_a_fill_rows_own_source_moves_to_a_neighbour():
    affiliations = [row('a01', 2010, 2010, 'a record'), fill('a02', 2012, 2013, 2010, 2014), row('a03', 2014, 2014)]
    citations = [cite('a01', S1), cite('a02', S2), cite('a02', S3, 'Jane works at Acme', 'cited as: profile'),
                 cite('a03', S2)]
    plan = migrate_notes.plan_fills(affiliations, citations)
    (removed,) = plan.removed
    assert removed.target.id == 'a03'  # one year away, the record before is two
    assert removed.moved == (cite('a02', S3, 'Jane works at Acme', 'cited as: profile'),)
    assert removed.on_neighbour == (cite('a02', S2),)
    new_affiliations, new_citations = migrate_notes.apply_fills(affiliations, citations, plan)
    assert sorted(new_citations, key=lambda c: (c.affiliation, c.source)) == [
        cite('a01', S1), cite('a03', S2), cite('a03', S3, 'Jane works at Acme', 'cited as: profile')]
    assert [a.notes for a in new_affiliations] == [
        'a record', 'bridged 2012-2013: between records of 2010 and 2014 of the same organisation']


def test_a_source_cited_with_another_snippet_moves_too():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2012), row('a03', 2012, 2012)]
    citations = [cite('a01', S1, 'one quote'), cite('a02', S1, 'another quote'), cite('a03', S2)]
    (removed,) = migrate_notes.plan_fills(affiliations, citations).removed
    assert removed.moved == (cite('a02', S1, 'another quote'),)


def test_a_citation_that_a_record_says_already_goes():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2013), row('a03', 2013, 2013)]
    citations = [cite('a01', S1, 'Jane works at Acme', 'cited as: profile; commits in 2010'),
                 cite('a02', S1, None, 'cited as: profile'), cite('a02', S2, None, 'cited as: a page'),
                 cite('a03', S2, 'a quote', 'cited as: another page')]
    (removed,) = migrate_notes.plan_fills(affiliations, citations).removed
    # The snippet and the longer notes of a01 say all the first one says; a03's notes don't say the second's
    assert removed.on_neighbour == (cite('a02', S1, None, 'cited as: profile'),)
    assert removed.moved == (cite('a02', S2, None, 'cited as: a page'),)


def test_a_tie_goes_to_the_later_neighbour():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2012), row('a03', 2012, 2012)]
    (removed,) = migrate_notes.plan_fills(affiliations, []).removed
    assert removed.target.id == 'a03'


def test_a_fill_row_without_both_neighbours_stays():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2012),
                    row('a03', 2012, 2012, organisation='other'), fill('a04', 2013, 2013, 2012, 2014, 'other'),
                    row('a05', 2014, 2014, status='assumed', organisation='other')]
    citations = [cite('a01', S1), cite('a02', S1), cite('a03', S2), cite('a04', S2), cite('a05', S2)]
    plan = migrate_notes.plan_fills(affiliations, citations)
    assert plan.removed == []
    assert [(f.row.id, f.reason) for f in plan.kept] == [
        ('a02', 'no record of acme after 2011'), ('a04', 'no record of other after 2013')]
    assert migrate_notes.apply_fills(affiliations, citations, plan) == (affiliations, citations)


def test_a_fill_row_across_a_record_of_another_organisation_or_a_denial_stays():
    affiliations = [row('a01', 2010, 2010), row('a02', 2011, 2011, organisation='other'),
                    fill('a03', 2012, 2012, 2010, 2013), row('a04', 2013, 2013),
                    fill('a05', 2014, 2014, 2013, 2016), row('a06', 2015, 2015, status='denied'),
                    row('a07', 2016, 2016)]
    plan = migrate_notes.plan_fills(affiliations, [])
    assert plan.removed == []
    assert [(f.row.id, f.reason) for f in plan.kept] == [
        ('a03', 'a stated row of other covers 2011'), ('a05', 'a denied row of acme covers 2015')]


def test_fill_rows_next_to_each_other_bridge_between_the_records():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2012), fill('a03', 2012, 2012, 2011, 2014),
                    row('a04', 2014, 2014)]
    citations = [cite('a01', S1), cite('a02', S1), cite('a03', S2), cite('a04', S1)]
    plan = migrate_notes.plan_fills(affiliations, citations)
    assert [(f.row.id, f.left.id, f.right.id, f.target.id) for f in plan.removed] == [
        ('a02', 'a01', 'a04', 'a01'), ('a03', 'a01', 'a04', 'a04')]
    new_affiliations, new_citations = migrate_notes.apply_fills(affiliations, citations, plan)
    assert [a.id for a in new_affiliations] == ['a01', 'a04']
    assert new_citations == [cite('a01', S1), cite('a04', S1), cite('a04', S2)]
    assert counting(new_affiliations, new_citations, range(2009, 2016)) == counting(
        affiliations, citations, range(2009, 2016))


def test_two_fill_rows_on_one_neighbour_keep_both_notes():
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2012), row('a03', 2012, 2012, 'record'),
                    fill('a04', 2013, 2013, 2012, 2015), row('a05', 2015, 2015)]
    plan = migrate_notes.plan_fills(affiliations, [])
    assert [f.target.id for f in plan.removed] == ['a03', 'a03']
    new_affiliations, _ = migrate_notes.apply_fills(affiliations, [], plan)
    assert [a.notes for a in new_affiliations if a.id == 'a03'] == [
        'record; bridged 2011-2011: between records of 2010 and 2012 of the same organisation; '
        'bridged 2013-2013: between records of 2012 and 2015 of the same organisation']
    # The notes kept on the record don't make it a fill row
    assert migrate_notes.plan_fills(new_affiliations, []) == migrate_notes.FillPlan([], [])


def test_main_lists_the_rows_and_writes_only_with_write(write_registers, capsys):
    write_registers(people=[('jane', None)], organisations=[('acme', 'Acme')])
    affiliations = [row('a01', 2010, 2010), fill('a02', 2011, 2011, 2010, 2014), row('a03', 2014, 2014)]
    citations = [cite('a01', S1), cite('a02', S3, None, 'cited as: profile'), cite('a03', S2)]
    write_affiliations(affiliations)
    write_citations(citations)
    assert migrate_notes.main(['fills']) == 0
    out = capsys.readouterr().out
    assert 'remove a02 jane acme 2011-2011' in out
    assert f'move {S3} -> a01' in out
    assert 'dry run' in out
    assert load_affiliations() == affiliations
    assert migrate_notes.main(['fills', '--write']) == 0
    assert [a.id for a in load_affiliations()] == ['a01', 'a03']
    assert cite('a01', S3, None, 'cited as: profile') in load_citations()
    capsys.readouterr()
    assert migrate_notes.main(['fills']) == 0  # a second run finds nothing
    assert 'fill rows: 0, removed 0, kept 0' in capsys.readouterr().out
