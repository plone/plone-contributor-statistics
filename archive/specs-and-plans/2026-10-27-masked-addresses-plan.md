# Masked Mail Addresses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No readable mail address of a person in the current tree; tools and collectors mask addresses on the way in; matching and organisation evidence work as before.

**Architecture:** One module, `scripts/lib/addresses.py`, holds the masking rule (hash, bare form, the form with domain for excerpts and snippets, free-text replacement, the allowlist). Matching hashes the lookup in `Registry.person_for`; capture masks the read text and the quotes; the changelog collector masks what it writes. A one-off migration rewrites the tracked files, then a repo-wide test keeps readable addresses out.

**Tech Stack:** Python 3, pytest, frictionless checks, pandas (changelog collector).

**Spec:** `2026-10-27-masked-addresses-design.md` (next to this plan; read it first).

**Worktree:** `/home/jensens/ws/cdev/plone-contributor-statistics/.claude/worktrees/masked-addresses`, branch `masked-addresses` from `origin/main` (a1541e6). The clone cache is at `/home/jensens/ws/cdev/plone-contributor-statistics/.cache` (pass `--cache` where a tool needs it). Python: `~/.venvs/plone-contributor-statistics/bin/python`.

## Global Constraints

- Masked form: `h-` + the first 16 hexadecimal characters of SHA-256 over the address stripped of whitespace and `<>`, lower-cased, UTF-8.
- Bare form, the default everywhere: `h-<16hex>`, whatever the domain. Used for the `value` of `kind=email` identities, `notes` and all other free text, collected files, docs, the archive.
- Form with domain, **only** in `curated/sources/excerpts/*.md` and in the `snippet` cells of `identities.csv` and `citations.csv` (which quote the excerpts verbatim): company domain (`is_company_domain`) → `h-<16hex>@<domain lower-cased>`; general mail service (`PERSONAL_DOMAINS`) or machine name/placeholder (`is_local_name`) → `h-<16hex>`.
- In both forms: `SVN_DOMAIN` and GitHub `NOREPLY` addresses unchanged; an allowlisted (`NOT_PERSONAL`) address unchanged; an already masked value stays masked (in the bare form, `h-x@domain` becomes `h-x`).
- CVS and Subversion are out of scope: no change to their addresses, the `svn` identities or `NameMapper.svn`.
- No real address in any test, Subversion forms included. Test addresses are invented and use reserved domains: `example.com` placeholders, `.test` company domains (`jane@acme.test`), `.test` names matching a wildcard of `PERSONAL_DOMAINS` for general services (`jane@gmx.test`, `jane@yahoo.test`), invented logins for `@localhost`/UUID forms (`jdoe@localhost`).
- No change to any attribution, credit or count; `derived/` and `reports/` stay identical.
- No git history rewrite.
- Offline pytest tests for code; the GitHub API replaced by fakes.
- Commit messages end with `Assisted-by: <model name>`, one line per model that contributed (the implementing subagent's model, then the orchestrator's, Claude Opus 5.5), no email, no other trailers such as `Co-Authored-By` (`AGENTS.md`).
- Before the pull request: `python -m scripts.tools.attribution_changes` reports no person and year that counts for another organisation (`AGENTS.md`).
- Docs are Sphinx/MyST; `make docs` must pass with warnings as errors. No numbers or rankings in prose.

## Review Focus

1. **Masking twice or in a different place gives a different string** → `find_quote` fails, a snippet loses its excerpt, an affiliation loses its citation. Expected: `mask_text(mask_text(t)) == mask_text(t)` and `mask_address` of an already masked value returns it unchanged. Pinned in Task 1.
2. **Mixed case and angle brackets** (`<Jane.Doe@Acme.TEST>`, `JANE@acme.test`) → expected the same hash as `jane.doe@acme.test`. Pinned in Task 1 and in Task 2's lookup test.
3. **Things that look like addresses but are not a person's**: `react@18.2.0`, `@plone/volto`, `gocept@Saltlabs`, `git@github.com:plone/x.git`, URLs with `user@host`. Expected: versions, scoped packages and dotless hosts untouched; project and service addresses listed in `NOT_PERSONAL` untouched. Pinned in Task 1; the migration dry run (Task 6) lists every distinct match for review.
4. **A `--quote` or snippet typed with the raw address** against a masked excerpt → expected to be found, because the quote is masked the same way first. Pinned in Task 3.
5. **An identity value with a domain** (`h-…@acme.test`) or a raw address entered by hand into `identities.csv` → expected `make check` to fail with a clear message. Pinned in Task 5.

