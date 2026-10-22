# Sources and capture tools Implementation Plan (plan 1 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A source register in `curated/sources/` (one row per source, one excerpt file with the cited passages) and a reusable capture tool that fetches a source once, caches the raw download locally, and stores only the passages around given quotes.

**Architecture:** The model (`scripts/lib/model/sources.py`) reads and writes the register, as it does for every curated file. A library `scripts/lib/capture/` does the work: `fetch.py` (polite, cached HTTP; Wayback helpers), `extract.py` (raw download → readable text, with site adapters), `passages.py` (find a quote, cut its passage). `scripts/tools/capture.py` is the command line. Nothing cites sources yet; plan 2 migrates the affiliations and identities onto them.

**Tech Stack:** Python 3.12, requests, trafilatura (new dependency), frictionless, pytest. External programs used when present: `pdftotext` (poppler), `yt-dlp`, `git`.

**Spec:** `2026-10-22-sources-and-events-design.md` (same folder; archived with this plan in `archive/specs-and-plans/` before the PR). Sections implemented here: "source", "Capture tools", the source checks of "Checks".

**The five plans:** 1 sources and capture (this); 2 affiliations, citations, decisions, counting, commit-domain collector and the migration of the mappings; 3 events and community data; 4 organiser credit through persons; 5 reviewed restructuring of `notes`.

## Global Constraints

- Work in the worktree `.claude/worktrees/sources-capture` on branch `sources-capture` (from `origin/main` c987479). Run everything from its root; Python from `~/.venvs/plone-contributor-statistics`.
- The repository stores **only passages we cite** (about the paragraph around a quote), never whole pages, Wayback copies or full captions: legally we may only quote.
- Raw downloads go to the gitignored `.cache/sources/` only. The constant lives in `scripts/lib/capture/fetch.py`, not in `paths.py` (`tests/test_layout.py::test_paths_follow_layout` allows only `curated/`, `collected/`, `derived/`, `reports/` there).
- A source with a cached raw copy is never fetched again unless `refresh=True`.
- Wayback: fetch with the `id_` form `https://web.archive.org/web/<14 digits>id_/<url>`; at most 15 requests a minute to `web.archive.org` and `archive.org` (4.0 s between requests); 1.0 s between requests to any other host.
- User-Agent: `plone-contributor-statistics/1.0 (+https://github.com/plone/plone-contributor-statistics)`.
- GitHub API calls go through `scripts.lib.github_api.github_get` with the token from `GITHUB_TOKEN` (never a `--token` option).
- `scripts/lib/model/` is the only code that reads or writes `curated/`; the capture library calls the model to write.
- Tests are offline: HTTP, `git`, `pdftotext` and `yt-dlp` are faked.
- Commit messages end with the model footer, e.g. `Assisted-by: Claude Sonnet 5.5` then `Assisted-by: Claude Opus 5.5` (the implementing model first), and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- A PR that changes what the docs describe updates `docs/` in the same PR; `docs/reference/curated-files.md` is regenerated with `python -m scripts.tools.schema_docs`, `curated/datapackage.json` with `python -m scripts.tools.datapackage`.

## Review Focus

1. **The same page under different URLs** (Wayback `if_`/`id_`/no flag, `http` vs `https`, `:80`, a `#fragment`, a trailing `/`) must give one source id; the query string must stay (`?searchterm=None` pages differ). → Task 1, `test_source_id_ignores_url_noise`.
2. **A quote written differently from the page** (typographic quotes and dashes, non-breaking spaces, line breaks inside the quote, an ellipsis `…` that skips text) must still be found, and the stored passage must keep the page's own spelling. → Task 3, `test_find_quote_normalizes` and `test_find_quote_with_ellipsis`.
3. **Old pages in Latin-1 or Windows-1252** (plone.org 2004–2006 captures) must decode without mojibake. → Task 5, `test_extract_html_decodes_declared_charset`.
4. **An interrupted run**: raw copy cached but no source row written; rerunning must finish without a network request. → Task 7, `test_capture_after_interruption_uses_cache`.
5. **Capturing the same quote twice** must not duplicate the passage; a second quote from the same paragraph must not add the paragraph again. → Task 2, `test_add_passage_is_idempotent`; Task 7, `test_second_quote_in_same_paragraph`.

