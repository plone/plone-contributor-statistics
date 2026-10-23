"""The attribution engine: which organisation a person counts for in a year, by the rules of attribution.md."""

import os
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, date, datetime

import pytest

from scripts.lib.model.attribution import Affiliation, Attribution, Citation
from scripts.lib.model.sources import Source
from tests.conftest import REPO

PERSON = 'p1'


def aff(org, start, end=None, status='stated', person=PERSON):
    return Affiliation(f'{person}-{org}-{start}-{end}-{status}', person, org, start, end, status, None, None)


def cite(affiliation, source, snippet='', supersedes=''):
    return Citation(affiliation.id, source, snippet, supersedes, None)


def src(sid, kind='page', on='2020-06-01', notes=None):
    return Source(sid, kind, sid, date.fromisoformat(on), f'https://example.org/{sid}', None,
                  datetime(2026, 10, 22, tzinfo=UTC), notes)


def engine(affiliations, citations=(), sources=(), excerpts=None, domains=None, name='Jane Doe',
           logins=('jdoe',), username='jdoe', organisations=None, organisation_names=None):
    """An engine over the rows; `domains` is {year: Counter} of the person, `organisations` {domain: org id}.

    `organisation_names` is {org id: [name, aliases]}; an organisation without an entry is named by its id.
    """
    organisations = organisations or {}
    domains = domains or {}

    def match_domain(domain):
        return (organisations[domain], 'alias') if domain in organisations else None

    return Attribution(
        affiliations, citations, {source.id: source for source in sources},
        excerpt=lambda sid: (excerpts or {}).get(sid, ''),
        commit_domains=lambda year: {username: domains[year]} if year in domains else {},
        match_domain=match_domain, name_of=lambda person: name, logins_of=lambda person: list(logins),
        username_of=lambda person: username,
        names_of_organisation=lambda org: (organisation_names or {}).get(org, [org]))


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


def test_commits_of_other_organisations_and_unmatched_domains_are_left_out():
    rows = [aff('acme', 2020, 2020), aff('beta', 2020, 2020)]
    organisations = {'acme.test': 'acme', 'beta.test': 'beta', 'gamma.test': 'gamma'}
    # gamma has no row: its commits don't count, and acme's one commit doesn't outnumber the two personal ones
    commits = Counter({'gamma.test': 10, 'acme.test': 1, 'gmail.com': 2})
    attribution = engine(rows, domains={2020: commits}, organisations=organisations)
    assert attribution.organisation(PERSON, 2020) is None
    # Unmatched company domains don't count either: acme's four commits outnumber the personal ones (none)
    commits = Counter({'acme.test': 4, 'nobody.test': 5})
    attribution = engine(rows, domains={2020: commits}, organisations=organisations)
    assert attribution.organisation(PERSON, 2020) == 'acme'


def test_own_statement_decides_when_most_commits_are_personal():
    acme, beta = aff('acme', 2019, 2020), aff('beta', 2019, 2020)
    citations = [cite(acme, 'talk'), cite(beta, 'old-profile'), cite(beta, 'team-page')]
    sources = [src('talk', 'speaker-page', '2020-10-01'), src('old-profile', 'profile', '2018-01-01'),
               src('team-page', 'page', '2019-02-01')]
    commits = {2020: Counter({'gmail.com': 8, 'acme.test': 1}), 2019: Counter({'gmail.com': 8})}
    attribution = engine([acme, beta], citations, sources, domains=commits, organisations={'acme.test': 'acme'})
    assert attribution.organisation(PERSON, 2020) == 'acme'
    # In 2019 no own statement of the year: the records of the year decide, only beta has one
    assert attribution.organisation(PERSON, 2019) == 'beta'


def test_own_domain_counts_as_personal():
    acme, beta = aff('acme', 2020, 2020), aff('beta', 2020, 2020)
    citations = [cite(beta, 'profile')]
    sources = [src('profile', 'profile', '2020-05-01')]
    commits = {2020: Counter({'vanrees.org': 6, 'acme.test': 2, 'beta.test': 1})}
    organisations = {'acme.test': 'acme', 'beta.test': 'beta'}
    kwargs = {'domains': commits, 'organisations': organisations, 'logins': ['mauritsvanrees'],
              'username': 'mauritsvanrees'}
    attribution = engine([acme, beta], citations, sources, name='Maurits van Rees', **kwargs)
    assert attribution.organisation(PERSON, 2020) == 'beta'  # mostly personal commits: his own profile decides
    stranger = engine([acme, beta], citations, sources, name='Jane Doe', **kwargs)
    assert stranger.organisation(PERSON, 2020) == 'acme'  # vanrees.org is unmatched and left out: commits decide


def test_more_records_decide():
    acme, beta = aff('acme', 2020, 2020), aff('beta', 2020, 2020)
    citations = [cite(acme, 'one'), cite(acme, 'one', 'another quote'), cite(beta, 'two'), cite(beta, 'three')]
    attribution = engine([acme, beta], citations, [src('one'), src('two'), src('three')])
    assert attribution.organisation(PERSON, 2020) == 'beta'


def test_records_of_the_year_decide():
    acme, beta = aff('acme', 2005, 2020), aff('beta', 2018)
    citations = [cite(acme, f'a{year}') for year in range(2005, 2010)] + [cite(beta, 'b2018')]
    sources = [src(f'a{year}', on=f'{year}-03-01') for year in range(2005, 2010)] + [src('b2018', on='2018-03-01')]
    attribution = engine([acme, beta], citations, sources)
    assert attribution.organisation(PERSON, 2018) == 'beta'
    assert attribution.organisation(PERSON, 2019) is None  # no records of 2019