---

### Task 1: The masking module

**Files:**
- Create: `scripts/lib/addresses.py`
- Test: `tests/test_addresses.py`

**Interfaces:**
- Consumes: `is_company_domain`, `is_local_name`, `NOREPLY` from `scripts/lib/commit_authors.py`; `SVN_DOMAIN` from `scripts/lib/changelogs.py`. Import these inside the functions or at module level only from those two modules; `addresses.py` must not import `scripts.lib.model` (cycle: model → registers → addresses).
- Produces:
  - `PREFIX = 'h-'`
  - `MASKED = re.compile(r'h-[0-9a-f]{16}')` (match a whole local part)
  - `ADDRESS: re.Pattern` finds addresses in free text: a local part `[\w.+\-]+` not preceded by `[\w.+\-/@]`, `@`, a domain of dot-separated labels ending in a label of at least two letters; also the dotless `SVN_DOMAIN` forms are *not* matched (they stay unchanged anyway, so the pattern may skip them).
  - `NOT_PERSONAL: dict[str, str]` address → reason; addresses that are not a person's and stay readable. Starts with `'git@github.com': 'the SSH address of GitHub repositories'` and `'noreply@github.com': 'GitHub's sender address'`; Task 6's dry run adds what it finds, each with its reason.
  - `address_hash(address: str) -> str`
  - `is_masked(value: str) -> bool` true for `h-<16hex>` and `h-<16hex>@domain`
  - `mask_address(address: str, keep_domain: bool = False) -> str`; accepts raw, bare-masked and masked-with-domain values. `keep_domain=True` only for excerpts and snippets.
  - `mask_text(text: str, keep_domain: bool = False) -> str` every `ADDRESS` match replaced by `mask_address(match, keep_domain)`

- [ ] **Step 1: Write the failing tests** in `tests/test_addresses.py`:

```python
import hashlib
from scripts.lib.addresses import address_hash, is_masked, mask_address, mask_text

def h(address):
    return 'h-' + hashlib.sha256(address.encode()).hexdigest()[:16]

def test_hash_normalises_case_space_and_brackets():
    assert address_hash(' <Jane.Doe@Acme.TEST> ') == h('jane.doe@acme.test')

def test_company_address_keeps_its_domain_only_when_asked():
    assert mask_address('Jane@Acme.test', keep_domain=True) == h('jane@acme.test') + '@acme.test'
    assert mask_address('Jane@Acme.test') == h('jane@acme.test')

def test_general_service_and_machine_names_are_masked_completely():
    for address in ('jane@gmx.test', 'jane@' + 'janes-imac.local', 'jane@example.com'):
        assert mask_address(address, keep_domain=True) == h(address)

def test_subversion_noreply_and_not_personal_stay():
    for address in ('jdoe@localhost', 'jdoe@3b4cdb85-528f-c531-b63d-5919d5b1aa08',
                    '123+jdoe@users.noreply.github.com', 'git@github.com'):
        assert mask_address(address) == address
        assert mask_address(address, keep_domain=True) == address

def test_masking_is_idempotent():
    with_domain = mask_address('jane@acme.test', keep_domain=True)
    assert mask_address(with_domain, keep_domain=True) == with_domain
    text = 'Author: Jane <jane@acme.test>\nCc: bob@gmx.test'
    for keep in (False, True):
        assert mask_text(mask_text(text, keep), keep) == mask_text(text, keep)