---

### Task 1: Source register, schema and model reader

**Files:**
- Create: `curated/schemas/sources.json`, `curated/sources/sources.csv` (header only), `scripts/lib/model/sources.py`, `tests/test_model_sources.py`
- Modify: `scripts/lib/paths.py`, `scripts/lib/model/__init__.py`, `tests/conftest.py` (`EMPTY_MAPPINGS`), `tests/test_schemas.py` (`KINDS`), `tests/test_model_is_the_only_reader.py` (`CONSTANTS`), `scripts/tools/schema_docs.py` (`GROUPS`, `ONE_ROW_IS`), `curated/datapackage.json` (regenerate), `docs/reference/curated-files.md` (regenerate)

**Interfaces:**
- Produces in `scripts.lib.paths`: `SOURCES_DIR = Path('curated/sources')`, `SOURCES = SOURCES_DIR / 'sources.csv'`, `EXCERPTS_DIR = SOURCES_DIR / 'excerpts'`.
- Produces in `scripts.lib.model.sources` (re-exported from `scripts.lib.model`):
  - `SOURCE_KINDS = ('page', 'speaker-page', 'profile', 'commit', 'video', 'pdf', 'register', 'issue-comment', 'decision')`
  - `@dataclass(frozen=True) class Source: id: str; kind: str; title: str; date: datetime.date; url: str; archive_url: str | None; fetched: datetime.datetime; notes: str | None`
  - `normalize_url(url: str) -> str`
  - `split_archive_url(url: str) -> tuple[str, str] | None` — `(original_url, timestamp)` for a Wayback URL, else `None`
  - `archive_url_of(original: str, timestamp: str) -> str` — the readable form `https://web.archive.org/web/<timestamp>/<original>`
  - `source_id(url: str, timestamp: str | None = None) -> str`
  - `load_sources() -> dict[str, Source]` (by id; raises `FileNotFoundError` without the file)
  - `excerpt_path(source_id: str) -> Path` → `paths.EXCERPTS_DIR / f'{source_id}.md'`

Schema `sources.json`, fields in this order: `id` (string, required, pattern `^[0-9a-f]{12}$`), `kind` (string, required, enum `SOURCE_KINDS`), `title` (string, required), `date` (date, required), `url` (string, required, pattern `^https?://.*$`), `archive_url` (string, pattern `^https://web\.archive\.org/web/\d{14}/https?://.*$`), `fetched` (datetime, required), `notes` (string). `primaryKey: ["id"]`. Descriptions in the style of the other schemas (one sentence each; `date`: "The date the source speaks for: its publication date if it shows one, else the capture date of the archived copy, else the day it was fetched."; `fetched`: "When the source was read, in UTC.").

`normalize_url`: scheme dropped from the key (`http` = `https`), host lower-cased, default port (`:80`, `:443`) and `www.` kept as is, fragment dropped, trailing `/` dropped except for the bare host, query kept. Returns e.g. `github.com/fredvd`.
`split_archive_url` accepts `web.archive.org/web/<ts><flag>/<url>` with any flag (`id_`, `if_`, `im_`, `js_`, `cs_`, or none), `http` or `https`, and an original with or without scheme (`http://` added when missing).
`source_id(url, ts)`: `hashlib.sha1(f'{normalize_url(url)} {ts or ""}'.encode()).hexdigest()[:12]`.

- [ ] **Step 1: Write the failing tests** in `tests/test_model_sources.py`:

```python
def test_source_id_ignores_url_noise():
    ids = {source_id(u) for u in ('https://github.com/fredvd', 'http://github.com/fredvd/',
                                  'https://GitHub.com:443/fredvd#top')}
    assert len(ids) == 1
    assert source_id('https://a.org/x?searchterm=None') != source_id('https://a.org/x')
    assert len(source_id('https://a.org/x')) == 12

def test_split_archive_url_accepts_every_flag():
    for url in ('https://web.archive.org/web/20051017042508/http://ploneconf2005.bluedynamics.net:80/speakers',
                'http://web.archive.org/web/20051017042508id_/http://ploneconf2005.bluedynamics.net:80/speakers',
                'https://web.archive.org/web/20051017042508if_/ploneconf2005.bluedynamics.net:80/speakers'):
        original, ts = split_archive_url(url)
        assert ts == '20051017042508'
        assert normalize_url(original) == 'ploneconf2005.bluedynamics.net/speakers'
    assert split_archive_url('https://plone.org/foundation') is None

def test_archived_and_live_copies_are_different_sources():
    assert source_id('https://limi.net/about') != source_id('https://limi.net/about', '20100125023558')

def test_load_sources_reads_the_register(tmp_repo):
    sid = source_id('https://limi.net/about', '20100125023558')
    paths.SOURCES.write_text(
        'id,kind,title,date,url,archive_url,fetched,notes\n'
        f'{sid},page,About Limi,2010-01-25,https://limi.net/about,'
        'https://web.archive.org/web/20100125023558/http://limi.net:80/about,2026-10-22T14:03:51Z,\n',
        encoding='utf-8')
    source = load_sources()[sid]
    assert source.date == datetime.date(2010, 1, 25)
    assert source.fetched.tzinfo is not None
    assert excerpt_path(sid) == paths.EXCERPTS_DIR / f'{sid}.md'
```

Also add `'sources'` to `KINDS` in `tests/test_schemas.py`, and `paths.SOURCES: 'id,kind,title,date,url,archive_url,fetched,notes\n'` to `EMPTY_MAPPINGS` in `tests/conftest.py`, and `'SOURCES_DIR', 'SOURCES', 'EXCERPTS_DIR'` to `CONSTANTS` in `tests/test_model_is_the_only_reader.py`.

- [ ] **Step 2: Run** `python -m pytest tests/test_model_sources.py tests/test_schemas.py -q` — expected: FAIL (import error, missing schema).
- [ ] **Step 3: Implement** the paths, the schema, `scripts/lib/model/sources.py` (read through `read_rows`), the re-exports, the header-only `curated/sources/sources.csv`; add a `('Sources', 'The sources the registers cite, in `curated/sources/`, each with an excerpt file of the cited passages.', [('sources', 'Sources')])` group after "Registers" in `schema_docs.GROUPS` and `'sources': 'one source: a page, profile, commit, video or decision that we read once; its excerpt file holds the passages we cite.'` in `ONE_ROW_IS`; run `python -m scripts.tools.datapackage` and `python -m scripts.tools.schema_docs`.
- [ ] **Step 4: Run** `python -m pytest -q && python -m scripts.tools.check` — expected: all pass, no check errors.
- [ ] **Step 5: Commit** — "Add the source register and its schema".

### Task 2: Writing sources and passages through the model

**Files:**
- Modify: `scripts/lib/model/sources.py`, `scripts/lib/model/__init__.py`
- Test: `tests/test_model_sources.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `PASSAGE_SEPARATOR = '\n\n---\n\n'`
  - `write_source(source: Source) -> None` — inserts or replaces the row by id, keeps the file sorted by id, writes `fetched` as `YYYY-MM-DDTHH:MM:SSZ`.
  - `read_excerpt(source_id: str) -> str` — `''` when the file doesn't exist.
  - `passages(source_id: str) -> list[str]` — the excerpt split on `PASSAGE_SEPARATOR`.
  - `add_passage(source_id: str, passage: str) -> bool` — appends the passage (stripped) unless an existing passage already contains it after whitespace collapsing; returns whether it was added. Files end with one newline.

- [ ] **Step 1: Write the failing tests**:

```python
def test_write_source_keeps_rows_sorted(tmp_repo): ...  # write ids 'bbbbbbbbbbbb' then 'aaaaaaaaaaaa'; file rows in id order; rewriting 'aaaaaaaaaaaa' with a new title replaces, not duplicates

def test_add_passage_is_idempotent(tmp_repo):
    assert add_passage('aaaaaaaaaaaa', 'He works for Zest.') is True
    assert add_passage('aaaaaaaaaaaa', 'He  works for\nZest.') is False
    assert add_passage('aaaaaaaaaaaa', 'Nowadays he works for kitconcept.') is True
    assert passages('aaaaaaaaaaaa') == ['He works for Zest.', 'Nowadays he works for kitconcept.']
    assert read_excerpt('aaaaaaaaaaaa').endswith('kitconcept.\n')