@pytest.mark.parametrize('notes', ['not captured on 2026-10-22: nothing found', 'could not be fetched on 2026-10-22'])
def test_uncaptured_sources_are_no_records_and_no_statements(notes):
    acme, beta = aff('acme', 2026, 2026), aff('beta', 2026, 2026)
    uncaptured = src('gone', 'profile', '2026-10-22', notes)
    attribution = engine([acme, beta], [cite(acme, 'gone')], [uncaptured],
                         domains={2026: Counter({'gmail.com': 5})})
    assert attribution.organisation(PERSON, 2026) is None


def test_named_first_within_one_sentence():
    zest, kitconcept = aff('zest', 2023, 2023), aff('kitconcept', 2023, 2023)
    sentence = 'Nowadays he works for both Zest and Kitconcept'
    excerpt = f'Fred van Dijk is a Plone developer. {sentence}.'
    citations = [cite(zest, 'bio', sentence), cite(kitconcept, 'bio', sentence)]
    names = {'zest': ['Zest Software', 'Zest'], 'kitconcept': ['kitconcept GmbH', 'kitconcept']}
    attribution = engine([zest, kitconcept], citations, [src('bio', 'speaker-page', '2023-05-01')],
                         {'bio': excerpt}, organisation_names=names)
    assert attribution.organisation(PERSON, 2023) == 'zest'


def test_decisions_of_one_day_the_superseding_one_wins():
    acme, beta = aff('acme', 2010, 2012), aff('beta', 2010, 2012)
    for first, second in (('d1', 'd2'), ('d2', 'd1')):
        citations = [cite(acme, first), cite(beta, second, supersedes=first)]
        sources = [src(first, 'decision', '2026-01-10'), src(second, 'decision', '2026-01-10')]
        attribution = engine([acme, beta], citations, sources)
        assert attribution.organisation(PERSON, 2011) == 'beta'
        assert attribution.decision_errors() == []


def test_decision_errors_see_the_rows_that_count():
    acme, beta = aff('acme', 2010, 2012), aff('beta', 2011, 2013)
    denied = aff('beta', 2011, 2011, status='denied')
    citations = [cite(acme, 'first'), cite(beta, 'later')]
    sources = [src('first', 'decision', '2025-01-10'), src('later', 'decision', '2026-03-01')]
    attribution = engine([acme, beta, denied], citations, sources)
    assert attribution.organisation(PERSON, 2011) == 'acme'  # beta is denied in 2011, its decision with it
    assert attribution.decision_errors() == [
        'p1: the decision later (2026-03-01) does not name the earlier decision first (2025-01-10) in '
        '`supersedes`, for 2012']


def test_change_year_ignores_assumed_rows_around_it():
    rows = [aff('acme', 2010, 2015), aff('acme', 2016, 2016, status='assumed'), aff('beta', 2015)]
    attribution = engine(rows)
    assert attribution.organisation(PERSON, 2015) == 'acme'


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
            row = Affiliation(f'{person}-{year}', person, org, year, None if open_end else end,
                              rng.choice(['stated', 'assumed']), None, None)
            rows.append(row)
            if rng.random() < 0.3:  # another row of the same organisation over part of the years
                rows.append(Affiliation(f'{person}-{year}-again', person, org, year + rng.randint(0, end - year),
                                        row.to_year, rng.choice(['stated', 'assumed']), None, None))
            if rng.random() < 0.3:  # an organisation the person has no row for, denied
                rows.append(Affiliation(f'{person}-{year}-denied', person, 'zeta', year, end, 'denied', None, None))
            if rng.random() < 0.3:  # a proposal nobody reviewed
                rows.append(Affiliation(f'{person}-{year}-proposed', person, rng.choice(['beta', 'zeta']), year,
                                        end, 'proposed', None, None))
            if open_end:
                break
            year = end + 1 + rng.randint(0, 3)
    base = [row for row in rows if row.id.count('-') == 1]
    rng.shuffle(rows)
    citations = [Citation(row.id, f's{rng.randint(0, 5)}', '', '', None) for row in rows]
    sources = [src(f's{i}', rng.choice(['page', 'profile', 'speaker-page'])) for i in range(6)]
    commits = {year: Counter({'acme.test': rng.randint(0, 9), 'gmail.com': rng.randint(0, 9)})
               for year in range(1998, 2030)}
    attribution = engine(rows, citations, sources, domains=commits, organisations={'acme.test': 'acme'})
    for person in ('p1', 'p2', 'p3', 'p4'):
        for year in range(1998, 2030):
            assert attribution.organisation(person, year) == _first_match(base, person, year), (person, year)
    assert attribution.conflicts(until=2030) == []
    assert attribution.decision_errors() == []


IMPORT_FIRST = ['scripts.lib.commit_authors', 'scripts.lib.commit_domains', 'scripts.lib.model.attribution',
                'scripts.lib.capture']


def _fresh_import(module, root):
    return subprocess.run([sys.executable, '-c', f'import {module}'], cwd=root, capture_output=True, text=True,
                          env={**os.environ, 'PYTHONPATH': str(root)})


@pytest.mark.parametrize('module', IMPORT_FIRST)
def test_imports_in_a_fresh_interpreter(module):
    result = _fresh_import(module, REPO)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('module', IMPORT_FIRST)
def test_imports_when_the_model_imports_the_engine(module, tmp_path):
    """No import cycle once scripts.lib.model imports the engine, whichever module comes first."""
    shutil.copytree(REPO / 'scripts', tmp_path / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    init = tmp_path / 'scripts' / 'lib' / 'model' / '__init__.py'
    init.write_text(init.read_text(encoding='utf-8') + '\nfrom scripts.lib.model import attribution  # noqa\n',
                    encoding='utf-8')
    result = _fresh_import(module, tmp_path)
    assert result.returncode == 0, result.stderr