def test_bare_form_drops_the_domain_of_a_masked_value():
    bare = h('jane@acme.test')
    assert mask_address(bare + '@acme.test') == bare
    assert mask_address(bare) == bare

def test_mask_text_replaces_only_addresses():
    text = ('Author: Jane <jane@acme.test>, see https://acme.test/@jane and @jarn.com; '
            'react@18.2.0, @plone/volto, gocept@Saltlabs, git@github.com:plone/x.git')
    assert mask_text(text, keep_domain=True) == text.replace('jane@acme.test', h('jane@acme.test') + '@acme.test')
    assert mask_text(text) == text.replace('jane@acme.test', h('jane@acme.test'))

def test_is_masked():
    assert is_masked(h('a@b.test')) and is_masked(h('a@b.test') + '@b.test')
    assert not is_masked('jane@acme.test') and not is_masked('h-xyz@acme.test')
```

- [ ] **Step 2: Run** `pytest tests/test_addresses.py -v`. Expected: FAIL, `ModuleNotFoundError: scripts.lib.addresses`.
- [ ] **Step 3: Implement `scripts/lib/addresses.py`** with the interface above and a module docstring that points to `docs/explanation/attribution.md`. `mask_address` checks in this order: already masked (bare form: drop a domain), `NOT_PERSONAL`, `NOREPLY`, `SVN_DOMAIN` on the domain, then with `keep_domain` company vs. complete masking, without it the bare hash. A value without `@` that is not masked is returned unchanged.
- [ ] **Step 4: Run** `pytest tests/test_addresses.py -v` and `python -c "import scripts.lib.addresses; import scripts.lib.model"`. Expected: PASS, no import error.
- [ ] **Step 5: Commit** `git commit -m "Add the masking of mail addresses"` with the footer.

### Task 2: Matching by hash

**Files:**
- Modify: `scripts/lib/model/registers.py:93-94` (index), `:122-128` (`person_for`)
- Modify: `scripts/tools/person.py:16-35` (`find`)
- Test: `tests/test_model_registers.py`, `tests/test_tool_person.py`, `tests/test_commit_authors.py`

**Interfaces:**
- Consumes: `mask_address` from Task 1. In `registers.py` import the module, `from scripts.lib import addresses`, and call `addresses.mask_address(...)` at call time (import cycle).
- Produces: `Registry.person_for(email=...)` accepts a raw, a bare-masked or a masked-with-domain address; `_by_email` is keyed by `mask_address(identity.value).lower()`.

- [ ] **Step 1: Write the failing tests.** In `tests/test_model_registers.py`: `test_person_for_email_matches_by_hash` builds `registry_of([...person 'jane-doe'...], identities=[('jane-doe', 'email', mask_address('jane@acme.test'))])` (use the existing `registry_of` signature from `tests/conftest.py`) and asserts `person_for(email='Jane@ACME.test')`, `person_for(email=mask_address('jane@acme.test', keep_domain=True))` and `person_for(email=mask_address('jane@acme.test'))` all return `jane-doe`; and that an identity `('j-doe', 'email', 'jdoe@localhost')` is found by `person_for(email='JDoe@localhost')`. In `tests/test_tool_person.py`: `find(registry, 'Jane@acme.test')` finds the person whose identity is the bare hash.
- [ ] **Step 2: Run** those tests. Expected: FAIL (lookup returns None).
- [ ] **Step 3: Implement**: index with `addresses.mask_address(identity.value).lower()`, look up with `addresses.mask_address(email).lower()` (the unchanged Subversion and noreply forms are compared ignoring case, as today); in `person.py:find`, compare `mask_address(identity.value) == mask_address(query)` when the query contains `@` or is masked.
- [ ] **Step 4: Replace real addresses in the touched test files** (`test_model_registers.py`, `test_tool_person.py`, `test_commit_authors.py`, `test_name_mapper_registry.py`, `test_collect_with_registry.py`, `test_git_history.py`, `test_changelogs_counting.py`) by invented ones per the Global Constraints, Subversion logins included (`andyd_`, `bsaller`, `Whit`, `paul`, `zopepaul` → invented). Identities in fixtures for non-SVN addresses use `mask_address(...)`.
- [ ] **Step 5: Run** `pytest -q`. Expected: PASS.
- [ ] **Step 6: Commit** `"Match commit addresses by their hash"`.

### Task 3: Capture writes masked excerpts

**Files:**
- Modify: `scripts/lib/capture/__init__.py` (`capture` about l.252 and after `read` is obtained about l.278; `capture_commit` l.396-414)
- Test: `tests/test_capture.py`, `tests/test_capture_extract.py`, `tests/test_tool_capture.py`

**Interfaces:**
- Consumes: `mask_text`, `mask_address` from Task 1.
- Produces: every excerpt written by `capture` is masked with `keep_domain=True`; `capture(..., quotes, names)` masks quotes and names the same way before searching; `capture_commit(url, email, ...)` returns the masked `Author:` line (with domain).

- [ ] **Step 1: Write the failing tests.** Change `test_capture_commit_cites_the_author_line` (`tests/test_capture.py:329`) to expect `f'Author: Jane <{mask_address("jane@acme.test", keep_domain=True)}>'` and the excerpt file to contain no `jane@acme.test`. Add `test_capture_masks_page_addresses`: a fake page with `Email: jane@acme.test` captured with `--quote 'Email: jane@acme.test'` stores `Email: h-…@acme.test` and reports the quote as found. Add `test_capture_masks_a_general_service_address_completely` with `jane@gmx.test`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** (every call with `keep_domain=True`): at the top of `capture`, mask `quotes` and `names` with `mask_text`; right after `read` is obtained, `read = dataclasses.replace(read, text=mask_text(read.text, True), full_text=mask_text(read.full_text, True))` (`_Read` is a frozen dataclass, `scripts/lib/capture/__init__.py:103`); in `capture_commit`, pass `names=(mask_address(email, True),)` and compare the `Author:` line with it. Replace any real address in the three test files.
- [ ] **Step 4: Run** `pytest -q`. Expected: PASS.
- [ ] **Step 5: Commit** `"Mask addresses when a source is captured"`.

### Task 4: Tools and the changelog collector write masked text

**Files:**
- Modify: `scripts/collect/plone_changelogs.py:150-160` (`year_table`)
- Modify: `scripts/tools/unmatched_changelog_names.py:104-140` (`capture_command`, the snippet and the who-note)
- Modify: `scripts/tools/cite_snippets.py:80-88` (`span`: mask the quote before `find_quote`)
- Check, change only if needed: `scripts/tools/address_proposals.py` (`propose`, `cite`), `scripts/tools/github_evidence.py` (`propose`): the snippet comes from `capture_commit` (masked by Task 3); make sure no raw address reaches a written cell or note.
- Test: `tests/test_changelogs_collect.py`, `tests/test_unmatched_changelog_names.py`, `tests/test_tool_cite_snippets.py`, `tests/test_address_proposals.py`, `tests/test_github_evidence.py`

**Interfaces:**
- Consumes: `mask_text`, `mask_address` from Task 1; `capture_commit` from Task 3.
- Produces: collected changelog `username` and `changelog_names` cells in the bare form; snippets (which quote excerpts) with `keep_domain=True`; notes and every other written cell in the bare form. Printing raw addresses to the terminal stays allowed.

- [ ] **Step 1: Write the failing tests.** `test_year_table_masks_unmatched_addresses`: `year_table({'jane@acme.test': stats})` (build `stats` as `count` does) gives `username == mask_address('jane@acme.test')` (bare) and bare `changelog_names`. In `test_unmatched_changelog_names.py`, the proposed snippet is `Author: Jane Doe <h-…@acme.test>` (with domain) and the who-note holds the bare hash. In `test_tool_cite_snippets.py`, a note quoting the raw `"Jane <jane@acme.test>"` is filled as a snippet against an excerpt masked with domain (mask the quote with `keep_domain=True` before `find_quote`). In `test_address_proposals.py` and `test_github_evidence.py`, assert no written CSV cell matches `addresses.ADDRESS` unless `is_masked`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** the masking at the listed places.
- [ ] **Step 4: Replace real addresses** in these five test files (about 60, mostly `greenfinity.hu`, `hannosch.eu`, `glicksoftware.com`, `columbia.edu`, `gmail.com`) by invented ones per the Global Constraints, keeping each test's intent (own domain → `jane@janedoe.test` with person `Jane Doe`). A test of the domain logic alone (`registrable_label('foo.com.au')`, `is_company_domain(...)`) passes a bare domain, which is no address and may stay real.
- [ ] **Step 5: Run** `pytest -q`. Expected: PASS.
- [ ] **Step 6: Commit** `"Write masked addresses from the tools and the changelog collector"`.

### Task 5: Checks, the helper and the guard function

**Files:**
- Modify: `scripts/lib/model/checks.py` (new check, registered for `identities` in `checks_for` l.736)
- Modify: `curated/schemas/identities.json` (`value` description: an `email` value is the bare hash, except Subversion-era and noreply addresses)
- Create: `scripts/tools/mask_address.py` (CLI: `python -m scripts.tools.mask_address ADDRESS...` prints, per address, the identity value and the text form)
- Modify: `scripts/lib/addresses.py`: add `MASKED_WITH_DOMAIN = re.compile(r'\bh-[0-9a-f]{16}@')` and `readable_addresses(text: str) -> list[str]` (the `ADDRESS` matches that `mask_address(..., keep_domain=True)` would change, so masked values with a domain don't count; reserved domains `.test`, `.example`, `.invalid`, `.localhost`, `example.com/org/net` count as not readable)
- Regenerate: `docs/reference/curated-files.md` with `python -m scripts.tools.schema_docs`
- Test: `tests/test_checks.py`, `tests/test_addresses.py`, `tests/test_tool_mask_address.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `class EmailIdentityMasked(Check)`, `type = 'email-identity'`, first docstring line "An email identity is the hash of the address, except a Subversion-era or noreply address."; error when `kind == 'email'` and `row['value'] != mask_address(row['value'])` (a raw address or a hash with a domain). `readable_addresses(text) -> list[str]` used by Task 6.

