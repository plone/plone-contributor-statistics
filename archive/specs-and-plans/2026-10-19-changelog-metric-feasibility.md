# Changelog entries as a contribution metric: feasibility study (#71)

Status: research and prototype only. Nothing in the repository was changed.
Data state: the clones in `.cache/repositories/plone/` and `collected/contributors/` as of 2026-10-19.

## Short answer

It works, and it is worth doing for **2004 to 2012**.

- From 2004 on, 89 to 99 percent of the changelog entries end with a name, almost always as `[name]`.
- Once deduplicated, there are about 1,000 to 1,700 entries per year from 2004 to 2012 (10,874 for 2003 to 2012 together).
- The names map well. Today's curated files and the logins already known map 49 to 88 percent of the entries per year. With 27 more mappings, each backed by a commit that repeats the entry, the share rises to 80 to 94 percent.
- Per person, the metric correlates strongly with commits (Pearson 0.93 across 2003 to 2012). So it is mostly a check on the commit counts and a second view of them. It adds little new: 13 people have changelog entries but no counted commits in 2003 to 2012.
- From 2016 on, towncrier and `@login` take over, and the entries track the merged PRs closely (Pearson 0.85 to 0.88). Before 2013, they don't track the PRs at all (0.10 for 2011 to 2012).

## How the study was done

The scripts are in this folder. All of them are read only against the main checkout.

| Script | What it does |
|---|---|
| `fetch.py` | For every repository in the cache, except those in `excluded_repositories.csv`, it takes the default branch and the release branches. It uses the collector's `VERSION_BRANCH` rule. It makes its own shallow, blobless clone under `clones/` and fetches only the changelog blobs of the branch tips into `raw/`, listed in `files.csv`. |
| `extract.py` | Parses the files, extracts names and dates, deduplicates, and maps the names. It writes `occurrences.csv`, `entries.csv`, `per-year.csv` and `names.csv`. With `--proposals`, it also uses `changelog-name-proposals.csv` and writes the `*-with-proposals.csv` files. |
| `evidence.py` | Matches the entries up to 2012 to the commits in the cache whose message repeats the entry. It uses `git log` on the treeless clones and fetches nothing. It writes `evidence.csv`, the author per name, and `lag.csv`, the commit date against the release date. |
| `profiles.py` | Gets the GitHub profile names of the 865 logins in `collected/contributors`. It writes `profiles.csv`. |

The result files `evidence-logins.csv`, `compare.txt`, `lag.txt` and `coverage.txt` hold the raw numbers quoted below.

## 1. Where the changelogs are

There are 441 repositories (438 fetched, 3 empty). 356 of them have changelog files or news fragments, with 1,886 files on 1,210 branch tips.

- **File names** (count of branch-tip files): `CHANGES.rst` 728, `HISTORY.txt` 189 (129 of them as `docs/HISTORY.txt`), `CHANGELOG.md` 135, `CHANGES.txt` 129, `CHANGES.md` 65, `CHANGELOG.rst` 45, `ChangeLog` 39, `history.txt`/`history.rst` 34. A few more are `HISTORY.rst`, `docs/CHANGES.*` and `CHANGES`.
- **Old entries live in subfolders and on release branches.** `Products.CMFPlone` keeps its history in `HISTORY.txt` on 2.0 to 3.0, in `Products/CMFPlone/HISTORY.txt` on 3.1 to 4.0, in `docs/HISTORY.txt` plus `docs/CHANGES.txt` on 4.0 to 4.4.x, in `CHANGES.rst` on 4.3.x and later, and in `docs/HISTORY.rst` plus `CHANGES.md` on master. Of the deduplicated entries from 2003 to 2012, 15.5 percent exist **only** on release branches (40 percent in 2004). The main cases are `Products.Archetypes` (687), `Products.CMFPlone` (234), `Products.CMFEditions` (214) and `plone.app.upgrade` (175). Reading the default branch alone is not enough. The collector's rule, default branch plus release branches, is.
- **Not changelogs:** test fixtures (`tests/`, `_resources/fake-project`), cookiecutter templates, vendored libraries (`jscalendar/ChangeLog`, `static/components/*`, `debian/changelog`), `RELEASENOTES.txt`/`NEWS.txt`, and the aggregated `buildout.coredev/release/changelog.txt` (5.2 and later). The prototype skips these by path.
- **Copies between repositories:** the `Plone` repository's 3.1 branch holds a copy of CMFPlone's `HISTORY.txt` (2,351 shared entries), and `aurora` started as a copy of `volto` (2,482 shared entries).
- **GNU-style ChangeLogs** (`2005-01-22  Name  <email>` followed by `* file: text`) exist in 7 old Products, with about 600 dated records from 2003 to 2006: PloneLanguageTool, PlacelessTranslationService, Archetypes, CMFQuickInstallerTool, CMFFormController, PortalTransforms and validation. The prototype doesn't parse them yet. They carry a name and an email, which makes them easy to map.
- **towncrier news fragments:** 401 files in 105 repositories (353 on default branches). They are the not-yet-released entries only, because towncrier deletes them on release and writes them into `CHANGES.*`.

