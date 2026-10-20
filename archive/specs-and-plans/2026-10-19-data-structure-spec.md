## Analysis and specification

This comment has two parts: an analysis of why adding data goes wrong, and a specification of a structure that doesn't ask for those errors.
It rests on the code paths and the git history as of 742ed36, after #140; the counts are from that state, and links into the code point at that commit.

### Part 1: Why editing goes wrong

The errors we keep making — names not linked to the right login, organisations wrong in some years although the overrides were right, the same fact in several places — are not slips.
The structure asks the editor to compute joins by hand and gives no feedback when they get one wrong.
Six properties cause this.

#### 1. There is no person

Identity is keyed four ways: by login in the mapping files, by free-text name in the community data, by email in `commit_authors.csv`, by changelog name in `changelog_names.csv`.
The join between them happens at build time, in three matchers with different rules:

- [`people.build_person_index`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/lib/people.py#L77) drops a name with two candidate logins, doesn't apply account aliases, and has no login fallback.
- [`changelogs.NameMapper`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/lib/changelogs.py#L436) takes the first commit-author hit and the last fullname hit, applies aliases, and matches names against logins.
- [`site.js`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/report/site/static/site.js#L50) repeats the normalisation in JavaScript, with a different definition of a combining character.

An editor writes a name and learns whether it matched only when the page is built, if at all.
A login column exists in two of ten kinds (`Github`, `GitHub Handle(s)`).
Víctor Fernández de Alba is spelled four ways across the files, Eric Bréhault three, and nine more people two.
Five of seventy logins in the fullname mapping need several rows for their spellings; people without a login, such as Ionut Dobricean, have nowhere to record a variant at all.
`commit_authors.csv` is read by four different pieces of code.

#### 2. The organisation of a person in a year is stored twice, and the default is wrong by design

The mapping computes it: [`load_organisation_mapping`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/lib/mappings.py#L89) takes the `Team` column for every year and lets an override replace it.
The community data stores it again: 388 of 1,531 rows (25 %) say in `Source` that their organisation was copied from the mapping.
Nothing compares the copy with the mapping for that year, and a copied organisation looks exactly like one the source states.
"Wrong in some years although the overrides were right" is this: the copy was made before the override existed.
Correcting the years 2020–2023 of two people took 14 curated rows, 2 overrides and 4 commits (`7e379fe`, `aa880f0`, `7ed781a`, `40fe9ae`); after #136, 13 stale copies had to be found by hand, and the World Plone Day talks could only be checked by reviewing all 250 rows against their videos in #140.

The default makes it worse.
Because the current entry reaches back to 2002, the overrides hold 60 rows with the organisation `Unmapped` whose only purpose is to block it; 38 of them start in 2002 or 2003.
86 of the 132 logins with overrides have no current entry at all, so their "override" overrides nothing: it is the only record.
`lrowe` has a current entry that applies to no year, because nine overrides cover 2002 to 2025.
One correct override (`thet,Syslab,2019,`) left seventeen earlier years counted for Syslab.
Mapping one person (`d8dc035`) touched seven files.
`organisation_mapping_sources.csv` repeats, row for row, the organisation that `organisations.csv` already states, and no script reads it.

#### 3. Multi-value cells are matched by position

`Organiser(s)`, `Trainer(s)`, `Speaker(s)`, `GitHub Handle(s)` and `Organisation` are semicolon lists that the reader zips by index.
52 of 263 sprint rows with organisers have a different number of organisations than organisers.
The docs give the same column two meanings: in sprints, `Organisation` is the organising organisation; in trainings and talks, it is "in the same order as the trainers".
[`community_records`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/lib/community.py#L93) drops empty parts, so one empty handle makes the counts differ and every handle of the row is lost ([2004 trainings, row 11](https://github.com/plone/plone-contributor-statistics/blob/742ed36/curated/community-contributions/2004-plone-conference-trainings.csv#L11)); when the organisation count differs, every person gets the joined string and the page credits each organisation once per person.
The recognition script [reads the same files a second time](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/report/generate_community_recognition_report.py#L176) with its own splitting, doesn't split person cells at all, doesn't filter empty parts in two kinds, and opens the files without an encoding.

#### 4. An organisation is its spelling

Organisation names are compared in five ways: `lower()` in [`organisation_names`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/lib/mappings.py#L74), a [hardcoded alias table plus `lower()`](https://github.com/plone/plone-contributor-statistics/blob/742ed36/scripts/report/generate_community_recognition_report.py#L76) in the recognition script with targets that aren't in `organisations.csv`, raw strings in the page's history, accent-folding `slug()` for the page's keys, and exact match in the tests.
None of them would have caught `Ecreall` next to `Ecréall`.
`r2 Solutions GmbH` was added with an empty `Team` one day after `R2 Solutions GmbH` had been removed on evidence, and passes every test.
231 of 315 organisations have an empty `Team`; they exist only so that the spelling test accepts them.

#### 5. `Source` is a bag

The cell holds the record for the row, then "organisation of X from the organisation mapping: <record>" or "X: <record>" per person, then episode links in the podcasts.
Three kinds of fact in one free-text cell, which no code can take apart; the distinction that matters most — stated by the source, or copied from the mapping — exists only as prose, and the per-person records are again matched to the people by order.

#### 6. The rules are in the docs, the checks are about shape

The documentation states about 25 rules an editor must hold at once (sorted ignoring case, login once with GitHub's case, semicolons never `&`, current entry here and past entry there, `Unmapped` rows to block the default, spell organisations exactly, same order as the trainers, …).
About half are tested, and none of the tests is about meaning: no test checks that a person exists, that a handle is a login, that a community row's organisation agrees with the mapping for its year, or that two names are the same person.
Ten header layouts exist across the 167 community files; `Notes` exists only in some kinds and years.
`organisation_mapping_sources.csv`, `organisation_mapping_proposals.csv` and `community-recognition-points.csv` are read by no script.

### Part 2: Specification

#### Principles

1. **Every fact once.** A person, an organisation and an affiliation each have one row; everything else refers to it by key.
2. **Every reference is a key a check can verify.** No free-text name is matched at build time.
3. **The schema is the format.** A [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) in `curated/datapackage.json` defines every curated file; the checks run from it and the reference documentation is generated from it.
4. **A set cell only where nothing runs parallel to it.** A cell may hold several keys only when the elements have no attributes of their own and no other column is matched to it by position.
5. **One model library.** One package reads the curated files and resolves people and organisations; every stage, tool and test imports it.
6. **A public record for every row stays**, as `AGENTS.md` states it, with the exception for early commit authors.

#### The registers

The files replace the mapping files in `curated/mappings/`.
Column names are `snake_case` throughout.
Whether the folder keeps its name is left to the builder.

##### `people.csv`

One row per person.

| Column | Meaning |
|---|---|
| `id` | Opaque identifier: lower-case letters, digits and hyphens. Chosen when the row is created, by convention from the name (`philip-bauer`, with a number on collision), and from then on never renamed, never derived from anything, never matched against anything. |
| `name` | The display name: the name the person uses in public, usually the GitHub profile name. |
| `github` | The GitHub login the person's code work is counted under, spelled as on GitHub; empty for a person without an account. Unique, ignoring case. |
| `source` | The public record for the person: the GitHub profile, or the page that names them in the role the data records. |

Rules: `id` unique and primary key; sorted by `id`.
A person who later gets a GitHub account gets a `github` value; the `id` stays.

##### `identities.csv`

One row per string that denotes a person in a source.
Replaces `mapping-github-username-to-fullname.csv`, `commit_authors.csv`, `account_aliases.csv` and `changelog_names.csv`.

| Column | Meaning |
|---|---|
| `person` | Foreign key to `people.id`. |
| `kind` | `name`: a spelling in changelogs, conference pages or older data. `email`: a commit address that GitHub links to no account, in lower case. `login`: a second GitHub account. |
| `value` | The string. |
| `source` | As the current files require it per kind: the record that links the string to the person; for a Subversion address, what the identification rests on. |

Rules: (`kind`, `value`) unique, ignoring case; sorted by `person`, `kind`, `value`.
A name may belong to one person only; the policy for short names stays as documented for `changelog_names.csv`.
The precedence rules of `NameMapper` become unnecessary: any identity resolves to its person.
Two rules of the changelog collector are not identities and stay in the collector, on top of the model: a changelog name that equals a login with commits, and the part before the `@` of a Subversion address.

##### `affiliations.csv`

One row per person, organisation and period.
Replaces the `Team` column of `organisations.csv`, `organisation_mapping_sources.csv` and `organisation_mapping_overrides.csv`.

| Column | Meaning |
|---|---|
| `person` | Foreign key to `people.id`. |
| `organisation` | Foreign key to `organisations.id`. |
| `from` | First year, as `YYYY`. |
| `to` | Last year, as `YYYY`; empty means up to the present. |
| `source` | The public record, as `docs/explanation/attribution.md` defines acceptable records. |
| `checked` | The date the record was read, `YYYY-MM-DD`; required when `to` is empty. |
| `notes` | Free text, for example which years of the range the record covers. |

Rules: `from` ≤ `to`; the rows of one person don't overlap; sorted by `person`, `from`.
**There is no default.** A year that no row covers is Unmapped.
`Unmapped` is therefore never written; the 60 blocking rows disappear, and so does the difference between "current" and "past": today's organisation is a row with an empty `to`.
A bio that names an employer for a conference year is an affiliation row for that year, with the bio as its record; it is thereby also evidence for the commits of that year, as the attribution rules already say about signatures and participant lists.

##### `organisations.csv`

One row per organisation.

| Column | Meaning |
|---|---|
| `id` | Opaque identifier, primary key, with the same rule as `people.id`: a slug chosen at creation (`kitconcept`, `upcnet`), never renamed, never derived from the name afterwards. |
| `name` | The canonical spelling, shown in the derived files, the reports and on the page. It may change; the references don't. |
| `kind` | `organisation`; `independent` for a person's own entry such as `Jane Doe (independent)`; `foundation` for `Plone Foundation`, which the conference and talk files name as an organising entity and which is not counted as an organisation. The code stops parsing the `(independent)` suffix; `Plone Foundation (community volunteer)`, which no curated file uses any more, is retired. |
| `aliases` | Other spellings and former names, separated by semicolons. |
| `notes` | Free text. |

Rules: `id` unique; `name` unique; sorted by `id`.
A new `name` must not fold — case, accents, whitespace, punctuation — to an existing name or alias; that is the check that would have refused `Ecreall` and `r2 Solutions GmbH`.
A rename of an organisation is one cell; the twenty-file commits of `21febd2` and `e41525a` don't happen again.
The alias table in the recognition script moves here and is deleted from the code.
`Unmapped` is not a row; it is a reserved word of the derived data.

##### `affiliation_proposals.csv`

Replaces `organisation_mapping_proposals.csv`: the columns of `affiliations.csv`, with `evidence` instead of `source` and `checked`.
It holds what a source states but no accepted record confirms yet; no script reads it, the schema checks it, and the migration fills it (see below).

##### Unchanged

`bot_accounts.csv` and `excluded_repositories.csv` stay as they are and get a schema.

#### The curated community data

One file per year and kind stays.
Every file has `source` (required, containing a link) and `notes` (optional), and the columns of its kind.
A person is referred to by `people.id`, either in `person` (one per row) or in a set column named after the role.
An organisation column holds `organisations.id` values and names an organising entity that the source names; it never holds a person's employer, which the statistics take from the affiliations.
The rule "spell organisation names exactly as in `organisations.csv`" disappears: the key is checked, the spelling lives in one cell.
Groups in person columns are not allowed: a company team is an organising entity in an organisation column, as #140 already decided for the talks; a community or a role goes into `notes`.

| Kind | Columns | Shape |
|---|---|---|
| `board-of-directors` | `person`, `role` (`voting`, `non-voting`), `source`, `notes` | one row per member |
| `team-leaders` | `person`, `team`, `source`, `notes` | one row per leader and team |
| `release-managers` | `person`, `source`, `notes` | one row per release manager |
| `podcasts` | `series`, `person`, `episodes`, `source`, `notes` | one row per host, as today |
| `plone-conference-trainings` | `title`, `trainers`, `source`, `notes` | one row per training; `trainers` is a set |
| `world-plone-day-talks` | `title`, `speakers`, `organisations`, `type`, `location`, `source`, `notes` | one row per video; `speakers` a set; `organisations` only when the source names a company team instead of people; `source` is the video link |
| `sprints` | `sprint`, `start`, `end`, `location`, `organisers`, `organisations`, `level`, `source`, `notes` | one row per sprint; both sets |
| `plone-conference` | `organisation`, `organisers`, `source`, `notes` | one row per organising organisation, as today; `organisers` a set |
| `world-plone-day-event` | `date`, `location`, `format`, `organisations`, `organisers`, `source`, `notes` | one row per local event; both sets |

Where a set is allowed, its elements are keys with no attributes of their own: the organisation of a trainer or speaker comes from the affiliations, the credit for a sprint goes to its organising entities.
Where an element needs an attribute — the episodes of a host, the team of a leader, the role of a Board member — the kind has one row per person, which these kinds already have.
`Source` cells that today hold several facts are split: the record for the row stays in `source`, the records for people's organisations move to `affiliations.csv` or `affiliation_proposals.csv`, episode links stay in `source` separated by spaces as now.

#### How the statistics are derived

- The organisation of a person in year Y is the affiliation row that covers Y, else Unmapped.
- Code work: the collected login resolves to a person through `people.github` or an identity of kind `login`; the organisation follows from the affiliations. A login without a person is Unmapped, as today.
- A role (Board, team lead, release manager, trainer, speaker, host, sprint organiser, conference organiser) counts for the person's organisation in the year of the file. An event counts for its organising entities, split as the points file says. Today an organiser's role is credited to the organising entities; this changes it to the person's organisation, so that one rule covers all roles.
- A person is active in a year if they appear in any person column of that year or in the collected data, joined through the register, so one person counts once.
- People are shown by `people.name` and organisations by `organisations.name`; the derived files and reports keep naming organisations as today, rendered from the register, and the `Name (independent)` entries keep their names.
- In the collected and derived files, `username` stays the GitHub login; a person without a login is written as `person:<id>`. This replaces today's rule that a username with a space is a name. Four commit authors are affected.

#### The schema and the checks

`curated/datapackage.json` declares one resource per register and one per kind of community data, the latter with the list of its yearly files as `path`.
The Table Schema states the types (`integer` for years and episodes, `date` for dates), `required`, `enum` for `kind`, `role`, `level`, `format` and `type`, a `pattern` that requires a `https?://` link somewhere in every `source` (except identities of kind `email`, where the early-commit-author exception applies), `unique`, the primary keys and the foreign keys of every scalar `person` and organisation column.

`frictionless validate curated/datapackage.json` runs in `make check` and `make test`.
Its report names file, row, column and the rule, which is the feedback an editor or an agent needs at the moment of the edit.

A small set of custom checks, written in Python and registered with Frictionless, covers what Table Schema can't express:

- the elements of a set column are foreign keys and unique within the cell;
- the affiliations of one person don't overlap;
- no organisation name folds to another name or alias;
- the files are sorted as their rules say;
- `people.github` values are unique ignoring case.

The pytest format tests that the schema now covers are deleted.
What stays in pytest is policy that is not format: the completeness rules for the recognition year, the layout test, the reproducible outputs.

#### The model library

`scripts/lib/model/` is the only code that opens a file under `curated/`; a test enforces that.
It loads through the schema (Frictionless `Resource.read_rows()`, so values arrive typed), returns records as dataclasses, and owns the two resolutions:

- `person_for(login=…)`, `person_for(email=…)`, `person_for(name=…)`: a person or `None`, from `people.csv` and `identities.csv`;
- `organisation_of(person, year)`: the organisation or Unmapped, from `affiliations.csv`;

plus `roles(year)` and `events(year)` for the community data.
The collectors, the derive and report scripts, the tools and the tests import it.
With it go the second reader in the recognition script, the three name matchers, the four readers of `commit_authors.csv`, the alias table, and the duplicated constants (`UNMAPPED`, `TALK_TYPES`, `IN_PERSON`, five copies of the login regex).

#### Tools an editor needs

- `python -m scripts.tools.person <query>`: finds people by id, name, login or email and prints their rows; `--add "<name>" [--github <login>] --source <url>` creates a row with a generated id and prints it.
- `python -m scripts.tools.affiliation <person> <year>`: says which organisation the data gives and which row says so.
- `python -m scripts.tools.check`: the validation, with hints such as the nearest existing ids for an unknown key.
- `unmatched_names` and `unmatched_changelog_names` propose `people.csv` and `identities.csv` rows instead of fullname rows.

#### Migration

The migration is a script, so that reviewers can re-run it and compare, and it lands in one pull request, because the old code can't read the new files and the documentation must change with them.
It takes no decisions that need a person; everything that does is deferred to files that are reviewed afterwards, and nothing that the current files hold is lost.

1. **Registers from the current files.** People: every login in the mapping files, every distinct person in the community data, every commit author and fullname row; ids generated from the names, merged where today's person index links them, kept apart where it doesn't. Display names of logins that no curated file names (about 150) come from a one-off fetch of the GitHub profile names, committed as an input file of the script, so that the script itself stays offline; a profile without a name gets the login. Identities from the four files. Organisations with ids generated from their names, their kinds, and the alias table of the recognition script as aliases. Affiliations materialised from `load_organisation_mapping(year)` for every year from 2002 to the current one, compressed into ranges, with the `sources` row as the record of the current entry and the override's source for the past; ranges that exist only because the current entry reached back get a `notes` value that says so.
2. **Community data rewritten.** Names become ids; rows with several people of a per-person kind are split; positional cells become sets; `Source` cells are split as described. Organisation cells disappear from person rows. Where a cell was copied from the mapping, or agrees with the mapping of its year, nothing is lost. Where it states something the mapping doesn't — an organisation for a year the mapping leaves Unmapped (about 65 rows), one that differs from the mapping (about a dozen), or any organisation of a person without a login (about 160) — the statement goes to `affiliation_proposals.csv`, with the row's record and a reference to the row as `evidence`. Those rows count for the mapping's organisation, or Unmapped, until a review moves the proposal into `affiliations.csv`.
3. **Code switched** to the model library, the schema and the checks added, the old loaders and tests removed.
4. **Documentation updated**: the reference pages for the files generated from the schema, the explanation of attribution and of the curated data revised, the how-tos rewritten around adding a person, an affiliation and a row.

`tests/test_reproducible_outputs.py` is the gate.
Code attribution must not change at all in this pull request, since the affiliations are today's mapping made explicit.
Community credit changes only for the rows that step 2 defers and for organiser roles, and the pull request lists every such row; every other difference in `derived/` and `reports/` must be explained by one of the defects named in Part 1 (dropped handles, organisations credited once per person).
Anything else is a bug in the migration.

Afterwards, in separate pull requests, the judgement that the migration deferred:

- **The proposals** are reviewed row by row into `affiliations.csv`, as `organisation_mapping_proposals.csv` is reviewed today.
- **The reaching-back ranges** are trimmed to the years their record supports. The script proposes a first year per row — the year of the record, or the person's first collected activity — and a maintainer confirms or corrects it; this changes the numbers, mostly towards Unmapped in the early years, and is reviewed as a policy change.
- Two ids that turn out to be one person are merged in one commit that rewrites the references.

#### Out of scope

- Moving the data out of CSV files in git, or making id.plone.org or plone.org the source of truth (#28).
- Changing the counting rules, the attribution rules or the recognition points.
- Affiliations by date instead of by year.
- Reading `community-recognition-points.csv` in the recognition script instead of hardcoding it; worth its own issue.
- Scraping curated data.

#### Open points

1. The World Plone Day talks: keep `youtube_id` next to `source`, or derive it from the video link? The specification drops it.
2. Whether `curated/mappings/` is renamed, for example to `curated/registers/`, is a one-line change in `paths.py` and left to the builder.

Refs #16, #38, #53, #70, #86, #117, #136, #140.

Assisted-by: Claude Fable 5.1
