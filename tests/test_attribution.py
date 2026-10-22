"""The attribution engine: which organisation a person counts for in a year, by the rules of attribution.md."""

import random
from collections import Counter
from datetime import UTC, date, datetime

import pytest

from scripts.lib.model.attribution import Affiliation, Attribution, Citation
from scripts.lib.model.sources import Source

PERSON = 'p1'


def aff(org, start, end=None, status='stated', person=PERSON):
    return Affiliation(f'{person}-{org}-{start}-{end}-{status}', person, org, start, end, status, None, None)


def cite(affiliation, source, snippet='', supersedes=''):
    return Citation(affiliation.id, source, snippet, supersedes, None)


def src(sid, kind='page', on='2020-06-01'):
    return Source(sid, kind, sid, date.fromisoformat(on), f'https://example.org/{sid}', None,
                  datetime(2026, 10, 22, tzinfo=UTC), None)


def engine(affiliations, citations=(), sources=(), excerpts=None, domains=None, name='Jane Doe',
           logins=('jdoe',), username='jdoe', organisations=None):
    """An engine over the rows; `domains` is {year: Counter} of the person, `organisations` {domain: org id}."""
    organisations = organisations or {}
    domains = domains or {}

    def match_domain(domain):
        return (organisations[domain], 'alias') if domain in organisations else None

    return Attribution(
        affiliations, citations, {source.id: source for source in sources},
        excerpt=lambda sid: (excerpts or {}).get(sid, ''),
        commit_domains=lambda year: {username: domains[year]} if year in domains else {},
        match_domain=match_domain, name_of=lambda person: name, logins_of=lambda person: list(logins),
        username_of=lambda person: username)


def test_unmapped_without_rows():
    attribution = engine([aff('acme', 2010, 2012, person='other')])
    assert attribution.organisation(PERSON, 2011) is None
    assert attribution.organisation('other', 2013) is None
    assert attribution.conflicts() == []


def test_proposed_rows_are_ignored():
    attribution = engine([aff('acme', 2010, 2012), aff('beta', 2010, 2012, status='proposed')])
    assert attribution.organisation(PERSON, 2011) == 'acme'
    assert engine([aff('beta', 2010, status='proposed')]).organisation(PERSON, 2011) is None


def test_denied_removes_only_its_organisation():
    # Maurits: the Zest address of 2024-2025 is an old mailbox (denied); Py76 is stated for 2024 onwards
    rows = [aff('zest', 2005), aff('py76', 2024), aff('zest', 2024, 2025, status='denied')]
    attribution = engine(rows)
    assert attribution.organisation(PERSON, 2023) == 'zest'
    assert attribution.organisation(PERSON, 2024) == 'py76'
    assert attribution.organisation(PERSON, 2025) == 'py76'
    assert attribution.organisation(PERSON, 2026) is None  # zest and py76 again: no rule decides
    assert attribution.conflicts(until=2026) == [(PERSON, 2026, ['py76', 'zest'])]


def test_denied_without_organisation_is_ignored():
    attribution = engine([aff('acme', 2010, 2012), aff('', 2011, 2011, status='denied')])
    assert attribution.organisation(PERSON, 2011) == 'acme'


def test_decision_counts_before_every_other_rule():
    acme, beta = aff('acme', 2010, 2012), aff('beta', 2010, 2012)
    citations = [cite(acme, 'decided'), cite(beta, 'one'), cite(beta, 'two')]  # beta has more records
    attribution = engine([acme, beta], citations, [src('decided', 'decision'), src('one'), src('two')])
    assert attribution.organisation(PERSON, 2011) == 'acme'
    assert attribution.decision_errors() == []


def test_latest_decision_wins():
    acme, beta = aff('acme', 2010, 2012), aff('beta', 2010, 2012)
    citations = [cite(acme, 'first'), cite(beta, 'later', supersedes='first')]
    sources = [src('first', 'decision', '2025-01-10'), src('later', 'decision', '2026-03-01')]
    attribution = engine([acme, beta], citations, sources)
    assert attribution.organisation(PERSON, 2011) == 'beta'
    assert attribution.decision_errors() == []