- [ ] **Step 1: Write the failing tests**: `EmailIdentityMasked` accepts `mask_address('jane@acme.test')`, `jdoe@localhost`, `1+jdoe@users.noreply.github.com`; rejects `mask_address('jane@acme.test', keep_domain=True)` (a hash with a domain) and the raw `jane@acme.test` (the check rejects raw values whatever the domain, reserved ones included). `readable_addresses('a jane@acme.test b ' + mask_address('jane@acme.test', keep_domain=True))` returns `[]` (reserved), and for a non-reserved domain built at runtime (`'jane@' + 'acme' + '.com'`) returns that address. The CLI prints both forms for `Jane@acme.test`: the bare one labelled for identities and notes, the one with domain labelled for snippets.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement**, register the check, update the schema description, regenerate `docs/reference/curated-files.md`.
- [ ] **Step 4: Run** `pytest -q`. Expected: PASS except `test_curated_data_passes_the_checks`, which fails on the unmigrated `identities.csv` until Task 6; note that failure in the commit message.
- [ ] **Step 5: Commit** `"Check that email identities are masked"`.

### Task 6: The migration

**Files:**
- Create: `scripts/tools/mask_addresses.py` (one-off; moved to the archive in Task 8)
- Create: `tests/test_mask_addresses.py`
- Create: `tests/test_no_readable_addresses.py`
- Modify (by running the migration): files below `curated/`, `collected/`, `derived/`, `reports/`, `docs/`, `archive/`; `scripts/lib/addresses.py` (`NOT_PERSONAL` additions)

