"""The migration of notes to data (plan 5): the fill rows go, their evidence moves to the records around them."""

import datetime

import pytest

from scripts.lib.model import (Affiliation, Citation, Identity, Organisation, Person, Registry, affiliation_id,
                               load_affiliations, load_citations, load_identities, write_affiliations,
                               write_citations, write_identities)
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


# The SVN users in the notes of identities

PAUL = 'paul-everitt'


def address(person, value, source, notes, kind='email'):
    return Identity(person, kind, value, source, value if kind == 'email' else None, notes)


def commit(author):
    return lambda source: f'Author: {author} <{author}@localhost>\nDate: 2008-07-28T21:01:55+00:00\n\nA change\n'


def test_two_svn_users_of_one_person_become_two_identities():
    identities = [address(PAUL, 'paul@localhost', S1, 'SVN user paul: in diazo the same commits exist as zopepaul'),
                  address(PAUL, 'zopepaul@localhost', S2, 'Review in #69; SVN user zopepaul, founder of Zope')]
    excerpts = {S1: commit('paul')(S1), S2: 'a page without the user'}
    plan = migrate_notes.plan_svn(identities, excerpts.get)
    assert plan.added == [
        Identity(PAUL, 'svn', 'paul', S1, 'Author: paul <paul@localhost>',
                 'SVN user paul: in diazo the same commits exist as zopepaul'),
        Identity(PAUL, 'svn', 'zopepaul', S2, None, 'SVN user zopepaul, founder of Zope')]
    assert plan.errors == []


def test_one_svn_user_on_two_addresses_becomes_one_identity():
    identities = [address('alex', 'aclark@3b4cdb85-528f-c531-b63d-5919d5b1aa08', S1, 'Review in #69; SVN user aclark'),
                  address('alex', 'aclark@db7f04ef-aaf3-0310-a811-c281ed44c4ad', S2, 'Review in #69; SVN user aclark')]
    plan = migrate_notes.plan_svn(identities, lambda source: '')
    assert plan.added == [Identity('alex', 'svn', 'aclark', S1, None, 'SVN user aclark')]
    assert [identity.value for identity in plan.found['alex', 'aclark']] == [identities[0].value, identities[1].value]


def test_svn_user_is_this_login_takes_the_login():
    identities = [address('jan', 'jjmurre@localhost', S1, 'Review in #69; SVN user is this login; example commit'),
                  address('jan', 'jjmurre', S1, 'Review in #69; SVN user is this login; example commit', kind='name')]
    plan = migrate_notes.plan_svn(identities, commit('jjmurre'))
    assert plan.added == [Identity('jan', 'svn', 'jjmurre', S1, 'Author: jjmurre <jjmurre@localhost>',
                                   'SVN user is this login')]


def test_an_svn_user_recorded_already_is_not_added_again():
    identities = [address('alex', 'aclark@localhost', S1, 'SVN user aclark'),
                  Identity('alex', 'svn', 'aclark', S1, None, 'SVN user aclark')]
    assert migrate_notes.plan_svn(identities, lambda source: '').added == []


def test_an_svn_user_of_two_people_is_an_error():
    identities = [address('alex', 'aclark@localhost', S1, 'SVN user aclark'),
                  address('other', 'aclark@example.org', S2, 'SVN user AClark')]
    plan = migrate_notes.plan_svn(identities, lambda source: '')
    assert plan.errors == ['the SVN user AClark of other is the SVN user aclark of alex']


def test_main_svn_writes_the_identities(write_registers, capsys):
    write_registers(people=[(PAUL, None)])
    identities = [address(PAUL, 'paul@localhost', S1, 'SVN user paul'),
                  address(PAUL, 'zopepaul@localhost', S2, 'SVN user zopepaul')]
    write_identities(identities)
    assert migrate_notes.main(['svn']) == 0
    assert f'add {PAUL} svn paul (source {S1}, no snippet)' in capsys.readouterr().out
    assert load_identities() == identities
    assert migrate_notes.main(['svn', '--write']) == 0
    assert [(i.kind, i.value) for i in load_identities()] == [
        ('email', 'paul@localhost'), ('email', 'zopepaul@localhost'), ('svn', 'paul'), ('svn', 'zopepaul')]
    capsys.readouterr()
    assert migrate_notes.main(['svn']) == 0
    assert 'svn identities: 0 to add' in capsys.readouterr().out


