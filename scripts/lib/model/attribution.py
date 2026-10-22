"""The organisation a person counts for in a year, computed from the affiliations and the sources they cite.

The rules are those of docs/explanation/attribution.md, in this order:

1. A `proposed` row is ignored. A `denied` row removes its organisation from its years; a denied row without an
   organisation (a reviewed "stays Unmapped") is ignored here.
2. Decision: of the rows that cite a source of kind `decision`, the one with the latest decision (by the date
   of the source) counts; of two decisions of the same date, the one whose citation `supersedes` the other.
   A decision overrides every rule below.
3. One organisation: if one organisation is left, it counts. Stated rows win over assumed ones: when stated
   rows cover the year, the assumed ones drop out of the rules below (also for the years around it in rule 4).
4. Change year: of two organisations, if one also covers the year before and not the year after, and the other
   covers the year after and not the year before, the person leaves the first one during the year, and it counts.
5. Bridging is not computed: the rows already cover the years between two records of the same organisation.
6. Tie-breaks, among the organisations left (the candidates):
   a. named first: the rows of every candidate cite the same source with a snippet; the candidate whose snippet
      comes first in the excerpt of that source counts. When the snippets start at the same place (one sentence
      names both), the candidate whose name (or alias) comes first in that sentence counts;
   b. commits: when the person's commits of the year under the domains of the candidates outnumber the commits
      under personal domains, the candidate with the most commits counts. Commits under other organisations and
      under company domains that no organisation claims are left out; a domain that no organisation claims but
      that is the person's own (`is_own_domain_for`, vanrees.org) is personal;
   c. own statement: when the personal commits outnumber the candidates' commits, the candidate that the
      person's own statements of the year name counts (citations of sources of kind `speaker-page` or
      `profile` dated in the year), if they name exactly one;
   d. records: the candidate that more distinct cited sources dated in the year name counts.
   Sources that were never captured (notes `not captured on …`) carry no text and only the capture day as their
   date: rules c and d leave them out.
7. Otherwise the year is a conflict: Unmapped, and listed by `conflicts`, until a decision settles it.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

STATED, ASSUMED, DENIED, PROPOSED = 'stated', 'assumed', 'denied', 'proposed'
COUNTING = (STATED, ASSUMED)
DECISION = 'decision'
OWN_STATEMENT_KINDS = ('speaker-page', 'profile')
UNCAPTURED = 'not captured on'


@dataclass(frozen=True)
class Affiliation:
    id: str
    person: str
    organisation: str
    from_year: int
    to_year: int | None
    status: str
    checked: object
    notes: str | None

    def covers(self, year):
        """Whether the affiliation holds in the year."""
        return self.from_year <= year and (self.to_year is None or year <= self.to_year)


@dataclass(frozen=True)
class Citation:
    affiliation: str
    source: str
    snippet: str | None
    supersedes: str | None
    notes: str | None


def _year_runs(years):
    """`2011-2012, 2015` for the years."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return ', '.join(str(first) if first == last else f'{first}-{last}' for first, last in runs)


def _unique_best(scores):
    """The key with the highest score, if no other key has it and it is above zero; else None."""
    if not scores:
        return None
    best = max(scores.values())
    winners = [key for key, score in scores.items() if score == best]
    return winners[0] if best > 0 and len(winners) == 1 else None


def _unique_first(positions):
    """The key with the lowest position, if no other key has it; else None."""
    if not positions:
        return None
    first = min(positions.values())
    firsts = [key for key, position in positions.items() if position == first]
    return firsts[0] if len(firsts) == 1 else None