```

- [ ] **Step 2: Run** `python -m pytest tests/test_model_sources.py -q` — FAIL.
- [ ] **Step 3: Implement** with `csv.DictWriter` (field order from the schema), `lineterminator='\n'`.
- [ ] **Step 4: Run** `python -m pytest tests/test_model_sources.py -q` — PASS.
- [ ] **Step 5: Commit** — "Write sources and excerpt passages through the model".

### Task 3: Finding a quote and cutting its passage

**Files:**
- Create: `scripts/lib/capture/__init__.py` (empty for now), `scripts/lib/capture/passages.py`, `tests/test_capture_passages.py`

**Interfaces:**
- Produces:
  - `normalize_text(text: str) -> str` — NFKC; `‘’‚‛′` → `'`; `“”„″` → `"`; `–—‐‑−` → `-`; `…` → `...`; every whitespace run (incl. NBSP) → one space; stripped. Case is kept.
  - `find_quote(text: str, quote: str) -> tuple[int, int] | None` — the span **in the original text** of the quote, compared after `normalize_text`. A quote containing `...` or `…` matches when its parts occur in order within one paragraph; the span runs from the first part's start to the last part's end.
  - `cut_passage(text: str, span: tuple[int, int], limit: int = 1000) -> str` — the paragraph (blocks split on blank lines) that contains the span; if longer than `limit`, a window of `(limit - (end - start)) // 2` characters on each side of the span, widened to whole words, with `…` where text was cut. Original spelling kept.

Build the normalized text with an index map back to the original so spans translate exactly.

- [ ] **Step 1: Write the failing tests**:

```python
TEXT = 'Intro.\n\nMaurits has been a Plone programmer for Zest Software since 2005.\nMore.\n\nOutro.'

def test_find_quote_normalizes():
    span = find_quote(TEXT, 'has been a Plone programmer for Zest Software since 2005')
    assert TEXT[span[0]:span[1]] == 'has been a Plone programmer for Zest Software since 2005'
    assert find_quote('He said “Nowadays” – ok', '"Nowadays" - ok') is not None
    assert find_quote(TEXT, 'Zest Software since 2006') is None

def test_find_quote_with_ellipsis():
    span = find_quote(TEXT, 'Maurits has been … since 2005')
    assert TEXT[span[0]:span[1]].startswith('Maurits') and TEXT[span[0]:span[1]].endswith('2005')
    assert find_quote(TEXT, 'Intro … Outro') is None  # parts in different paragraphs

def test_cut_passage_returns_the_paragraph():
    span = find_quote(TEXT, 'since 2005')
    assert cut_passage(TEXT, span) == 'Maurits has been a Plone programmer for Zest Software since 2005.\nMore.'

def test_cut_passage_windows_a_long_paragraph():
    long = ' '.join(['word'] * 600) + ' QUOTE HERE ' + ' '.join(['word'] * 600)
    passage = cut_passage(long, find_quote(long, 'QUOTE HERE'), limit=200)
    assert 'QUOTE HERE' in passage and len(passage) <= 210
    assert passage.startswith('…') and passage.endswith('…')
```

- [ ] **Step 2: Run** `python -m pytest tests/test_capture_passages.py -q` — FAIL.
- [ ] **Step 3: Implement** `scripts/lib/capture/passages.py`.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — "Find quotes and cut passages for excerpts".

### Task 4: Polite, cached fetching and the Wayback helpers

**Files:**
- Create: `scripts/lib/capture/fetch.py`, `tests/test_capture_fetch.py`

**Interfaces:**
- Consumes: `split_archive_url`, `normalize_url` (Task 1).
- Produces:
  - `CACHE_DIR = os.path.join('.cache', 'sources')`, `USER_AGENT` (value in Global Constraints), `PACE = {'web.archive.org': 4.0, 'archive.org': 4.0}`, `DEFAULT_PACE = 1.0`, `MAX_RETRIES = 5`
  - `@dataclass(frozen=True) class Raw: url: str; status: int; content_type: str; body: bytes; fetched: datetime.datetime`
  - `class FetchError(Exception)`
  - `raw_capture_url(archive_url: str) -> str` — the `id_` form.
  - `class Fetcher: __init__(self, cache: str = CACHE_DIR, session=None, sleep=None, clock=None, refresh: bool = False)`; `get(self, url: str) -> Raw` — from the cache when present (files `<cache>/<sha1 of url>.body` and `.json` with url, status, content_type, fetched), else fetches, waits out the pace per host since the last request to that host, retries 429/5xx and connection errors with `sleep(2 ** attempt)` up to `MAX_RETRIES`, caches responses with status 200, 404 and 410, raises `FetchError` otherwise. `sleep` and `clock` (returns a monotonic float) are injectable for tests; the `fetched` timestamp comes from `datetime.now(timezone.utc)` unless the test patches it.
  - `nearest_capture(fetcher: Fetcher, url: str, timestamp: str | None = None) -> str | None` — asks `https://archive.org/wayback/available?url=<url>&timestamp=<ts>` (one request, through the fetcher, so it is paced and cached) and returns the readable archive URL (`archive_url_of`) of the closest available capture, or `None`.