# The conflicting records of `not applied` and `Kept, not deciding` notes

ARCHIVED = 'https://web.archive.org/web/20120105050017/http://conf.example.org/event/1'
LIVE = 'https://conf.example.org/speakers/jane'
SEARCH = 'https://github.com/search?q=author%3Ajane+org%3Aother+committer-date%3A2019-01-01..2019-12-31&type=commits'
NOT_APPLIED = f'not applied, the verified row stands: "Company Other", Plone Conference 2011 speaker page: {ARCHIVED}'
KEPT = (f'2019: two organisations, the rule decides. Kept, not deciding: Commits in the GitHub organisation @other in '
        f'2019 (28 in 2019; search: {SEARCH}); "CTO at Zeta Labs", Plone Conference 2019 speaker page: {LIVE} '
        f'(Jens, #171)')


def organisations():
    return [Organisation('acme', 'Acme', 'organisation', None, (), None),
            Organisation('other', 'Other', 'organisation', 'other', (), None),
            Organisation('zeta', 'Zeta Labs', 'organisation', None, ('zeta',), None),
            Organisation('clearwind-consulting', 'Clearwind Consulting', 'organisation', None, (), None),
            Organisation('plone-foundation', 'Plone Foundation', 'foundation', None, (), None),
            Organisation('jane-independent', 'Jane (independent)', 'independent', None, (), None)]


def world(affiliations, citations=(), sources=(), excerpts=None, domains=None):
    """A registry of jane over the rows; sources are Source rows, excerpts {source id: text}."""
    excerpts = excerpts or {}
    register = {source.id: source for source in sources}
    return Registry([Person('jane', 'Jane Doe')], [], affiliations, organisations(),
                    attribution_inputs=lambda: (list(citations), register, lambda sid: excerpts.get(sid, ''),
                                                lambda year: (domains or {}).get(year, {})))


def source(url, on, kind='speaker-page', notes=None):
    from scripts.lib.model import Source, source_id, split_archive_url

    original, stamp = split_archive_url(url) or (url, None)
    return Source(source_id(original, stamp), kind, 'A page', datetime.date.fromisoformat(on), original,
                  url if stamp else None, datetime.datetime(2026, 10, 22, tzinfo=datetime.UTC), notes)


def test_a_not_applied_note_names_one_record():
    (record,) = migrate_notes.records_of(row('a01', 2011, 2013, NOT_APPLIED))
    assert record.quote == 'Company Other'
    assert record.url == ARCHIVED
    assert record.label == 'Plone Conference 2011 speaker page'
    assert record.text == f'"Company Other", Plone Conference 2011 speaker page: {ARCHIVED}'
    assert record.clause == NOT_APPLIED


def test_a_kept_note_names_each_record_after_the_marker_with_the_attribution():
    first, second = migrate_notes.records_of(row('a01', 2019, 2019, KEPT))
    assert first.quote is None
    assert first.url == SEARCH
    assert first.text == f'Commits in the GitHub organisation @other in 2019 (28 in 2019; search: {SEARCH})'
    assert first.clause == f'Kept, not deciding: {first.text} (Jens, #171)'
    assert second.quote == 'CTO at Zeta Labs'
    assert second.url == LIVE
    assert second.clause == f'Kept, not deciding: "CTO at Zeta Labs", Plone Conference 2019 speaker page: {LIVE} ' \
                            f'(Jens, #171)'


def test_notes_without_a_record_name_none():
    assert migrate_notes.records_of(row('a01', 2011, 2011, 'between records of 2010 and 2012 of the same '
                                                           'organisation')) == []
    assert migrate_notes.records_of(row('a01', 2011, 2011, None)) == []