## 2. The name convention

- **Start:** the first `[name]` is in CMFPlone 1.0.2 (2003-06-03): `[limi]`, `[gdavis]`. By 1.0.4 (August 2003) it is the norm. CMFPlone's `HISTORY.txt` then says "(name of developer listed in brackets)". Before that, 2001 to 2002 has no names (2 percent). 2003 is thin in the data, see 3.
- **Variants** (share of deduplicated entries):

  | Period | `[name]` at the end | `[name]` on its own line, before URLs | `@login` (towncrier) | `(name)`, `-- name`, email | no name |
  |---|---|---|---|---|---|
  | 2001–2005 | 83% | 0.4% | 0 | under 0.5% | 16% |
  | 2006–2009 | 96% | 0.1% | 0 | about 0 | 4% |
  | 2010–2012 | 93% | 0.1% | 0 | 0.1% | 7% |
  | 2013–2015 | 94% | 0.1% | 0 | 0 | 6% |
  | 2016–2019 | 78% | 0 | 15% | 0.2% | 7% |
  | 2020–2026 | 41% | 0 | 48% | 0.1% | 12% |

  Within brackets there are `[a, b]`, `[a and b]`, `[a] [b]`, rarely `[a/b]` or `[a & b]`, and sometimes `[applied by kleist]`. Full names in brackets are rare (`[Eric Brehault]`). `(name)` and `-- name` are mostly false positives, such as "(hopefully)" and "(tm)". The prototype accepts them only when every name maps to a known person, which leaves 34 entries.
- **Not persons:** `[plone devs]` (plone/meta, 154 entries), `[zopeskel]` (template boilerplate) and `[plone]`. They are filtered out. So are placeholders such as "Nothing changed yet." and "*add item here*".
- **Coverage per year** (deduplicated entries):

  | Year | Entries | Repos | Named | Mapped today | Mapped with proposals | `@login` |
  |---|---|---|---|---|---|---|
  | 2002 | 110 | 2 | 2% | 0% | 0% | 0% |
  | 2003 | 69 | 2 | 10% | 7% | 9% | 0% |
  | 2004 | 791 | 10 | 89% | 63% | 80% | 0% |
  | 2005 | 1004 | 18 | 98% | 49% | 86% | 0% |
  | 2006 | 905 | 26 | 96% | 68% | 91% | 0% |
  | 2007 | 1082 | 55 | 95% | 76% | 90% | 0% |
  | 2008 | 939 | 82 | 95% | 77% | 85% | 0% |
  | 2009 | 1699 | 109 | 98% | 88% | 94% | 0% |
  | 2010 | 1738 | 122 | 99% | 76% | 92% | 0% |
  | 2011 | 1452 | 128 | 97% | 62% | 86% | 0% |
  | 2012 | 1195 | 126 | 96% | 77% | 86% | 0% |
  | 2013 | 1168 | 121 | 92% | 82% | 86% | 0% |
  | 2014 | 1029 | 122 | 95% | 82% | 88% | 0% |
  | 2015 | 1964 | 133 | 96% | 89% | 94% | 0% |
  | 2016 | 1443 | 153 | 97% | 93% | 95% | 1% |
  | 2018 | 1763 | 157 | 93% | 91% | 92% | 13% |
  | 2020 | 1659 | 116 | 90% | 82% | 83% | 33% |
  | 2022 | 2048 | 98 | 92% | 82% | 82% | 40% |
  | 2024 | 1423 | 98 | 87% | 79% | 79% | 48% |
  | 2026 | 1741 | 95 | 85% | 77% | 77% | 69% |