class Attribution:
    """The attribution rules over the affiliations and citations of the registers.

    `sources` is {id: Source}, `excerpt(source_id)` the text of a source's excerpt, `commit_domains(year)` the
    {username: Counter({domain: commits})} of a year ({} for a year without a file). The registers come in as
    functions: `match_domain(domain) -> (organisation id, how) | None`, `name_of(person_id)`,
    `logins_of(person_id)` (all GitHub logins of the person), `username_of(person_id)` (the username the
    collected files count the person under, or None) and `names_of_organisation(organisation_id)` (its name
    and aliases).
    """

    def __init__(self, affiliations, citations, sources, excerpt, commit_domains, *, match_domain, name_of,
                 logins_of, username_of, names_of_organisation):
        self._rows = defaultdict(list)
        for affiliation in affiliations:
            if affiliation.status != PROPOSED:
                self._rows[affiliation.person].append(affiliation)
        self._citations = defaultdict(list)
        for citation in citations:
            self._citations[citation.affiliation].append(citation)
        self._sources = sources
        self._excerpt = excerpt
        self._commit_domains = commit_domains
        self._match_domain = match_domain
        self._name_of = name_of
        self._logins_of = logins_of
        self._username_of = username_of
        self._names_of_organisation = names_of_organisation
        self._domains_by_year = {}
        self._excerpts = {}

    def organisation(self, person_id, year):
        """The id of the organisation the person counts for in the year, or None for Unmapped."""
        return self._decide(person_id, year)[0]

    def conflict(self, person_id, year):
        """The ids of the organisations between which no rule decides in the year; empty when one counts or none."""
        return self._decide(person_id, year)[1]

    def conflicts(self, until=None):
        """[(person id, year, [organisation ids])] of the years that no rule decides.

        Open-ended affiliations are followed up to `until`; the years up to the last end of a row are always
        included. `until` defaults to the current year, so callers that must give the same answer every day
        (the check) pass it explicitly.
        """
        found = []
        for person_id in sorted(self._rows):
            for year in self._years(person_id, until):
                organisation, conflict = self._decide(person_id, year)
                if organisation is None and conflict:
                    found.append((person_id, year, conflict))
        return found

    def decision_errors(self, until=None):
        """Two decisions for one person and year where the later one does not name the earlier in `supersedes`.

        The decisions are those that rule 2 weighs, compared in the order of their dates; each must name the one
        before it. `until` as for `conflicts`.
        """
        missing = defaultdict(set)  # (person, earlier, later) -> years
        for person_id in sorted(self._rows):
            for year in self._years(person_id, until):
                decisions, supersedes = self._decisions(self._counting(person_id, year))
                ordered = self._in_order(decisions, supersedes)
                for earlier, later in zip(ordered, ordered[1:]):
                    if earlier not in supersedes[later]:
                        missing[(person_id, earlier, later)].add(year)
        sources = self._sources
        return [f'{person}: the decision {later} ({sources[later].date}) does not name the earlier decision '
                f'{earlier} ({sources[earlier].date}) in `supersedes`, for {_year_runs(years)}'
                for (person, earlier, later), years in sorted(missing.items())]

    def _years(self, person_id, until):
        rows = [row for row in self._rows[person_id] if row.status in COUNTING]
        if not rows:
            return range(0)
        last = max([until or date.today().year] + [row.to_year for row in rows if row.to_year is not None])
        return range(min(row.from_year for row in rows), last + 1)

    def _counting(self, person_id, year):
        """The stated and assumed rows of the person that cover the year, without the denied organisations."""
        rows = [row for row in self._rows[person_id] if row.covers(year)]
        denied = {row.organisation for row in rows if row.status == DENIED and row.organisation}
        return [row for row in rows if row.status in COUNTING and row.organisation not in denied]

    def _candidates(self, person_id, year):
        """The counting rows, and of them only the stated ones when there are any."""
        rows = self._counting(person_id, year)
        return [row for row in rows if row.status == STATED] or rows

    def _decide(self, person_id, year):
        """(organisation id or None, the organisations in conflict when no rule decides)."""
        rows = self._counting(person_id, year)
        if not rows:
            return None, []
        decided = self._by_decision(rows)
        if decided is not None:
            return decided
        rows = self._candidates(person_id, year)
        organisations = sorted({row.organisation for row in rows})
        if len(organisations) == 1:
            return organisations[0], []
        for rule in (self._change_year, self._named_first, self._commits_and_statements, self._records):
            organisation = rule(person_id, year, rows, organisations)
            if organisation is not None:
                return organisation, []
        return None, organisations

    def _source(self, source_id):
        return self._sources.get(source_id)

    def _kind(self, source_id):
        source = self._source(source_id)
        return source.kind if source else None

    def _captured_in(self, source_id, year):
        """Whether the source was captured and speaks for the year."""
        source = self._source(source_id)
        return (source is not None and source.date.year == year
                and not (source.notes or '').startswith(UNCAPTURED))

    def _decisions(self, rows):
        """({decision source: date}, {decision source: the sources its citations supersede}) of the rows."""
        decisions, supersedes = {}, defaultdict(set)
        for row in rows:
            for citation in self._citations[row.id]:
                if self._kind(citation.source) == DECISION:
                    decisions[citation.source] = self._sources[citation.source].date
                    supersedes[citation.source].update(
                        name.strip() for name in (citation.supersedes or '').split(';') if name.strip())
        return decisions, supersedes

    @staticmethod
    def _in_order(decisions, supersedes):
        """The decisions from the earliest to the latest; of the same date, a superseding one after the other."""
        def key(source):
            same_day = [other for other in decisions if decisions[other] == decisions[source]]
            return decisions[source], sum(other in supersedes[source] for other in same_day), source
        return sorted(decisions, key=key)

    def _by_decision(self, rows):
        """Rule 2: (organisation, []) of the latest decision, (None, organisations) for a tie, else None."""
        decisions, supersedes = self._decisions(rows)
        if not decisions:
            return None
        newest = max(decisions.values())
        latest = {source for source, when in decisions.items() if when == newest}
        latest -= {earlier for source in latest for earlier in supersedes[source]}
        organisations = sorted({row.organisation for row in rows for citation in self._citations[row.id]
                                if citation.source in latest})
        if not latest:  # decisions of one day that supersede each other: a conflict
            organisations = sorted({row.organisation for row in rows for citation in self._citations[row.id]
                                    if decisions.get(citation.source) == newest})
        return (organisations[0], []) if len(organisations) == 1 else (None, organisations)

    def _change_year(self, person_id, year, rows, organisations):
        """Rule 4: the organisation the person leaves during the year."""
        if len(organisations) != 2:
            return None
        before = {row.organisation for row in self._candidates(person_id, year - 1)}
        after = {row.organisation for row in self._candidates(person_id, year + 1)}
        leaving = [org for org in organisations if org in before and org not in after]
        joining = [org for org in organisations if org in after and org not in before]
        return leaving[0] if len(leaving) == 1 and len(joining) == 1 else None

    def _excerpt_of(self, source_id):
        if source_id not in self._excerpts:
            self._excerpts[source_id] = self._excerpt(source_id) or ''
        return self._excerpts[source_id]

    def _named_first(self, person_id, year, rows, organisations):
        """Rule 6a: the organisation named first in a source that the rows of all of them cite."""
        # Imported here: scripts.lib.capture imports the model, which imports this module
        from scripts.lib.capture.passages import find_quote

        spans = defaultdict(lambda: defaultdict(list))  # source -> organisation -> spans of its snippets
        for row in rows:
            for citation in self._citations[row.id]:
                if citation.snippet:
                    span = find_quote(self._excerpt_of(citation.source), citation.snippet)
                    if span is not None:
                        spans[citation.source][row.organisation].append(span)
        winners = set()
        for source, by_organisation in spans.items():
            if set(by_organisation) != set(organisations):
                continue
            starts = {org: min(start for start, _ in found) for org, found in by_organisation.items()}
            first = _unique_first(starts) or self._named_first_within(source, by_organisation, starts)
            if first is not None:
                winners.add(first)
        return winners.pop() if len(winners) == 1 else None

    def _named_first_within(self, source, by_organisation, starts):
        """The organisation whose name comes first in the text of the snippets that start first together."""
        from scripts.lib.capture.passages import find_name

        start = min(starts.values())
        tied = [org for org, position in starts.items() if position == start]
        end = max(span_end for org in tied for span_start, span_end in by_organisation[org] if span_start == start)
        text = self._excerpt_of(source)[start:end]
        names = {}
        for org in tied:
            found = [span[0] for name in self._names_of_organisation(org) if name
                     if (span := find_name(text, name)) is not None]
            if found:
                names[org] = min(found)
        return _unique_first(names) if len(names) == len(tied) else None

    def _commits_of(self, person_id, year):
        """(commits per organisation, personal commits) of the person in the year, or None without commits."""
        # Imported here: commit_authors imports the model, which imports this module
        from scripts.lib.commit_authors import is_own_domain_for
        from scripts.lib.commit_domains import organisation_commits

        username = self._username_of(person_id)
        if not username:
            return None
        if year not in self._domains_by_year:
            self._domains_by_year[year] = self._commit_domains(year)
        counts = self._domains_by_year[year].get(username)
        if not counts:
            return None
        name, logins = self._name_of(person_id), self._logins_of(person_id)
        per_organisation, personal, _ = organisation_commits(
            counts, self._match_domain, lambda domain: is_own_domain_for(domain, name, logins))
        return per_organisation, personal

    def _commits_and_statements(self, person_id, year, rows, organisations):
        """Rules 6b and 6c: the commits of the year, else the person's own statement of the year."""
        commits = self._commits_of(person_id, year)
        if commits is None:
            return None
        per_organisation, personal = commits
        candidates = {org: per_organisation[org] for org in organisations}
        if sum(candidates.values()) > personal:
            return _unique_best(candidates)
        if personal > sum(candidates.values()):
            named = {row.organisation for row in rows for citation in self._citations[row.id]
                     if self._kind(citation.source) in OWN_STATEMENT_KINDS
                     and self._captured_in(citation.source, year)}
            return named.pop() if len(named) == 1 else None
        return None

    def _records(self, person_id, year, rows, organisations):
        """Rule 6d: the organisation that more distinct cited sources dated in the year name."""
        sources = defaultdict(set)
        for row in rows:
            sources[row.organisation].update(citation.source for citation in self._citations[row.id]
                                             if self._captured_in(citation.source, year))
        return _unique_best({org: len(sources[org]) for org in organisations})