def test_decisions_without_supersedes_are_reported():
    acme, beta = aff('acme', 2010, 2012), aff('beta', 2011, 2013)
    citations = [cite(acme, 'first'), cite(beta, 'later')]
    sources = [src('first', 'decision', '2025-01-10'), src('later', 'decision', '2026-03-01')]
    attribution = engine([acme, beta], citations, sources)
    assert attribution.organisation(PERSON, 2011) == 'beta'  # the latest still counts
    assert attribution.decision_errors() == [
        'p1: the decision later (2026-03-01) does not name the earlier decision first (2025-01-10) in '
        '`supersedes`, for 2011-2012']


def test_one_organisation_left_counts():
    attribution = engine([aff('acme', 2010, 2012), aff('acme', 2012, 2014, status='assumed')])
    assert attribution.organisation(PERSON, 2012) == 'acme'
    assert attribution.conflicts() == []


def test_stated_beats_assumed():
    attribution = engine([aff('acme', 2010, 2012, status='assumed'), aff('beta', 2012, 2014)])
    assert attribution.organisation(PERSON, 2012) == 'beta'


def test_change_year_counts_for_the_organisation_the_person_leaves():
    attribution = engine([aff('acme', 2010, 2015), aff('beta', 2015)])
    assert attribution.organisation(PERSON, 2015) == 'acme'
    assert attribution.organisation(PERSON, 2016) == 'beta'


def test_no_change_year_when_one_organisation_spans_both_sides():
    attribution = engine([aff('acme', 2010, 2015), aff('beta', 2005)])
    assert attribution.organisation(PERSON, 2015) is None


def test_named_first_in_the_same_source():
    acme, beta = aff('acme', 2023, 2023), aff('beta', 2023, 2023)
    excerpt = 'Nowadays he works for both Beta GmbH and Acme Ltd.'
    citations = [cite(acme, 'page', 'Acme Ltd'), cite(beta, 'page', 'works for both Beta GmbH')]
    attribution = engine([acme, beta], citations, [src('page')], {'page': excerpt})
    assert attribution.organisation(PERSON, 2023) == 'beta'


def test_named_first_needs_one_source_for_both():
    acme, beta = aff('acme', 2023, 2023), aff('beta', 2023, 2023)
    citations = [cite(acme, 'one', 'Acme'), cite(beta, 'two', 'Beta')]
    attribution = engine([acme, beta], citations, [src('one'), src('two')], {'one': 'x Acme', 'two': 'Beta'})
    assert attribution.organisation(PERSON, 2023) is None


def test_commits_decide_when_company_commits_are_the_majority():
    rows = [aff('acme', 2020, 2020), aff('beta', 2020, 2020)]
    commits = Counter({'acme.test': 6, 'beta.test': 2, 'gmail.com': 3})
    attribution = engine(rows, domains={2020: commits}, organisations={'acme.test': 'acme', 'beta.test': 'beta'})
    assert attribution.organisation(PERSON, 2020) == 'acme'


def test_commits_do_not_decide_without_a_majority_of_company_commits():
    rows = [aff('acme', 2020, 2020), aff('beta', 2020, 2020)]
    commits = Counter({'acme.test': 4, 'nobody.test': 5})  # unmatched company domains are not company commits
    attribution = engine(rows, domains={2020: commits}, organisations={'acme.test': 'acme'})
    assert attribution.organisation(PERSON, 2020) is None


def test_own_statement_decides_when_most_commits_are_personal():
    acme, beta = aff('acme', 2019, 2020), aff('beta', 2019, 2020)
    citations = [cite(acme, 'talk'), cite(beta, 'old-profile'), cite(beta, 'team-page')]
    sources = [src('talk', 'speaker-page', '2020-10-01'), src('old-profile', 'profile', '2018-01-01'),
               src('team-page', 'page', '2020-02-01')]
    commits = {2020: Counter({'gmail.com': 8, 'acme.test': 1}), 2019: Counter({'gmail.com': 8})}
    attribution = engine([acme, beta], citations, sources, domains=commits, organisations={'acme.test': 'acme'})
    assert attribution.organisation(PERSON, 2020) == 'acme'
    # In 2019 no own statement of the year: the records decide, beta has more of them
    assert attribution.organisation(PERSON, 2019) == 'beta'