## 3. Dating an entry

- An entry is dated by the release header it sits under. The headers come in many forms: `1.2.3 (2010-05-04)`, `1.2.3 - 2010-05-04`, `Plone 2.0.5 - Backed Up Willie - Released December 1, 2004`, `Plone 3.0.6 - released Febuary 15, 2008` (sic), `RC1 - Released September 12, 2006` as a sub-header, `## 6.1.0 (2025-01-01)`, `1.0 - 12.03.2008` and `1.1 (2008-xx-xx)`. The prototype handles ISO dates, `d.m.Y`, English month names (matched by their first three letters, so typos pass), month-only and year-only dates.
- Across all 185,470 occurrences, 93.0 percent take their date from the header and 0.8 percent from the repository tag of the version, as a fallback when the header has no date. 4.5 percent sit under a header without a date: mostly the Plone 1.0 alpha, beta and rc sections of 2002, and a few early 1.0 sections of packages. 1.8 percent are unreleased. After deduplication, 2,220 of 35,507 entries have no year (1,320 unreleased, 900 without a date). **For 2003 to 2012, all 10,874 entries are dated (98 percent by the header, 2 percent by the tag).**
- **Lag:** the release date is later than the work. For the 5,133 entries up to 2012 that could be matched to their commit, the median lag is 15 days, the 75th percentile 41 days and the 90th percentile 118 days. 13.4 percent fall into a later calendar year than their commit (22 percent for the 2009 releases, which include the long Plone 4.0 cycle). Big releases pull a year's work into one date: Plone 2.0 (March 2004) has 181 entries, and its development was in 2003. That is why 2003 shows only 69 entries.
- **Unreleased sections** (`(unreleased)` on branch tips, and the news fragments) get no year and don't count. When the entry was released later on another branch, deduplication takes the released copy.

## 4. Deduplication

- Each entry occurs about 5 times (185,470 occurrences, 35,507 entries). The causes are the copies on every later release branch, backports with the same text, files moved within a repository (`HISTORY.txt` to `docs/HISTORY.txt` to `CHANGES.rst`), and copies between repositories (`Plone` 3.1 and CMFPlone, `aurora` and `volto`).
- **Proposed key:** `text_hash` = SHA-1 of the normalised entry text, names included (Unicode NFKC, lower case, whitespace collapsed, RST/Markdown emphasis removed).
  1. Within a repository, one entry per `text_hash`, over all branches and files.
  2. Across repositories, the same `text_hash` is one entry when the text is at least 60 characters long, or when both copies have the same release date. Short generic texts, such as "Initial release [hannosch]", stay separate in different packages released on different days.
  3. The entry counts for its **earliest dated occurrence**: release date, then default branch before release branch. Undated occurrences lose to dated ones.
- Keeping the names in the key means "Release on PyPI [a]" and "[b]" stay two entries. A backport whose text was edited counts twice. That is accepted, and it is in line with "a backport PR is work of its own".

## 5. Name mapping

- There are 1,679 distinct names. 456 of them first appear in 2012 or earlier.
- The layers, in order (the counts are names first seen up to 2012, with all their entries):

  | Layer | Rule | Names | Entries |
  |---|---|---|---|
  | `svn_name` | the local part of a Subversion address (`@localhost`, the two SVN UUIDs, `users.sourceforge.net`) in `commit_authors.csv` | 35 | 9,875 |
  | `login` | the same login (ignoring case) is in `collected/contributors/*.csv` | 161 | 12,586 |
  | `fullname` | `commit_authors.csv` name or `mapping-github-username-to-fullname.csv` | 4 | 7 |
  | `profile_name` | a full name equal to exactly one GitHub profile name of a known login | 1 | 2 |
  | proposals (new) | a commit that repeats the entry, authored by an address GitHub links to a login | 27 | 2,318 |
  | unmatched | | 228 (255 without proposals) | 1,224 (3,536 without proposals) |

  `account_aliases.csv` is applied to the result. `bobdobbs666` becomes `runyaga`.