**Interfaces:**
- Consumes: `mask_text`, `mask_address`, `readable_addresses`, `MASKED_WITH_DOMAIN`, `NOT_PERSONAL` (Tasks 1, 5); `load_identities(mappings_dir)`, `load_registry(mappings_dir)`, `write_identities(identities, mappings_dir)`, `write_citations` from `scripts/lib/model/registers.py` (`write_identities` re-sorts); `git_history.read_authors`, `cached_repositories`, `ORGANISATION` (as in `scripts/collect/plone_commit_domains.py:81-86`).
- Produces: `python -m scripts.tools.mask_addresses list|write|verify [--cache DIR]`.
  - `list`: every distinct address found by `ADDRESS` in the tracked text files of the folders above (`git ls-files`, skip binaries), with its count, its class (company/complete/unchanged) and the files; plus spelled-out forms found by `SPELLED = re.compile(r'\b([\w.]+)\s+(?:at|\[at\])\s+([\w-]+)\s+(?:dot|\[dot\])\s+([a-z]{2,})\b', re.I)`.
  - `write`: `mask_text(text, keep_domain=True)` for `curated/sources/excerpts/*.md`; in `identities.csv` and `citations.csv` the `snippet` cells with `keep_domain=True` and every other cell bare, each `kind=email` `value` to `mask_address(value)`, written through `write_identities`/`write_citations` (re-sorted); every other file bare. Spelled-out forms are replaced by `mask_address` of the rebuilt address, in the form of their place. Keeps CSV quoting (mask cell values through the csv module for CSV files, not raw text).
  - `verify --cache DIR`: offline matching equivalence. Builds the old registry with `load_registry(old_dir)` from `git archive <base> curated/mappings | tar -x -C <tmp>` (`<base>` defaults to `origin/main`, option `--base`) and the new one with `load_registry()` from the working tree; for every `(email, name)` of `read_authors(clone)` over all cached clones, asserts `Finder(old).person(email, name) == Finder(new).person(email, name)` (compare person ids); prints the counts and every difference; exit code 1 on any difference.

