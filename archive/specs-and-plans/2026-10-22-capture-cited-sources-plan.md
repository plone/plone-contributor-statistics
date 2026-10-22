# Capture the sources the mappings cite — Implementation Plan (plan 2a)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every source that `curated/mappings/` cites today (2,127 distinct URLs) is captured once into the source register, with the passages around the quotes the cells hold, so that plan 2c can turn the source cells into citations offline. The mapping files themselves don't change in this plan.

**Architecture:** First four small extensions of the capture library that the bulk run needs (Wayback redirects, GitHub issue and comment adapter, Google Docs adapter, a fallback to passages around a name when a cell has no quote) and a memo for the register. Then a migration tool that reads the source cells through the model and writes a work list (one JSON line per URL, with its quotes, names and kind), a batch mode of the capture command that works through the list resumably, and the networked run itself.

**Tech Stack:** Python 3.12, the existing `scripts/lib/capture/` and `scripts/lib/model/`, pytest.

**Spec:** `archive/specs-and-plans/2026-10-22-sources-and-events-design.md` (sections "source", "Capture tools", "Migration" step 1). Plan 1: `archive/specs-and-plans/2026-10-22-sources-and-capture-plan.md`.

**The plans after this one:** 2b collector of commit domains per login and year; 2c the switch of `people`, `identities`, `affiliations` to the new structure with citations, decisions and computed counting (reads the results of this plan); 3 events and community data (captures the community sources, about 960 videos among them); 4 organiser credit; 5 reviewed restructuring of `notes`.

## Global Constraints