- **Commit evidence works.** Of the 79 names that the other layers already map, and that have commit evidence, 73 agree. The 6 that disagree are second accounts: `giacomos`/`giacomos85`, and `runyaga`/`bobdobbs666`, which the alias file already handles. For example, the entries signed `[alecm]` match 242 commits, all by Alec Mitchell (`alecpm`). `[elro]` matches 179 commits, 88 percent by Laurence Rowe (`lrowe`).
- **Top unmatched with today's files**, all mapped by the proposals: `alecm` 523 → alecpm, `timo` 487 → tisto, `elro` 280 → lrowe, `stefan` 238 → stefanholek, `spliter` 171 → mishunov, `nouri` → dnouri, `rossp` → rpatterson, `yenzenz` → jensens, `dreamcatcher` → sidnei, `elvix` → baekholt, `ree` → reebalazs, `geoffd`/`plonista` → geoff-davis, `ldr` → lrowe.
- **Still unmatched** (entries): `thomasdesvenain` 235 (evidence share 0.74, under the 0.8 threshold; tdesvenain), `deo` 114 (Dorneles Treméa, share 0.6), `mj` 91 (Martijn Pieters, only 3 commits), `ramon` 64 (Ramon Navarro Bosch, 2 commits), `dunlapm` 41, `ender` 35 (two authors), `iElectric` 26 (domenkozar), `anthonygerrard` 25, `turgmr2`, `rochael`, `andym`, `swampmonkey`, `bmh`, `igbun`, `tarek`, `kteague`, `wiggy` (Wichert). Most of these have commit evidence just below the automatic threshold, or a person without a login.
- **Pitfall:** commit evidence sometimes points to the committer instead of the author. `[wald]` gives 4 commits by Hanno Schlichting, and `[piv]`/`[saffe]` give Timo Stollenwerk. These are exactly the cases of "work committed by others". So proposals must be reviewed by a person and never applied automatically. `wald` was removed from the prototype's proposals by hand.

## 6. Several names per entry

- 4.6 percent of the named entries from 2003 to 2012 have more than one name: 420 have two, 58 have three or more, and the most is seven. From 2013 on it is 3.4 percent.
- Full credit for each person gives 10,972 credits for 10,409 entries from 2003 to 2012, 5.4 percent more than one credit per entry. Splitting gives fractional numbers.
- The current rules give the PR to its opener and the commit to its author: one person, full credit. Several names in one entry mean joint work, often a pair at a sprint.

## 7. Comparison with the commit counts (2003–2012)

The comparison is between `per-year-with-proposals.csv` and `collected/contributors/YYYY-plone-contributors.csv` (`total_commits`).

- **Person-years** (930): Pearson 0.85 and Spearman 0.52 for 2003 to 2012, 0.92 and 0.56 for 2004 to 2008, 0.82 and 0.57 for 2009 to 2012. 498 person-years have both, 349 have commits only and 67 have entries only.
- **Per person over 2003 to 2012:** Pearson 0.93, Spearman 0.69. 294 people have commits and 203 have entries. 13 have entries but no commits, 104 have commits but no entries.
- **Totals per year:** about 0.15 to 0.3 entries per commit (2004: 3,053 commits and 662 credited entries; 2010: 8,821 and 1,669).
- **Entries but few commits** (work committed by others, or commits not linked to an account): `giacomos` (7 entries, 0 commits, second account `giacomos85`), `alecghica` 6/0, `stonor` 5/0, `pingviini` 4/0, `hathawsh` 4/1, `gogobd` 4/2, `sunew` 4/1, `joka` 3/1. Per year, 0 to 16 mapped people have entries but no commits in that year (2012: 16, 2010: 14, 2009: 11). The commit matching shows that 5.7 percent of the matched single-name entries were committed by someone other than the main author of that name.
- **Many commits, (almost) no entries:** `andymckay` 224 commits/0 entries, `jcameroncooper` 274/0, `domenkozar` 151/0 (his entries are signed `iElectric`, unmatched), `mjpieters` 280/1 (signed `mj`, unmatched), `aclark4life` 928/11 (buildout and website work), `longsleep` 296/2, `sthenault` 195/1, `zworkb` 213/4, `whitmo` 275/8, `tdesvenain` 395/11 (signed `thomasdesvenain`, unmatched). Part of this is mapping that is still missing. The rest is work without changelog entries: early years before the convention, infrastructure, translations, and the Subversion imports.
- **Entries per commit vary a lot** between people: `alecpm` 0.41, `hannosch`/`tiran` 0.31, `esteele`/`tisto` 0.10. This depends on personal habit (many small commits against one entry per change), which is a reason to report the metric next to commits, not to mix the two.