def test_own_domain_counts_as_personal():
    acme, beta = aff('acme', 2020, 2020), aff('beta', 2020, 2020)
    citations = [cite(acme, 'profile'), cite(beta, 'one'), cite(beta, 'two')]
    sources = [src('profile', 'profile', '2020-05-01'), src('one'), src('two')]
    commits = {2020: Counter({'vanrees.org': 6, 'acme.test': 2, 'beta.test': 1})}
    organisations = {'acme.test': 'acme', 'beta.test': 'beta'}
    kwargs = {'domains': commits, 'organisations': organisations, 'logins': ['mauritsvanrees'],
              'username': 'mauritsvanrees'}
    attribution = engine([acme, beta], citations, sources, name='Maurits van Rees', **kwargs)
    assert attribution.organisation(PERSON, 2020) == 'acme'  # personal majority: his own profile decides
    stranger = engine([acme, beta], citations, sources, name='Jane Doe', **kwargs)
    assert stranger.organisation(PERSON, 2020) == 'beta'  # vanrees.org is unmatched: no majority, records decide


def test_more_records_decide():
    acme, beta = aff('acme', 2020, 2020), aff('beta', 2020, 2020)
    citations = [cite(acme, 'one'), cite(acme, 'one', 'another quote'), cite(beta, 'two'), cite(beta, 'three')]
    attribution = engine([acme, beta], citations, [src('one'), src('two'), src('three')])
    assert attribution.organisation(PERSON, 2020) == 'beta'


def test_conflicts_list_the_undecided_years():
    rows = [aff('acme', 2020, 2022), aff('beta', 2021, 2021), aff('gamma', 2030, status='assumed'),
            aff('delta', 2030)]
    attribution = engine(rows)
    assert attribution.organisation(PERSON, 2021) is None
    assert attribution.conflicts(until=2031) == [(PERSON, 2021, ['acme', 'beta'])]


def _first_match(rows, person, year):
    """The lookup of the registers before the engine: the first row of the person that covers the year."""
    for row in rows:
        if row.person == person and row.covers(year):
            return row.organisation
    return None


@pytest.mark.parametrize('seed', range(50))
def test_non_overlapping_rows_equal_first_match(seed):
    rng = random.Random(seed)
    rows = []
    for person in ('p1', 'p2', 'p3'):
        year = rng.randint(2000, 2010)
        while year < 2026 and rng.random() < 0.8:
            end = year + rng.randint(0, 6)
            open_end = rng.random() < 0.15
            org = rng.choice(['acme', 'beta', 'gamma'])
            rows.append(Affiliation(f'{person}-{year}', person, org, year, None if open_end else end,
                                    rng.choice(['stated', 'assumed']), None, None))
            if open_end:
                break
            year = end + 1 + rng.randint(0, 3)
    rng.shuffle(rows)
    citations = [Citation(row.id, f's{rng.randint(0, 5)}', '', '', None) for row in rows]
    sources = [src(f's{i}', rng.choice(['page', 'profile', 'speaker-page'])) for i in range(6)]
    commits = {year: Counter({'acme.test': rng.randint(0, 9), 'gmail.com': rng.randint(0, 9)})
               for year in range(1998, 2030)}
    attribution = engine(rows, citations, sources, domains=commits, organisations={'acme.test': 'acme'})
    for person in ('p1', 'p2', 'p3', 'p4'):
        for year in range(1998, 2030):
            assert attribution.organisation(person, year) == _first_match(rows, person, year), (person, year)
    assert attribution.conflicts(until=2030) == []
    assert attribution.decision_errors() == []
