# Capture the sources of the community data — Implementation Plan (plan 3a)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every source the curated community data cites in its `source` columns (2,080 distinct URLs, 253 already in the register, about 235 new videos) is captured once into the source register, so plan 3b can turn the community files into event, talk, training, organiser and role records citing source ids, offline. YouTube captions, once downloaded, are kept in the cache and never fetched again. The community files themselves don't change.

**Architecture:** As plan 2a: a work-list tool reads the community cells (through the model), the existing batch mode captures them resumably, the results go to `archive/migration-to-events/`. Two library changes first: video captions are kept and reused from the cache, and the cell parser that plan 2a archived becomes live library code (plan 3b's migration needs it too).

**Tech Stack:** Python 3.12, the capture library, pytest. yt-dlp with Jens's PO-token provider for the YouTube part (Jens installs and starts it; Claude never installs it).

**Spec:** `archive/specs-and-plans/2026-10-22-sources-and-events-design.md` ("events and community data", "Capture tools", Migration step 1). Precedent: `archive/specs-and-plans/2026-10-22-capture-cited-sources-plan.md`, `archive/migration-to-sources/`.

## Global Constraints

- Worktree `.claude/worktrees/community-sources`, branch `community-sources`, from `origin/main` 0dda4f4. Python `~/.venvs/plone-contributor-statistics`.
- Passages only; whole text only for commits, profiles and own-repository issues. Every request through `Fetcher` (shared cache in the main checkout's `.cache`, Internet Archive 4 s, YouTube 30 s); GitHub API with `GITHUB_TOKEN` from the environment.
- **A YouTube caption track, once downloaded, is kept** in the cache and reused; no request to YouTube for a video whose tracks are cached, unless `refresh`.
- **Claude never installs or starts the PO-token provider.** The video part of the run happens only when Jens has started it; if YouTube refuses captions, the videos stay "not captured" and the run goes on.
- The curated community files and the registers don't change in this plan (only `curated/sources/` grows).
- Tests offline; the model is the only reader/writer of `curated/`; commit footers `Assisted-by: <implementing model>`, `Assisted-by: Claude Opus 5.5`, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, each once; docs in the same PR; no statistics in prose.

## Review Focus

1. **A video re-read after the first capture** (another citing row, a later plan) must not contact YouTube. → Task 1 `test_cached_tracks_are_reused_without_a_request`.
2. **Old translation tracks** left in a cache folder by the first adapter (plain `en.vtt`, `de.vtt` from 2026-10-22) must never be read as captions. → Task 1 `test_only_tracks_of_the_manifest_are_read`.
3. **A community cell citing several URLs** (sprint reports plus Board minutes) gives one work item per URL, with the row's names. → Task 3 `test_every_url_of_a_cell_is_an_item`.
4. **A WPD talk whose source is the recording** gets the speakers' names for its passage. → Task 3 `test_video_source_gets_the_speakers`.
5. **An interrupted run** resumes without repeating requests (batch mode, cache). → covered by plan 2a's tests; Task 4 checks it once on the real run.

---

### Task 1: Keep YouTube captures in the cache

**Files:** `scripts/lib/capture/extract.py`, `scripts/lib/capture/__init__.py` (if the workdir is chosen there), tests in `tests/test_capture_extract.py`, `docs/how-to/capture-a-source.md`.

**Interfaces:**
- The caption folder of a video is `cache_dir('sources', 'video', <YouTube video id>)` (by video id, not source id, so two sources of one video share it).
- After a successful download `extract_video` writes `tracks.json` there: `{"url": …, "tracks": ["<id>.it-orig.vtt", …], "title": …, "fetched": "<UTC ISO>"}` listing only the files this adapter downloaded (original auto tracks or manual tracks).
- `extract_video(url, workdir, run, fetcher, which, refresh=False)`: when `tracks.json` exists and every listed file is present and `refresh` is false, it reads those tracks and the stored title **without running yt-dlp**. Otherwise it downloads as today into the folder **without deleting** anything; files not in the new manifest are ignored, never read. Never delete caption files.
- `capture(..., refresh=True)` passes `refresh` through.

- [ ] Step 1: failing tests: `test_cached_tracks_are_reused_without_a_request` (fake run asserts it is not called), `test_only_tracks_of_the_manifest_are_read` (a stray `x.en.vtt` beside `x.it-orig.vtt` is ignored), `test_refresh_downloads_again_and_keeps_old_files`, `test_two_sources_of_one_video_share_the_folder`.
- [ ] Step 2: run — FAIL; Step 3: implement; Step 4: run — PASS, full suite once.
- [ ] Step 5: migrate the 77 existing caption folders: for every folder under the cache's `sources/video/<source id>/` that holds `-orig` or manual tracks of a captured video source, move them to the new by-video-id folder and write its `tracks.json` (a small one-off script in the scratchpad, local cache only; report what it moved). Commit the code — "Keep the caption tracks of a video in the cache".

### Task 2: The cell parser as library code

**Files:** create `scripts/lib/cells.py`, `tests/test_cells.py`; copy (don't import) `split_segments`, `parse_segment`, `Cited`, the quote helpers and their tests from `archive/migration-to-citations/cited_sources.py` / its tests, unchanged in behaviour; `scripts/tools/cite_snippets.py` uses `scripts.lib.cells` for its quote parsing if it duplicates it today.

- [ ] Steps: tests first (the copied tests, adapted imports), implement, full suite, commit — "Make the cell parser library code".

### Task 3: The work list of the community sources

**Files:** create `scripts/tools/community_sources.py` (migration code for plan 3b, archived after it), `tests/test_community_sources.py`.

**Interfaces:**
- Reads every community file through the model (`scripts/lib/model/community.py` readers or `read_rows` on `paths.COMMUNITY`), every `source` cell (not the `video` column, not `notes`).
- One item per distinct URL: `{"url", "quotes", "names", "kind"}` like plan 2a's work list. `quotes` = the cell's quotes (Task 2 parser); `names` = display names and `name` identities of the row's people (speakers, trainers, organisers, `person`) plus names and aliases of the row's organisations (organisations cells, `organisation` of plone-conference rows); `kind` hint: `video` for video hosts, `speaker-page` when the label says speaker page, else none.
- URLs already in the register are skipped when every quote of the item is stored in their excerpt (they'd return without a request anyway; listing them keeps the results complete — include them, the batch mode makes no request for them).
- CLI `python -m scripts.tools.community_sources --worklist PATH [--videos-only | --no-videos]` writes JSON lines sorted by URL and prints counts (items, videos, already registered).

- [ ] Steps: failing tests (`test_every_url_of_a_cell_is_an_item`, `test_video_source_gets_the_speakers`, `test_names_from_people_and_organisations`, `test_video_column_is_not_a_source`, `test_split_by_videos`), implement, full suite, commit — "Build the work list of the community sources".

### Task 4: The capture run (networked)

**Files:** `curated/sources/` (grows), `archive/migration-to-events/README.md`, `archive/migration-to-events/{worklist.jsonl, capture-results.jsonl}`, a row in `archive/README.md`.

- [ ] Step 1: work list without videos; batch run in the background (Internet Archive pace; expect one to two hours); resume after interruptions.
- [ ] Step 2: ask Jens to start the PO-token provider; then the video work list (about 235 new videos, 30 s apart, about two hours); when YouTube refuses, the items stay "not captured" — no retry loop.
- [ ] Step 3: retry once the items with transient errors; summarise (stored, partly missing, nothing found, errors by kind, videos); spot-check ten excerpts (passages only); `python -m scripts.tools.cite_snippets` dry run must report nothing to fill (community rows aren't cited yet).
- [ ] Step 4: `python -m pytest -q`, `python -m scripts.tools.check`; README with commands, dates, counts, the PO-token note; commit — "Capture the sources of the community data".

### Task 5: Pull request

- [ ] Copy this plan unchanged to `archive/specs-and-plans/2026-10-25-community-sources-plan.md`; verify (tests, check, `make docs`); ask Jens before pushing; open the PR.