## 8. towncrier and the year range

- `@login` appears in 2016 (1 percent) and reaches 69 percent in 2026. The fragment's author is usually the PR author.
- Correlation of entries with merged PRs per person-year: 0.10 for 2011 to 2012, 0.70 for 2013 to 2015, 0.85 for 2016 to 2019, 0.88 for 2020 to 2025. From 2016 on, the metric mostly repeats the PR count.
- **Recommendation:** collect all years, because the cost is the same, but **use the metric for 2004 to 2012**. Mention 2013 to 2015 as a transition, and don't use it from 2016 on. 2003 and earlier are too thin: 69 entries, and the convention only starts in mid-2003.

---

# Draft spec: changelog entries in the pipeline

## Data source and collector

- **New collector** `scripts/collect/plone_changelogs.py`, run as `python -m scripts.collect.plone_changelogs`.
- **Repositories and branches:** the same selection as `plone_contributors` (all repositories of the organisation minus `excluded_repositories.csv`; default branch plus `git_history.release_branches`). It takes the files at the tip of each branch. The history of a changelog file is not needed, because its tip holds all its entries.
- **Clones:** the cache clones are treeless (`--filter=tree:0`) and can't show files without fetching. Option A, recommended: extend `scripts/lib/git_history.py` with `changelog_files(path, branches)`. It runs `git ls-tree` on the branch tips (which lazily fetches the tip trees) and then fetches only the matching blobs in one batch (`git -c fetch.negotiationAlgorithm=noop fetch origin <oid>...`, which the prototype tested). Option B: a separate shallow, blobless cache `.cache/changelogs/` (`--depth=1 --filter=blob:none`). It took about 10 minutes for all repositories, with 12 parallel workers.
- **File selection:** `HISTORY|CHANGES|CHANGELOG(.txt|.rst|.md)?` at any depth. Skip test fixtures, templates and vendored folders, and keep a short curated list of further skips in the code with reasons (`buildout.coredev:release/changelog.txt`, `jscalendar`). News fragments: skip them, they are unreleased.
- **Parser** in `scripts/lib/changelogs.py`: release headers (RST underline, Markdown `#`, old flush-left `Plone x.y - released ...`), entries (bullets with continuation lines), names (`[...]` at the end or on its own line, `@login`, `(name)` only when it maps), and dates (header, then tag date). GNU ChangeLog support (`date  Name  <email>`) is a follow-up for 7 old Products.
- **Output** `collected/changelogs/plone-changelog-entries.csv`, one file for all years, like `plone-plips.csv`. One row per deduplicated entry, with the columns `repository, file, branch, version, release_date, year, text_hash, names, logins, occurrences`. The per-year counts are `derived/changelog-entries/YYYY-plone-changelog-entries.csv` (`login, entries`) from `scripts/derive/changelog_entries.py`. Name mapping belongs in derive, so a mapping fix needs no new collection, see `docs/explanation/scope.md`.
- **Make targets:** `run-changelogs` (collect), `run-changelog-stats` (derive), added to `help` and `docs/reference/make-targets.md`. `make year` doesn't need it, because the metric is historical.
- **Errors:** as in the other collectors, a failed fetch stops the run and writes no data file.

## Counting rules (proposal)

1. An entry is a bullet in a release section of a changelog file of a counted branch.
2. It counts for the year of the release date of its earliest dated occurrence. Entries without a release date don't count.
3. One entry per `text_hash` within a repository. Across repositories, one per `text_hash` for texts of 60 or more characters, or with the same release date.
4. Every named person gets full credit (see decision D3).
5. Bots (`bot_accounts.csv`), `plone devs`, `zopeskel` and placeholders don't count.
6. The metric is reported for 2004 to 2012 (D1), next to commits, not added to them.

## Name mapping