def test_a_record_becomes_a_stated_row_of_the_organisation_it_names_for_the_year_of_its_label():
    page = source(ARCHIVED, '2012-01-05')  # archived after the conference: the label gives the year
    verified = row('a01', 2011, 2013, NOT_APPLIED)
    registry = world([verified], sources=[page], excerpts={page.id: 'Jane Doe\nCompany Other\n'})
    (proposal,) = migrate_notes.plan_conflicts(registry)
    assert (proposal.organisation, proposal.how, proposal.years) == ('other', 'named', (2011, 2011))
    assert proposal.check == ()
    assert proposal.row == Affiliation(affiliation_id('jane', 'other', 2011, 2011), 'jane', 'other', 2011, 2011,
                                       'stated', None, NOT_APPLIED)
    assert proposal.citation == Citation(proposal.row.id, page.id, 'Company Other', None,
                                         f'cited as: "Company Other", Plone Conference 2011 speaker page: {ARCHIVED}')


def test_a_quote_the_excerpt_does_not_hold_is_no_snippet():
    page = source(ARCHIVED, '2012-01-05')
    registry = world([row('a01', 2011, 2013, NOT_APPLIED)], sources=[page], excerpts={page.id: 'Another text\n'})
    (proposal,) = migrate_notes.plan_conflicts(registry)
    assert proposal.citation.snippet is None
    assert proposal.check == ('the quote is not in the excerpt of the source',)


def test_a_source_not_in_the_register_is_listed_and_the_row_has_no_citation():
    page = source(LIVE, '2019-10-21')
    registry = world([row('a01', 2019, 2019, KEPT, organisation='acme')], sources=[page],
                     excerpts={page.id: 'CTO at Zeta Labs\n'})
    commits, talk = migrate_notes.plan_conflicts(registry)
    assert (commits.organisation, commits.how, commits.years, commits.source) == ('other', 'named', (2019, 2019),
                                                                                  None)
    assert commits.citation is None
    assert commits.check == ('no source of the address in the register: capture it first',)
    assert (talk.organisation, talk.years, talk.citation.snippet) == ('zeta', (2019, 2019), 'CTO at Zeta Labs')


def test_without_a_year_in_the_label_the_date_of_the_source_gives_it():
    note = f'not applied, the verified row stands: "Jane Doe, Other", the team page: {LIVE}'
    page = source(LIVE, '2016-03-01', kind='page')
    (proposal,) = migrate_notes.plan_conflicts(world([row('a01', 2016, 2016, note)], sources=[page]))
    assert proposal.years == (2016, 2016)


def test_an_organisation_named_by_its_first_word_or_a_freelancer_is_a_candidate_to_check():
    first = f'not applied, the verified row stands: "Jane Doe, ClearWind", Plone Conference 2003 speaker page: {LIVE}'
    free = (f'not applied, the verified row stands: "Jane worked at several companies and is now working as a '
            f'freelancer.", Plone Conference 2024 speaker page: {ARCHIVED}')
    registry = world([row('a01', 2003, 2003, first), row('a02', 2024, 2024, free),
                      row('a03', 2018, 2020, organisation='jane-independent')])
    clearwind, freelancer = migrate_notes.plan_conflicts(registry)
    assert (clearwind.organisation, clearwind.how) == ('clearwind-consulting', 'first word')
    assert 'check the organisation: found by the first word of its name' in clearwind.check
    assert (freelancer.organisation, freelancer.how) == ('jane-independent', 'freelancer')
    assert 'check the organisation: a freelancer, the independent organisation of the person' in freelancer.check


def test_an_unclear_organisation_is_listed_without_a_row():
    note = f'not applied, the verified row stands: "Jane Doe, Somewhere Unknown", Plone Conference 2011: {LIVE}'
    both = f'not applied, the verified row stands: "Jane Doe, Acme and Zeta Labs", Plone Conference 2012: {LIVE}'
    unknown, two = migrate_notes.plan_conflicts(world([row('a01', 2011, 2011, note, organisation='other'),
                                                       row('a02', 2012, 2012, both, organisation='other')]))
    assert unknown.organisation is None and unknown.row is None
    assert unknown.how == 'no organisation of the register is named'
    assert two.organisation is None and two.how == 'several organisations are named: acme, zeta'


