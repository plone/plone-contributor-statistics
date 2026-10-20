# Spec: affiliation evidence from the GitHub commit search

Date: 2026-10-20. Follow-up to #152 (address tool) and #153. Refs #139.

## Why

The migration to the registers kept today's organisation for every year of a person's activity, as rows marked
"not verified". Trimming them now would turn 48% of all commits and pull requests Unmapped (94% in 2024 and 2025),
because the current entries, mostly GitHub profiles read in 2026, date nothing. Before any trim, the guessed years
need dated evidence. A sample of 120 guessed active person-years showed that two queries of the GitHub commit
search support about 60% of them, more once every organisation has its GitHub handle:

1. the person's commits of a year, in all public repositories, carry a company address (53% of the sample);
2. the person committed in the organisation's own GitHub organisation that year (5%, tested only where a handle
   was known).

## Rules

The attribution rules already accept a company address in commits made in Git as evidence for the years of the
commits. They gain: commits in the repositories of an organisation's GitHub organisation in a year are evidence
for an affiliation with it in that year, of the same kind. Personal addresses and project organisations (plone,
collective, zopefoundation) say nothing. The change-year rule and the tie-breaker for two records apply unchanged.

## Register

`organisations.csv` has a new column `github`: the login of the organisation's GitHub organisation, with its case,
empty when it has none; unique ignoring case. Only organisations get one, never project organisations.

## Tool: `python -m scripts.tools.github_evidence`

Input: the people with a login and an affiliation whose notes say "not verified" (default), or `--person ID`
(repeatable); the years to query are those rows' years before 2026 in which the person has commits or pull
requests in `collected/contributors/<year>-plone-contributors.csv` (`--all-years` queries every year of the rows).

For each person-year:

- Query 1: `search/commits` with `author:<login> committer-date:<year>-01-01..<year>-12-31`, first page of 100,
  sorted by `committer-date` ascending so the example is the earliest. Each commit gives the author address; the
  domain is classified with the address tool's rules (`is_company_domain`, `is_own_domain`, the registry's
  `match_domain`). The organisations matched, with their commit counts, the earliest commit per organisation
  (its `html_url` and date), and the unmapped company domains are recorded.
- Query 2, when query 1 matched no organisation: for each organisation with a `github` handle among the person's
  affiliations of that year or the neighbouring years (the guess and the recorded ones), `search/commits` with
  `author:<login> org:<handle> committer-date:<year>-01-01..<year>-12-31`, `per_page=1`, reading `total_count`.
  A count above zero is evidence for that organisation.

Requests go through `scripts.lib.github_api.github_get` with the session and token the collectors use
(`GITHUB_TOKEN` from the environment, never `--token`), paced to the search limit of 30 requests a minute.
Every response is cached as JSON under `.cache/github-search/<login>/<year>.json` and
`.cache/github-search/<login>/<year>-org-<handle>.json`; `--refresh` ignores the cache. A run interrupted by an
error resumes from the cache.

Output, like the address tool: proposals for `affiliation_proposals.csv`, one per person, organisation and run
of consecutive years with evidence, leaving out years an affiliation of the same organisation covers already,
unless that affiliation is a "not verified" row (those are what the evidence is for). Evidence texts:

- `Company address @<domain> in commits <years> found by the GitHub commit search (example: <html_url>)`
- `Commits in the GitHub organisation @<handle> in <years> (<n> in <first year>; search:
  https://github.com/search?q=author%3A<login>+org%3A<handle>+committer-date%3A<year>-01-01..<year>-12-31&type=commits)`

The report (Markdown on stdout) has the tables Proposals (with how each was found, the counts and the example),
Conflicts (proposed years another organisation covers, saying whether that row is a guess), Unmapped domains
(company domains that match no organisation, with commits, years and people, for adding aliases), and
Organisations without a handle (the guessed organisations of the person-years that query 1 left open, with the
number of person-years each, for filling the `github` column). `--write` appends the proposals through the model.

## Review

The proposals are reviewed like the address ones: a proposal that only confirms a guessed row turns that row's
years into verified ones (the row's source gains the evidence and its note goes); a proposal that contradicts a
guess splits the guess around the evidence; a proposal against a dated record goes to the reviewer. A later
pull request does the review; the tool writes proposals only.

## Tests

Offline, with a fake session answering canned search responses; cover: query 1 with company, personal, own and
unmapped domains; query 2 after an empty query 1; the cache (second run makes no request; `--refresh` does);
pacing (the sleep is injected); the years chosen from the contributors files; the report sections; `--write`
appending once; the rate-limit path of `github_get` is already tested.

## Documentation

`docs/how-to/add-an-affiliation.md` gets a section "Find affiliations in the GitHub commit search" next to the
address one; `docs/explanation/attribution.md` the new evidence kind; `docs/reference/curated-files.md` is
regenerated for the column; `AGENTS.md` and `scripts/README.md` list the tool.

## Plan, as carried out

1. Measure first: a strict trim of the "not verified" rows against the collected activity (48% of all commits
   and pull requests would become Unmapped), then a sample of 120 guessed person-years against the two searches.
2. Archive the migration script, its data and tests, which would otherwise need the new column.
3. Add the `github` column: schema, model, checks (unique ignoring case), test fixtures, reference page.
4. Fill it: candidates from the `@handle` mentions in the affiliation sources, each checked against the API
   (an organisation, with a matching name or repositories); wrong mentions replaced by hand after a second lookup.
   Merge the migration's Atlasense row into Onna on the way.
5. Build the tool, its offline tests and its documentation (an implementation agent, from this spec), add the
   project and personal domains the sample surfaced, review, run the suite and the docs build.
6. Run the tool for real with the token from the environment, report, and leave the review of the proposals to
   the next pull request.