- Work in the worktree `.claude/worktrees/citations` on branch `capture-cited-sources` (rename the branch from `citations` before the first commit: `git branch -m citations capture-cited-sources`), from `origin/main` 0458001. Python from `~/.venvs/plone-contributor-statistics`.
- The repository stores **only passages** around quotes (about a paragraph), never whole pages, archived copies or full captions. Exception already in place: the whole short text of a commit or a GitHub profile; new exception here: the whole text of an issue or comment **of this repository** (`plone/plone-contributor-statistics`), which is our own public record.
- Every request goes through `Fetcher` (paced, cached in the main checkout's `.cache/sources/`, `PLONE_STATS_CACHE` overrides); Internet Archive at most one request per 4 s; the GitHub API through `github_get` with `GITHUB_TOKEN` from the environment, never a `--token` option.
- `scripts/lib/model/` is the only code that reads or writes `curated/`; tools read the registers through the model.
- Nothing in `curated/mappings/` changes in this plan.
- Tests are offline (fakes for HTTP, `git`, `yt-dlp`, `pdftotext`) and never write into the real `.cache` (the autouse fixture `private_cache` in `tests/conftest.py` sets `PLONE_STATS_CACHE`).
- Commit footers: `Assisted-by: <implementing model>`, `Assisted-by: Claude Opus 5.5`, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Pull request: `Assisted-by:` lines for every model used, then `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Docs change in the same PR when the capture command or the source register changes behaviour (`docs/how-to/capture-a-source.md`).
- Migration-only code (Task 6) is archived to `archive/` in plan 2c, after its last use, as `scripts/tools/migrate_data_structure.py` was before.

## Review Focus

1. **A cell with a quote followed by two URLs** (`"quote", speaker page: <live> (archived: <wayback>)`) attaches the quote to both URLs; the run must not count the live copy's "missing" as a failure of the source when the archived copy holds it. → Task 6, `test_quote_attaches_to_every_url_of_its_segment`; Task 7 results keep per-URL outcomes.
2. **The same Google Doc or GitHub page under several URL spellings** (`/edit`, no `/edit`, `#issuecomment-…`) must give one source per document or comment, and two different comments of one pull request two sources. → Task 2 `test_comment_fragments_are_kept`, Task 3 `test_google_doc_spellings_share_an_id`.
3. **A Wayback request that lands on another capture** must be recorded under the capture actually read. → Task 1 `test_redirected_capture_is_recorded_under_its_own_timestamp`.
4. **An interrupted batch run** must resume without fetching what it already captured and without duplicating result lines. → Task 7 `test_batch_resumes_after_interruption`.
5. **A cell without any quote** (a label in our own words) must still store a passage: the one naming the person or organisation; never the whole page. → Task 4 `test_names_cut_the_passage_when_no_quote_is_given`.

---

### Task 1: Wayback redirects and a memo of the register

**Files:**
- Modify: `scripts/lib/capture/fetch.py`, `scripts/lib/capture/__init__.py`, `scripts/lib/model/sources.py`
- Test: `tests/test_capture_fetch.py`, `tests/test_capture.py`, `tests/test_model_sources.py`

**Interfaces:**
- Produces: `Raw.final_url: str` (the URL after redirects, `response.url`; stored in the cache `.json`; a cache entry without it reads as `final_url = url`).
- Produces: in `capture()`, a Wayback read whose `final_url` carries another 14-digit timestamp than requested is recorded under the timestamp read: `archive_url`, `id` and the default `date` follow `final_url`; `CaptureResult.source_id` is that id.
- Produces: `load_sources()` keeps a memo keyed by `(path, st_mtime_ns, st_size)`; `write_source()` updates the memo after writing. Behaviour unchanged, only faster for runs of thousands of captures.

- [ ] **Step 1:** Write failing tests: `test_raw_records_the_final_url` (fake session response with `.url` differing from the request), `test_old_cache_entry_without_final_url`, `test_redirected_capture_is_recorded_under_its_own_timestamp` (request `…/web/20100101000000id_/http://a.org/x`, response url `…/web/20100125023558id_/http://a.org/x` → row `archive_url == 'https://web.archive.org/web/20100125023558/http://a.org/x'`, id `source_id('http://a.org/x', '20100125023558')`, date 2010-01-25), `test_load_sources_memo_sees_external_edits` (write the file directly between two loads → second load sees it).
- [ ] **Step 2:** Run `python -m pytest tests/test_capture_fetch.py tests/test_capture.py tests/test_model_sources.py -q` — FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the same — PASS; full suite once.
- [ ] **Step 5:** Commit — "Record a Wayback capture under the timestamp actually read".

### Task 2: GitHub issues, pull requests and their comments

**Files:**
- Modify: `scripts/lib/model/sources.py` (`normalize_url`), `scripts/lib/capture/extract.py`, `scripts/lib/capture/__init__.py`
- Test: `tests/test_model_sources.py`, `tests/test_capture_extract.py`, `tests/test_capture.py`

**Interfaces:**
- `normalize_url` keeps the fragment of a `github.com` URL when it matches `^(issuecomment-\d+|discussion_r\d+|pullrequestreview-\d+)$`; every other fragment is still dropped. (No source in the register has such a fragment yet, so no id changes.)
- `adapter_for(url)` returns `'github-issue'` for `github.com/<owner>/<repo>/(issues|pull)/<number>` with or without such a fragment (checked after Wayback and before `github-profile`).
- `extract_github_issue(owner, repo, number, fragment, session) -> Extracted`:
  - `issuecomment-<id>` → `GET /repos/<o>/<r>/issues/comments/<id>`; `discussion_r<id>` → `GET /repos/<o>/<r>/pulls/comments/<id>`; `pullrequestreview-<id>` → `GET /repos/<o>/<r>/pulls/<number>/reviews/<id>`. Text: `Author: <login>`, `Date: <created_at or submitted_at>`, blank line, body. `date` = that date.
  - no fragment → `GET /repos/<o>/<r>/issues/<number>` and all pages of `/issues/<number>/comments`: the issue as one block (`Title:`, `Author:`, `Date:`, body), then each comment as its own block (`Author:`, `Date:`, body), blocks separated by blank lines. `date` = the issue's creation date.
- Kind for the adapter: `issue-comment`. Passage rule: for a source of `plone/plone-contributor-statistics`, the whole extracted text is stored (our own public record); for other repositories, the block that contains the quote (cut_passage on the block text, blocks being the issue and each comment).

- [ ] **Step 1:** Failing tests: `test_comment_fragments_are_kept` (two `#issuecomment-` URLs of one PR → two ids; `#top` dropped), `test_adapter_for_github_issue`, `test_extract_issue_comment`, `test_extract_issue_with_comments_paginates`, `test_own_repository_issue_is_stored_whole`, `test_other_repository_issue_stores_the_block`.
- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Capture GitHub issues, pull requests and their comments".

### Task 3: Google Docs

**Files:**
- Modify: `scripts/lib/model/sources.py` (`normalize_url`), `scripts/lib/capture/extract.py`, `scripts/lib/capture/__init__.py`
- Test: `tests/test_model_sources.py`, `tests/test_capture_extract.py`

**Interfaces:**
- `normalize_url` turns `docs.google.com/document/d/<id>[/anything][?…]` into `docs.google.com/document/d/<id>`.
- `adapter_for` → `'google-doc'` for that pattern (live URLs only; a Wayback copy stays `generic`).
- `extract_google_doc(fetcher, doc_id) -> Extracted`: fetches `https://docs.google.com/document/d/<id>/export?format=txt` through the fetcher; decodes UTF-8 (strip a BOM); paragraphs = blocks separated by blank lines (single newlines in the export are paragraph ends: join non-empty lines with `\n\n`); title from the first non-empty line; `date` None. A non-200 answer (private document) → `ExtractError('not a public document')`. Kind `page`.

- [ ] **Step 1:** Failing tests: `test_google_doc_spellings_share_an_id` (`…/d/X`, `…/d/X/edit`, `…/d/X/edit?usp=sharing` → one id), `test_adapter_for_google_doc`, `test_extract_google_doc`, `test_private_google_doc_raises`.
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Capture public Google Docs through their text export".

### Task 4: Passages around a name when a cell has no quote

**Files:**
- Modify: `scripts/lib/capture/__init__.py`, `scripts/lib/capture/passages.py`, `scripts/tools/capture.py`, `docs/how-to/capture-a-source.md`
- Test: `tests/test_capture.py`, `tests/test_capture_passages.py`, `tests/test_tool_capture.py`

**Interfaces:**
- `find_name(text: str, name: str) -> tuple[int, int] | None` in `passages.py`: like `find_quote` but case-insensitive, accent-insensitive (compare after NFKD and dropping combining marks, on top of `normalize_text`), and only at word boundaries; returns the first occurrence's span in the original text.
- `capture(..., names: Sequence[str] = ())`: used **only when `quotes` is empty**. For each name, `find_name` in `text`, else `full_text`; the passage around the first occurrence is added. Names found count as `added` (the passage), names not found go to `missing`. Kinds whose whole text is stored (profile, commit, own-repository issue) store it whenever the source has no quotes, whether or not a name is found: the short text itself is the evidence (a profile often shows a login, not the display name). A new source with neither a quote nor a found name stores nothing (as today for quotes).
- CLI: `--name TEXT` (repeatable); `--quote` is no longer required when at least one `--name` is given. Docs: a short paragraph on `--name` in the how-to.

- [ ] **Step 1:** Failing tests: `test_find_name_ignores_case_and_accents` (`'jyvaskyla'` finds `Jyväskylä`; `'Ann'` doesn't match inside `Annette`), `test_names_cut_the_passage_when_no_quote_is_given`, `test_names_are_ignored_when_quotes_are_given`, `test_profile_with_name_stores_whole_text`, `test_cli_accepts_name_without_quote`.
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Cut a passage around a name when a source has no quote".

### Task 5: Batch mode of the capture command

**Files:**
- Modify: `scripts/tools/capture.py`, `docs/how-to/capture-a-source.md`
- Test: `tests/test_tool_capture.py`

**Interfaces:**
- Consumes: `capture()` (with `names`).
- Work list format (JSON lines, one object per line): `{"url": str, "quotes": [str], "names": [str], "kind": str | null}`.
- Results format (JSON lines): `{"url": str, "source_id": str | null, "created": bool, "added": [str], "missing": [str], "unreachable": bool, "error": str | null}`.
- `python -m scripts.tools.capture --batch WORKLIST --results RESULTS`: for each work-list line whose `url` has no line in RESULTS yet, call `capture(url, quotes, kind=kind, names=names)` and append one result line (flushed at once); a `CaptureError` becomes a result line with `error` set, and the run continues; one `Fetcher` and one GitHub session for the whole run. Progress on stderr every 25 items (`<done>/<total>  <created> new, <missing> with missing quotes, <errors> errors`). Exit status 0 when the run reached the end, whatever the outcomes.

- [ ] **Step 1:** Failing tests (capture patched): `test_batch_writes_one_result_per_url`, `test_batch_resumes_after_interruption` (RESULTS already has the first URL → only the second is captured; no duplicate lines), `test_batch_records_errors_and_continues`.
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Capture a work list of sources in one resumable run".

### Task 6: The work list of the sources the mappings cite (migration tool)

**Files:**
- Create: `scripts/tools/cited_sources.py`, `tests/test_cited_sources.py`

**Interfaces:**
- Consumes: the model (`load_registry`, `load_rejections`, `read_rows` as needed) — never `csv` on `curated/` directly.
- Produces: `split_segments(cell: str) -> list[str]` — split on `;` followed by whitespace, outside double quotes.
- Produces: `parse_segment(segment: str) -> list[Cited]`, `@dataclass(frozen=True) class Cited: url: str; quote: str | None; label: str` — every URL of the segment (pattern `https?://[^\s;"<>]+`, trailing `.,)` stripped, a `(archived: …)` URL included) is one `Cited`; `quote` is the text inside the last pair of double quotes that ends before the segment's first URL (CSV-doubled `""` already undone by the reader), else None; `label` is the rest of the text before the first URL with quote, `:` and surrounding punctuation stripped.
- Produces: `kind_hint(url: str, label: str) -> str | None` — `'speaker-page'` when the label contains "speaker page" (case-insensitive); `'profile'` when it contains "GitHub profile"; else None (the capture adapters decide).
- Produces: `work_list(registry, rejections) -> list[dict]` — one item per distinct URL (merged across every cell of `people.source`, `identities.source`, `affiliations.source` and `affiliations.notes`, `rejected_proposals.source` and `.reason`), with `quotes` = the distinct quotes attached to it (in first-seen order), `names` = the display name of the person of the row plus the person's `name` identities plus the organisation's name and aliases (affiliations only), `kind` = the first non-None hint.
- Produces: GitHub commit-search URLs (`github.com/search?…type=commits`) are not work-list items; `resolve_searches(urls, session) -> dict[str, list[str]]` asks the search API once per URL (through `github_get`, cached as JSON in `cache_dir('github-search', …)`, the same folder `scripts/tools/github_evidence.py` uses) and maps each search URL to the html URLs of its first three commits; those commit URLs become work-list items (names: the person's).
- CLI: `python -m scripts.tools.cited_sources --worklist PATH --searches PATH` writes the work list (JSON lines, sorted by URL) and the search mapping (JSON object). Module docstring says it is migration code for plan 2c and will be archived.

- [ ] **Step 1:** Failing tests: `test_split_segments_respects_quotes` (a quote containing `; ` stays whole), `test_parse_segment_quote_label_url` (`"He works at X.", Plone Conference 2017 speaker page: https://a.org/p` → quote, label `Plone Conference 2017 speaker page`, url), `test_quote_attaches_to_every_url_of_its_segment` (live + archived), `test_segment_without_quote`, `test_kind_hint`, `test_work_list_merges_urls_across_files` (tmp registers via the `write_registers` fixture / `tmp_repo`), `test_search_urls_resolve_to_commits` (fake session).
- [ ] **Step 2:** Run — FAIL.  **Step 3:** Implement.  **Step 4:** Run — PASS; full suite once.
- [ ] **Step 5:** Commit — "Build the work list of the sources the mappings cite".

### Task 7: The capture run (networked)

**Files:**
- Create: `curated/sources/excerpts/*.md` (many), `archive/migration-to-sources/README.md`, `archive/migration-to-sources/worklist.jsonl`, `archive/migration-to-sources/searches.json`, `archive/migration-to-sources/capture-results.jsonl`
- Modify: `curated/sources/sources.csv`, `archive/README.md` (a row for the new folder)

- [ ] **Step 1:** Build the work list: `GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.cited_sources --worklist archive/migration-to-sources/worklist.jsonl --searches archive/migration-to-sources/searches.json`. Expected: about 2,100 items, no search URLs among them.
- [ ] **Step 2:** Run in the background, resumable: `GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.capture --batch archive/migration-to-sources/worklist.jsonl --results archive/migration-to-sources/capture-results.jsonl`. Expected duration: one to two hours (about 450 Internet Archive requests at 4 s). If it stops, run the same command again.
- [ ] **Step 3:** Summarise the results (a short script in the scratchpad, not committed): counts of created, unreachable, errors, items with missing quotes, by host. Re-run once for items with `error` set (delete their result lines first) to rule out transient failures; leave the rest as they are.
- [ ] **Step 4:** `python -m scripts.tools.check` and `python -m pytest -q` — PASS. Spot-check ten random excerpt files: each holds passages, none a whole page.
- [ ] **Step 5:** Write `archive/migration-to-sources/README.md`: what the three files are, the commands that made them, the date, that plan 2c reads them, and the summary counts (counts belong here, in the archive, not in `docs/`). Add the folder to `archive/README.md`.
- [ ] **Step 6:** Commit — "Capture the sources the mappings cite".

### Task 8: Pull request

- [ ] **Step 1:** Copy this plan unchanged to `archive/specs-and-plans/2026-10-22-capture-cited-sources-plan.md` (the design is archived already); commit.
- [ ] **Step 2:** `python -m pytest -q && python -m scripts.tools.check && make docs` — PASS.
- [ ] **Step 3:** Ask Jens before pushing; then push `capture-cited-sources` and open the PR: the four library extensions, the batch mode, the work-list tool (migration code, archived in 2c), the run and its summary (from the archive README), what is left for 2c.