- [ ] **Step 1: Write the failing tests** with a fake session (records requests, returns queued responses), fake `sleep` and `clock`:
  - `test_raw_capture_url_uses_id_flag`: `raw_capture_url('https://web.archive.org/web/20100125023558/http://limi.net:80/about') == 'https://web.archive.org/web/20100125023558id_/http://limi.net:80/about'`; same result for an `if_` input.
  - `test_get_uses_the_cache_and_never_refetches`: two `get` calls, one request; with `refresh=True` a new Fetcher on the same cache fetches again.
  - `test_wayback_requests_are_paced`: two `get`s to different Wayback URLs with the clock frozen → `sleep` called with `4.0`; to two other hosts → no sleep.
  - `test_retries_then_fails`: five 503 responses → `FetchError`; sleeps `2, 4, 8, 16`.
  - `test_404_is_cached_and_returned`: status 404 returned as `Raw`, second call no request.
  - `test_sends_the_user_agent`.
  - `test_nearest_capture`: fake availability JSON `{"archived_snapshots": {"closest": {"available": true, "timestamp": "20091001000000", "url": "http://web.archive.org/web/20091001000000/http://ploneconf2009.org/x"}}}` → `'https://web.archive.org/web/20091001000000/http://ploneconf2009.org/x'`; `{"archived_snapshots": {}}` → `None`.
- [ ] **Step 2: Run** `python -m pytest tests/test_capture_fetch.py -q` — FAIL.
- [ ] **Step 3: Implement** `scripts/lib/capture/fetch.py`.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — "Fetch sources politely, once, through a local cache".

### Task 5: Extraction of HTML and PDF

**Files:**
- Create: `scripts/lib/capture/extract.py`, `tests/test_capture_extract.py`, fixtures in `tests/fixtures/capture/` (small hand-written HTML files, one Latin-1, one with header/menu/footer; a tiny PDF is not needed — fake `pdftotext`)
- Modify: `requirements.txt` (add `trafilatura>=2.0`)

**Interfaces:**
- Consumes: `Raw` (Task 4).
- Produces:
  - `@dataclass(frozen=True) class Extracted: text: str; full_text: str; title: str | None; date: datetime.date | None`
    `text` is the main content (for quotes and passages); `full_text` is the whole readable text of the page, used only to find a quote that main-content extraction cut (a sidebar bio). Neither is ever written whole to `curated/`.
  - `decode(raw: Raw) -> str` — charset from the `Content-Type` header, else from `<meta charset>`/`http-equiv`, else UTF-8, falling back to `cp1252` when UTF-8 fails.
  - `extract_html(raw: Raw) -> Extracted` — `trafilatura.extract(html, output_format='markdown', include_comments=False, include_tables=True, favor_recall=True, with_metadata=False)` for `text`; `trafilatura.html2txt(html)` for `full_text`; title and date from `trafilatura.extract_metadata`.
  - `extract_pdf(raw: Raw, run=subprocess.run) -> Extracted` — `pdftotext -enc UTF-8 - -` with the body on stdin; `text` and `full_text` the same; `ExtractError` with a hint when `pdftotext` is missing.
  - `class ExtractError(Exception)`
  - `extract(raw: Raw, run=subprocess.run) -> Extracted` — dispatch by content type (`application/pdf` or a URL ending `.pdf`) else HTML. Task 6 adds site adapters in front of this dispatch.