- [ ] **Step 1: Write the failing tests** in `tests/test_mask_addresses.py` on a `tmp_repo` (conftest): `write` turns an identity `('jane-doe','email','jane@acme.test', snippet 'Author: Jane <jane@acme.test>', notes 'see jane@acme.test')` into value `mask_address(...)`, snippet with `mask_address(..., keep_domain=True)`, notes bare; an excerpt keeps the domain, a citation note and an archive file don't; masks a CSV cell containing a comma and an address without breaking the quoting; masks `natea at jazkarta dot test` in an excerpt to `mask_address('natea@jazkarta.test', keep_domain=True)`; `verify` with a fake clone reader reports no difference for a masked identity and one difference when an identity is dropped.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** `scripts/tools/mask_addresses.py`.
- [ ] **Step 4: Run** `pytest tests/test_mask_addresses.py -v`. Expected: PASS.
- [ ] **Step 5: Dry run** `python -m scripts.tools.mask_addresses list > /tmp/…/addresses.txt` (scratchpad). Review every entry classed *unchanged* and every company-domain entry that is not a person's (project lists, service senders, false positives). Add each non-personal address to `NOT_PERSONAL` with its reason; tighten `ADDRESS` for false positives with a test in `tests/test_addresses.py`. Report the reviewed list in the task summary (counts by class, the `NOT_PERSONAL` additions).
- [ ] **Step 6: Record the baseline**: `pytest tests/test_reproducible_outputs.py -q` passes before the write.
- [ ] **Step 7: Run** `python -m scripts.tools.mask_addresses write`.
- [ ] **Step 8: Verify**: `python -m scripts.tools.mask_addresses verify --cache /home/jensens/ws/cdev/plone-contributor-statistics/.cache` exits 0; `python -m scripts.tools.check` passes; `pytest tests/test_reproducible_outputs.py -q` passes (derived and reports unchanged); `git diff --stat -- derived reports` is empty.
- [ ] **Step 9: Add the guard** `tests/test_no_readable_addresses.py`: over `git ls-files` (text files only), `readable_addresses(text) == []` for every file; and `MASKED_WITH_DOMAIN` matches only in `curated/sources/excerpts/`, in the `snippet` column of `identities.csv` and `citations.csv`, and in `tests/`. The failure message names the file and the addresses. The tests themselves pass the guard, because every test address uses a reserved domain or is built at runtime.
- [ ] **Step 10: Run** `make test`, `make check` and `python -m scripts.tools.attribution_changes`. Expected: PASS, and no person or year that counts for another organisation.
- [ ] **Step 11: Commit** the data and the archive change separately: `"Mask the mail addresses in the curated, collected and generated files"` and `"Mask the mail addresses in the archive"`; then the guard: `"Keep readable mail addresses out of the repository"`. Each message records the counts from Steps 5 and 8.