- **Reuse first:** `commit_authors.csv` (local part of Subversion addresses), logins seen in `collected/contributors`, `mapping-github-username-to-fullname.csv`, then `account_aliases.csv`.
- **New curated file** `curated/mappings/changelog_names.csv` with the columns `changelog_name, github_username, name, source`. Like `commit_authors.csv`, it names a person without an account under `name`.
- **Public-record rule:** `source` links the changelog entry itself (file and line on GitHub, at a fixed commit) **and** a public record that links the name to the person: a commit whose message repeats the entry and that GitHub links to the login, a GitHub profile, or a credits file (`CREDITS.txt` of Plone 2.0). As for early commit authors, an identification without a public record says in `source` what it rests on, or the name stays unmatched.
- **Tool:** `python -m scripts.tools.unmatched_changelog_names [--propose]`, in the style of `unmatched_names`. It lists unmatched names by entries, and with `--propose` it prints proposals from commit evidence: the author's share, the number of commits, and an example commit URL. A person checks each proposal (see the committer pitfall in 5).
- **Short ambiguous names** (`mj`, `ramon`, `timo`, `stefan`, `deo`) are mapped per name, never by a guess from a login with the same spelling. Direct login matching stays limited to logins that appear in `collected/contributors`.

## Documentation

- `docs/explanation/counting-rules.md`: a new section "A changelog entry belongs to the people it names", covering dating by release, deduplication and full credit.
- `docs/explanation/history-and-coverage.md`, "Before pull requests": replace "could serve" with the actual range and its limits (the lag of the release date, 2003 thin).
- `docs/explanation/known-limitations.md`: dated by release, not by work; personal habits differ; committer instead of author in the evidence; GNU ChangeLogs not parsed yet.
- `docs/reference/data-sources.md`, `data-files.md`, `mapping-files.md` (`changelog_names.csv`), `make-targets.md`.
- `docs/how-to/link-old-commits-to-a-person.md`: a section on linking a changelog name.

## Tests (offline, pytest)

- `tests/test_changelogs_parser.py`: header forms with fixed strings (all examples in 3), entries with continuation lines and sub-bullets, name variants (`[a, b]`, `[a] [b]`, `[a and b]`, `@a`, the line before URLs, `(hopefully)` rejected), placeholders, refs such as `(#123)` stripped.
- `tests/test_changelogs_dedup.py`: the same entry on two branches counts once for the earliest release; the generic short text in two repositories counts twice; a cross-repository copy with the same date counts once.
- `tests/test_changelogs_collect.py`: `git_history` is replaced by a fake that returns `{(branch, path): text}`; checks the branch selection and the skipped paths; a failed fetch raises and writes nothing.
- `tests/test_changelog_names_format.py`: format check of `changelog_names.csv` (columns, no duplicate names, the login in the case GitHub has, `source` contains a URL).
- The prototype's `extract.py` already has the functions in testable form: `parse_changelog`, `parse_date`, `extract_names`, `text_hash`, `NameMapper`.

## Open decisions for Jens

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Year range in reports and recognition | 2004–2012 / 2004–2015 / all years | **2004–2012** in reports, 2013–2015 only as a transition note; collect all years anyway. |
| D2 | Role of the metric | its own column next to commits / an input to recognition / only a check | **Its own column and report section for 2004–2012**, not mixed into commits; recognition later, once the mapping has been reviewed. |
| D3 | Entries with several names | full credit each / split 1/n | **Full credit each**, as with sprint participants. The effect is 5 percent, and fractions would be new in the pipeline. |
| D4 | Dating | release date / date of the commit that added the line | **Release date**, simple and reproducible. Document the median lag of 15 days and the 13 percent in another year. The commit date would need blame on every file (blobs of the full history). |
| D5 | New curated mapping file | `curated/mappings/changelog_names.csv` / extend `commit_authors.csv` with pseudo-emails | **A new file**: the key is a name, not an email, and the source is different. |
| D6 | Proposals from commit evidence | apply automatically above a threshold / tool proposes, a person confirms | **Tool proposes, a person confirms in a PR** (the committer pitfall, `wald` → hannosch). |
| D7 | Repository scope | all `plone` repositories like the collector / core packages only | **Same as the collector** (excluded list applies). `aurora`, `guillotina` and similar repositories hardly matter before 2013. |
| D8 | Clones | extend the existing cache (treeless, lazy fetch) / separate shallow cache | **Extend `git_history`**: one cache, and the blobs fetched are few (about 1,900 files). |
| D9 | GNU ChangeLogs (7 old Products, about 600 records from 2003 to 2006) | parse in the first PR / follow-up | **Follow-up issue**: small volume, a different format, but strong attribution (email). |
| D10 | Second accounts found on the way (`giacomos`/`giacomos85`) | add to `account_aliases.csv` with a public record / ignore | **Add, with a public record**, in a separate PR. |

Assisted-by: Claude Opus 5.5