- [ ] **Step 1: Write the failing tests**:
  - `test_extract_html_drops_navigation`: fixture with `<header>`, `<nav>` menu, `<footer>` "Privacy policy", main `<article>` "He works for Zest Software." → `'Zest Software' in text`, `'Privacy policy' not in text`.
  - `test_extract_html_keeps_sidebar_in_full_text`: a bio only in an `<aside>` → found in `full_text`.
  - `test_extract_html_decodes_declared_charset`: Latin-1 bytes with `<meta charset="iso-8859-1">` containing `Jyväskylä` → `'Jyväskylä' in text`.
  - `test_extract_pdf_runs_pdftotext`: fake `run` returning stdout `b'Alexander Limi, Plone Solutions'` → text equals it; fake raising `FileNotFoundError` → `ExtractError` mentioning `pdftotext`.
- [ ] **Step 2: Run** `pip install -r requirements.txt && python -m pytest tests/test_capture_extract.py -q` — FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** — PASS; `make check` — PASS (`pip check` may fail for system packages, as known; run `python -m scripts.tools.check` and pytest directly).
- [ ] **Step 5: Commit** — "Extract readable text from HTML and PDF sources".

### Task 6: Site adapters: Volto, GitHub profiles, commits, videos

**Files:**
- Modify: `scripts/lib/capture/extract.py`
- Test: `tests/test_capture_extract.py`