### Task 7: Documentation and the archive exception

**Files:**
- Modify: `docs/explanation/attribution.md` (l.28-30, 109-116, 157-162: company domains stay readable only in the excerpts and their snippets, as evidence; everywhere else the bare hash; why; link to the GDPR reason in one sentence, no legal advice)
- Modify: `docs/reference/mapping-files.md` (l.9, 12), `docs/reference/data-files.md` (l.45-46, 57, 61, 94-95), `docs/reference/tools.md` (l.11-20, add `mask_address`), `docs/reference/data-sources.md` (l.18)
- Modify: `docs/how-to/link-old-commits-to-a-person.md` (only the examples with real addresses, e.g. l.88; the Subversion procedure itself is unchanged), `docs/how-to/capture-a-source.md` (l.12, 29, 45, 80, 121), `docs/how-to/add-an-affiliation.md` (l.15, 126-152, 186-202), `docs/how-to/find-a-contributor.md` (l.25, 60), `docs/how-to/add-a-person.md` (l.10, 18), `docs/how-to/collect-data-again.md`, `docs/how-to/regenerate-after-a-mapping-change.md`, `docs/explanation/counting-rules.md` (l.11-17), `docs/explanation/known-limitations.md`, `docs/explanation/history-and-coverage.md` (only where it describes stored addresses), `docs/glossary.md` (l.58-59: add "masked address")
- Modify: `AGENTS.md` (l.41-56: masked addresses; the archive exception), `curated/mappings/README.md` (l.9), `archive/README.md` (l.4: "kept unchanged, except that mail addresses were masked on 2026-10-27"), the "archived unchanged" sentences of the migration READMEs in `archive/`
- Test: `make docs`, `pytest tests/test_docs_and_archive.py -q`

- [ ] **Step 1: Update the pages** listed; every example address in the docs is invented with a reserved domain, and the how-to pages say to get the identity value with `python -m scripts.tools.mask_address`.
- [ ] **Step 2: Run** `make docs` and `pytest tests/test_docs_and_archive.py tests/test_no_readable_addresses.py -q`. Expected: PASS, no warnings.
- [ ] **Step 3: Commit** `"Document masked mail addresses"`.

### Task 8: Archive the migration, the spec and the plan

**Files:**
- Move: `scripts/tools/mask_addresses.py` and `tests/test_mask_addresses.py` to `archive/migration-masked-addresses/` (`tests/` subfolder for the test), with `git mv`
- Create: `archive/migration-masked-addresses/README.md` after the template `archive/migration-notes-to-data/README.md` (title with date, links to spec and plan, Files, What ran with commit hashes and the counts from Task 6, Result, Follow-up: privacy notice and opt-out are separate work for the Board)
- Create: `archive/specs-and-plans/2026-10-27-masked-addresses-design.md` and `…-plan.md`, copied unchanged from the scratchpad
- Modify: `archive/README.md` (a row for `migration-masked-addresses/`)
- Test: `pytest tests/test_docs_and_archive.py tests/test_layout.py -q`, `make test`, `make check`, `make docs`

- [ ] **Step 1: Move and write** the files above.
- [ ] **Step 2: Run** `make test`, `make check`, `make docs`. Expected: PASS.
- [ ] **Step 3: Commit** `"Archive the masking migration, its design and its plan"`.