def test_the_foundation_named_beside_an_organisation_is_left_out():
    note = (f'Kept, not deciding: "Plone Foundation Member - Founder of iskra.cat and zeta.example", Plone '
            f'Conference 2020 speaker page: {LIVE}')
    (proposal,) = migrate_notes.plan_conflicts(world([row('a01', 2020, 2020, note)]))
    assert proposal.organisation == 'zeta'
    assert 'the record also names Plone Foundation' in proposal.check


def test_the_dry_run_lists_before_and_after_and_drafts_the_changes():
    page = source(ARCHIVED, '2012-01-05')
    affiliations = [row('a00', 2010, 2010, organisation='other'), row('a01', 2011, 2013, NOT_APPLIED)]
    registry = world(affiliations, sources=[page], excerpts={page.id: 'Company Other\n'})
    plan = migrate_notes.plan_conflicts(registry)
    results = migrate_notes.dry_run(registry, plan, credited={('jane', 2011): {'commits': 3}}, until=2014)
    by_year = {result.year: result for result in results}
    # Other covers 2010 and 2011, Acme 2011 to 2013: the person leaves Other during 2011 (change year)
    assert (by_year[2011].before, by_year[2011].after, by_year[2011].rule) == ('acme', 'other', 'change year')
    assert by_year[2011].changed and not by_year[2011].conflict
    assert by_year[2011].activity == '3 commits'
    assert not by_year[2012].changed
    text = migrate_notes.drafts(registry, plan, results)
    assert text.count('\n## ') == 1
    assert '## Jane Doe 2011: Acme' in text
    assert 'Company Other' in text and ARCHIVED in text
    assert 'the rules give **Other** (change year)' in text
    assert 'a decision cannot keep Acme' in text
    assert 'Change year (rule 4): in 2010 **Other**, in 2012 **Acme**.' in text


def test_the_dry_run_marks_a_conflict():
    talk, team = source(LIVE, '2019-10-21'), source('https://acme.example.org/team', '2019-05-01', kind='page')
    affiliations = [row('a01', 2019, 2019, f'Kept, not deciding: "CTO at Zeta Labs", Plone Conference 2019 '
                                           f'speaker page: {LIVE}')]
    registry = world(affiliations, [cite('a01', team.id)], sources=[talk, team],
                     excerpts={talk.id: 'CTO at Zeta Labs\n', team.id: 'Jane Doe\n'})
    plan = migrate_notes.plan_conflicts(registry)
    (result,) = [r for r in migrate_notes.dry_run(registry, plan, credited={}, until=2019) if r.year == 2019]
    # one record of the year each, no commits: no rule decides
    assert (result.before, result.after, result.rule, result.conflict) == ('acme', None, 'conflict',
                                                                           ('acme', 'zeta'))
    assert result.changed
    text = migrate_notes.drafts(registry, plan, [result])
    assert '## Jane Doe 2019: Acme' in text
    assert 'no rule decides: a conflict between **Acme** and **Zeta Labs**' in text
    assert 'Records (rule 6d): captured sources dated 2019: Acme 1, Zeta Labs 1.' in text
    assert '**Proposed decision.** Jane Doe counts for **Acme** in 2019' in text


def test_main_conflicts_is_a_dry_run_and_writes_the_drafts(write_registers, tmp_path, capsys):
    write_registers(people=[('jane', None)], organisations=[('acme', 'Acme'), ('other', 'Other')])
    write_affiliations([row('a00', 2010, 2010, organisation='other'), row('a01', 2011, 2013, NOT_APPLIED)])
    out_file = tmp_path / 'drafts.md'
    assert migrate_notes.main(['conflicts', '--drafts', str(out_file)]) == 0
    out = capsys.readouterr().out
    assert 'jane 2011: Acme (one organisation) -> Other (change year)' in out
    assert 'no source of the address in the register' in out
    assert '## jane 2011: Acme' in out_file.read_text(encoding='utf-8')
    assert [a.id for a in load_affiliations()] == ['a00', 'a01']  # nothing written


def test_main_conflicts_refuses_to_write(write_registers):
    write_registers(people=[('jane', None)], organisations=[('acme', 'Acme')])
    with pytest.raises(SystemExit):
        migrate_notes.main(['conflicts', '--write'])
