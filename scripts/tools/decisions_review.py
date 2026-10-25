#!/usr/bin/env python3
"""List every citation of a decision, for review: is the decision still needed, and what was recorded since?

Older decisions were taken with fewer recorded facts (docs/explanation/attribution.md). For each affiliation that
cites a source of kind `decision`, and each year of it, this prints a Markdown table row with

- the status: `needed` when the rules leave the year open without the decision, `outdated` when the rules decide
  it (rule 7: a decision settles only what the rules leave open, so an outdated decision is not applied). A
  decision cited by a `denied` row is what the denial rests on; it is `outdated` when the rules give the year the
  same organisation without the denied row, else `needed` (the denied row also keeps the evidence tools from
  proposing its reading again, which this does not weigh). A decision cited by a `proposed` row is not weighed;
- what the year counts for now, and what the rules alone give (`open` when they leave it open);
- the sources cited for that person and year whose date is after the date of the decision.

Years with the same cells are joined, such as 2011-2013.

Next to the decisions it lists the open cases: the years that no rule decides and no decision settles (rule 8);
they count as Unmapped until a decision settles them.
"""

import argparse
import sys
from collections import defaultdict
from datetime import date

from scripts.lib.model import UNMAPPED, load_registry
from scripts.lib.model.attribution import CONFLICT, COUNTING, DECIDED, DECISION, DENIED

NEEDED, OUTDATED, NOT_WEIGHED = 'needed', 'outdated', 'not weighed'
OPEN = 'open'
DENIAL_NOTE = ('A denied row also keeps the evidence tools from proposing its reading again; for a denied row, '
               '`outdated` says only that the counting does not need it.')
COLUMNS = ('Decision', 'Person', 'Years', 'Row', 'Status', 'Counts now', 'Rules without the decision',
           'Sources after the decision')


def _runs(years):
    """[(first, last)] of the runs of consecutive years."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return [tuple(run) for run in runs]


def _outcome(registry, explained):
    org, rule = explained
    return f'{registry.organisation_name(org) if org is not None else UNMAPPED} ({rule})'


def _by_rules(registry, explained):
    """The outcome of an explanation, or `open` when no rule decided it."""
    return OPEN if explained[1] in (DECIDED, CONFLICT) else _outcome(registry, explained)


def later_sources(registry, person, year, after):
    """The ids of the sources cited by the person's rows of the year (any status) dated after `after`, by date."""
    rows = {row.id for row in registry.affiliations if row.person == person and row.covers(year)}
    sources = registry.sources
    cited = {citation.source for citation in registry.citations
             if citation.affiliation in rows and citation.source in sources and sources[citation.source].date > after}
    return sorted(cited, key=lambda sid: (sources[sid].date, sid))


def review(registry, until=None):
    """[{decision, person, first, last, row, status, now, rules, later}] for every citation of a decision, the
    years of its row joined where the other values are the same."""
    until = until or date.today().year
    sources = registry.sources
    rows = {row.id: row for row in registry.affiliations}
    outdated = {(person, year, source) for person, year, source, _ in registry.attribution.outdated_decisions(until)}
    found = []
    decisions = {sid for sid, source in sources.items() if source.kind == DECISION}
    citing = sorted(((citation.source, rows[citation.affiliation]) for citation in registry.citations
                     if citation.affiliation in rows and citation.source in decisions),
                    key=lambda pair: (pair[0], pair[1].person, pair[1].from_year, pair[1].id))
    for source, row in citing:
        decided = sources[source].date
        without = registry.without_affiliations({row.id}) if row.status == DENIED else None
        per_year = {}
        for year in range(row.from_year, (row.to_year or until) + 1):
            now = registry.attribution.explain(row.person, year)
            if row.status == DENIED:
                alone = without.attribution.explain(row.person, year)
                rules = _by_rules(registry, alone)
                status = OUTDATED if rules != OPEN and alone[0] == now[0] else NEEDED
            elif row.status in COUNTING:
                status = OUTDATED if (row.person, year, source) in outdated else NEEDED
                rules = _by_rules(registry, now) if status == OUTDATED else OPEN
            else:
                status, rules = NOT_WEIGHED, _by_rules(registry, now)
            later = tuple(later_sources(registry, row.person, year, decided))
            per_year[year] = (status, _outcome(registry, now), rules, later)
        groups = defaultdict(list)
        for year, cells in per_year.items():
            groups[cells].append(year)
        entries = [(first, last, cells) for cells, years in groups.items() for first, last in _runs(years)]
        for first, last, (status, now, rules, later) in sorted(entries):
            found.append({'decision': source, 'person': row.person, 'first': first, 'last': last, 'row': row,
                          'status': status, 'now': now, 'rules': rules, 'later': list(later)})
    return found


def open_cases(registry, until=None):
    """[(person, first year, last year, [organisation ids])] of the years that no rule decides and no decision
    settles, consecutive years with the same organisations joined."""
    by_case = defaultdict(list)
    for person, year, organisations in registry.attribution.conflicts(until=until or date.today().year):
        by_case[(person, tuple(organisations))].append(year)
    return sorted((person, first, last, list(organisations)) for (person, organisations), years in by_case.items()
                  for first, last in _runs(years))


def _open_lines(registry, cases):
    lines = ['', '## Open cases', '']
    if not cases:
        return lines + ['None: the rules or a decision decide every year.']
    for person, first, last, organisations in cases:
        years = str(first) if first == last else f'{first}-{last}'
        names = [registry.organisation_name(org) for org in organisations]
        between = names[0] if len(names) == 1 else f'{", ".join(names[:-1])} and {names[-1]}'
        lines.append(f'- {person}, {years}: open: no rule decides between {between}')
    return lines


def markdown(registry, entries, cases=()):
    """The review as a Markdown table, with a heading, and the open cases."""
    lines = ['# Decisions to review', '']
    if not entries:
        return '\n'.join(lines + ['No affiliation cites a decision.'] + _open_lines(registry, cases)) + '\n'
    lines += ['| ' + ' | '.join(COLUMNS) + ' |', '|' + '---|' * len(COLUMNS)]
    sources = registry.sources
    for entry in entries:
        decision = sources[entry['decision']]
        row = entry['row']
        years = str(entry['first']) if entry['first'] == entry['last'] else f"{entry['first']}-{entry['last']}"
        later = '; '.join(f'{sid} ({sources[sid].date}, {sources[sid].kind})' for sid in entry['later']) or 'none'
        cells = [f'[{decision.id}]({decision.url}) ({decision.date})', entry['person'], years,
                 f'{row.id} {row.status} {registry.organisation_name(row.organisation) if row.organisation else "-"}',
                 entry['status'], entry['now'], entry['rules'], later]
        lines.append('| ' + ' | '.join(cell.replace('|', '\\|') for cell in cells) + ' |')
    if any(entry['row'].status == DENIED for entry in entries):
        lines += ['', DENIAL_NOTE]
    return '\n'.join(lines + _open_lines(registry, cases)) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    registry = load_registry()
    sys.stdout.write(markdown(registry, review(registry), open_cases(registry)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