**Interfaces:**
- Consumes: `Fetcher` (Task 4), `github_get`, `git_history.CACHE_DIR`, `plone_changelogs.ORGANISATION` (clones live at `<CACHE_DIR>/plone/<repo>.git`).
- Produces (all return `Extracted`; the orchestration in Task 7 decides which applies via `adapter_for(url: str) -> str`, one of `'volto' | 'github-profile' | 'commit' | 'video' | 'generic'`):
  - `VOLTO_HOSTS = {'plone.org', '2022.ploneconf.org', '2023.ploneconf.org', '2024.ploneconf.org', '2025.ploneconf.org'}`; `extract_volto(fetcher, url) -> Extracted` — fetches `<scheme>://<host>/++api++<path>` (live pages only, never for Wayback URLs) and renders `title`, `description` and the text of the `blocks` (Slate `value` text nodes; `text` blocks' `blocks[].text`) as paragraphs. Falls back to `extract_html` of the page itself when the `++api++` request isn't 200 or its JSON has no text (some ploneconf.org years are static Volto exports).
  - `extract_github_profile(login, session) -> Extracted` — `GET https://api.github.com/users/<login>`; text lines `Name: …`, `Company: …`, `Bio: …`, `Location: …`, `Blog: …` for the non-empty fields; `date` = today (UTC).
  - `extract_commit(owner, repo, sha, run=subprocess.run, session=None) -> Extracted` — from the bare clone `git --git-dir <clone> show -s --format=%an <%ae>%n%aI%n%n%B <sha>` when the clone exists, else `GET https://api.github.com/repos/<owner>/<repo>/commits/<sha>`; text `Author: Name <email>`, `Date: <ISO>`, blank line, message; `date` = author date.
  - `extract_video(url, workdir, run=subprocess.run) -> Extracted` — `yt-dlp --skip-download --write-auto-sub --write-sub --sub-langs "en.*,de.*,es.*,pt.*,it.*,nl.*,fr.*" --sub-format vtt -o <workdir>/%(id)s <url>`, then parse the first `.vtt`: drop headers and duplicate rolling lines, one line per cue as `[mm:ss] text` (hours as `[h:mm:ss]`); `title` from `yt-dlp --print title`; `ExtractError` when no captions exist. The workdir is under `CACHE_DIR`, so captions are cached and never committed whole.
  - sched.org and other hosts go through the generic adapter; an own adapter is added only if the migration capture in plan 2 shows that main-content extraction misses their text.
  - `adapter_for` rules: Wayback URLs → `'generic'` (the raw capture); host in `VOLTO_HOSTS` → `'volto'`; `github.com/<login>` with one path segment → `'github-profile'`; `github.com/<owner>/<repo>/commit/<sha>` → `'commit'`; `youtube.com`, `youtu.be`, `vimeo.com` → `'video'`; else `'generic'`.

- [ ] **Step 1: Write the failing tests** (fake fetcher/session/run): `test_adapter_for` (one assertion per rule above, incl. `https://github.com/search?q=…` → `'generic'` and `https://github.com/plone` → `'github-profile'`), `test_extract_volto_renders_blocks`, `test_extract_github_profile_lines` (`Company: @kitconcept` present, empty fields absent), `test_extract_commit_prefers_the_clone` (no API call when the clone dir exists), `test_extract_commit_falls_back_to_api`, `test_extract_video_parses_vtt` (a VTT with rolling duplicates → `['[04:36] currently working at Onna', …]` without duplicates), `test_extract_video_without_captions_raises`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — "Add capture adapters for Volto, GitHub, commits and videos".

### Task 7: capture(): one source, its row and its passages

**Files:**
- Modify: `scripts/lib/capture/__init__.py`
- Create: `tests/test_capture.py`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces:
  - `@dataclass(frozen=True) class CaptureResult: source_id: str; created: bool; added: tuple[str, ...]; missing: tuple[str, ...]; unreachable: bool`
  - `capture(url: str, quotes: Sequence[str] = (), kind: str | None = None, title: str | None = None, date: datetime.date | None = None, refresh: bool = False, fetcher: Fetcher | None = None, session=None, run=subprocess.run) -> CaptureResult`

Behaviour, in order:
1. A Wayback URL (`split_archive_url`) gives `original` and `timestamp`; `archive_url` is stored in the readable form, fetched in the `id_` form. Otherwise `original = url`, no archive.
2. `sid = source_id(original, timestamp)`. If the row exists, `refresh` is false and every quote is already inside a stored passage (by `find_quote` on the excerpt), return without fetching.
3. Fetch and extract with the adapter (`adapter_for`). A 404/410 for a live URL: try `nearest_capture` once and capture that instead (the row then has the archive URL); with nothing found, write the row with `notes = 'could not be fetched on <YYYY-MM-DD>'`, an excerpt file holding only that sentence, and return `unreachable=True` with all quotes `missing`.
4. For each quote: `find_quote` in `text`, else in `full_text`; found → `cut_passage` from the text it was found in → `add_passage`; not found → `missing`.
5. Row: `kind` = given, else by adapter (`github-profile`→`profile`, `commit`→`commit`, `video`→`video`, PDF→`pdf`, else `page`); `title` = given, else extracted, else the URL; `date` = given, else extracted, else the capture date of the timestamp, else the fetch date; `fetched` = `Raw.fetched`. An existing row keeps its `kind`, `title`, `date` and `notes`; only `fetched` changes on `refresh`.
6. Nothing whole is written: only `write_source` and `add_passage`.

- [ ] **Step 1: Write the failing tests** (fake Fetcher returning fixture HTML; `tmp_repo`):
  - `test_capture_creates_row_and_passage`: one quote → row with kind `page`, excerpt equals the paragraph, `created=True`, `missing=()`.
  - `test_capture_known_source_without_new_quotes_does_not_fetch`.
  - `test_second_quote_in_same_paragraph`: second capture with another quote of the same paragraph → `added=()`, one passage.
  - `test_capture_after_interruption_uses_cache`: raw in the cache, no row → `capture` writes the row with zero network requests (fake session asserts it is never called).
  - `test_missing_quote_is_reported_not_stored`.
  - `test_quote_only_in_sidebar_is_cut_from_full_text`.
  - `test_wayback_url_is_stored_readable_and_fetched_raw`: input `…/web/20100125023558if_/http://limi.net:80/about` → `archive_url == 'https://web.archive.org/web/20100125023558/http://limi.net:80/about'`, request URL contains `20100125023558id_/`, `date == 2010-01-25` when the page has no date.
  - `test_dead_live_url_falls_back_to_nearest_capture` and `test_dead_url_without_capture_is_unreachable` (row notes `could not be fetched on …`, `unreachable=True`).
- [ ] **Step 2: Run** `python -m pytest tests/test_capture.py -q` — FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** `python -m pytest -q` — PASS.
- [ ] **Step 5: Commit** — "Capture a source once and store the passages around its quotes".

### Task 8: Checks for the source register

**Files:**
- Modify: `scripts/lib/model/checks.py` (`checks_for`)
- Test: `tests/test_checks.py`

**Interfaces:**
- Consumes: `source_id`, `split_archive_url`, `excerpt_path` (Task 1).
- Produces checks registered for the `sources` resource:
  - `SourceIdMatchesUrl` (error type `source-id`): `id == source_id(url, timestamp of archive_url)`.
  - `SourceExcerptFiles` (error type `source-excerpt`): every row has its excerpt file with at least one passage; in `validate_end`, every `*.md` in the excerpts folder (`Path(package.basepath) / 'sources' / 'excerpts'`) has a row. `checks_for` passes the set of file stems found on disk.
  - `Sorted(fields=['id'])`.

- [ ] **Step 1: Write the failing tests** in `tests/test_checks.py`, following the existing pattern there (validate a tmp package): a row whose id doesn't match its URL → `source-id`; a row without excerpt file → `source-excerpt`; an orphan `.md` → `source-excerpt`; a correct row → no errors.
- [ ] **Step 2: Run** `python -m pytest tests/test_checks.py -q` — FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** `python -m pytest -q && python -m scripts.tools.check` — PASS.
- [ ] **Step 5: Commit** — "Check that every source matches its URL and has its excerpt".

### Task 9: Command line, documentation, first real sources

**Files:**
- Create: `scripts/tools/capture.py`, `docs/how-to/capture-a-source.md`, `curated/sources/README.md`
- Modify: `docs/how-to/index.md`, `curated/README.md` (row for `sources/`), `AGENTS.md` (Layout: `curated/sources/`; Commands: none), `docs/reference/curated-files.md` (regenerated if `ONE_ROW_IS` changed)
- Test: `tests/test_tool_capture.py`

**Interfaces:**
- Consumes: `capture()` (Task 7).
- Produces: `python -m scripts.tools.capture URL [--quote TEXT]... [--kind KIND] [--title TEXT] [--date YYYY-MM-DD] [--refresh]`. Prints `<source id>  <url>`, then one line per added passage (`+ <first 80 chars>`) and per missing quote (`! not found: <quote>`), or `! unreachable`. Exit status 1 when a quote is missing or the source is unreachable. Module docstring first line: "Capture a source once: its row in curated/sources/sources.csv and the passages around the given quotes."

- [ ] **Step 1: Write the failing tests**: `main([...])` with `capture` patched → output lines and exit codes for: all found (0), one missing (1), unreachable (1). `tests/test_layout.py` already runs `--help` for every tool.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** the tool; write `docs/how-to/capture-a-source.md` (Plone doc style, MyST): when to capture, the command with a real example, that only passages are stored and why (quotation right), the local cache and the politeness limits, what to do with a missing quote and an unreachable page, how to refresh a changing page (profile). `curated/sources/README.md`: what the folder holds, "edited through the capture tool, not by hand; never paste whole pages". No statistics in prose.
- [ ] **Step 4: Run** `python -m pytest -q && python -m scripts.tools.check && make docs` — PASS (docs warnings are errors).
- [ ] **Step 5: Smoke test against the real web** (the only networked step; once): `GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.capture https://2023.ploneconf.org/speakers/fred-van-dijk --quote "Nowadays he works for both Zest and Kitconcept"` and `python -m scripts.tools.capture "http://web.archive.org/web/20100125023558/http://limi.net:80/about" --quote "In 2006, he moved from Norway to San Francisco"`. Expected: two rows, two excerpt files each holding one paragraph; rerunning both makes no request. Keep these two sources as the first real rows; `python -m scripts.tools.check` — PASS.
- [ ] **Step 6: Commit** — "Add the capture command and its documentation".

### Task 10: Pull request

- [ ] **Step 1:** Copy the design and this plan unchanged to `archive/specs-and-plans/2026-10-22-sources-and-events-design.md` and `archive/specs-and-plans/2026-10-22-sources-and-capture-plan.md`; add them to `archive/README.md` as the archive's README requires (`tests/test_docs_and_archive.py::test_archive_readme_lists_every_file`).
- [ ] **Step 2:** `python -m pytest -q && python -m scripts.tools.check && make docs` — PASS.
- [ ] **Step 3:** Push `sources-capture` and open the PR: what the register and tool are, that nothing cites sources yet (plan 2), the legal reason for passages only, the politeness limits; end with `Assisted-by:` lines naming every model used, and `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
