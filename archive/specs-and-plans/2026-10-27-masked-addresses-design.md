# Masked mail addresses: design

Date: 2026-10-27
Status: draft for review

## Intent

The repository is public and holds several hundred mail addresses of contributors in readable form: commit addresses in `curated/mappings/identities.csv`, `Author: Name <address>` headers and contact lines in the excerpts below `curated/sources/excerpts/`, quotes in `curated/mappings/citations.csv`, unmatched changelog signatures in `collected/changelogs/`, real addresses in tests, and about 800 more in `archive/`.

The statistics don't need the addresses in readable form.
Under the GDPR, data minimisation (Art. 5(1)(c)) asks us not to keep what we don't need, and the addresses are the part of the data that can be harvested and misused (spam, recruiters).
The addresses stay public where they come from: in the commits on GitHub that our sources link.
So we replace every address in the current tree by a masked form that still lets the tools match a commit author to a person, and that keeps the mail domain where the domain is evidence for an organisation.

## Goals

- No readable mail address of a person in the current tree of the repository, `archive/` included.
- New data comes in masked: every tool and collector that writes an address writes the masked form.
- Matching works as before: a commit author's address from a clone or from the GitHub API is masked the same way and then looked up.
- Organisation evidence survives: in the excerpts and the snippets quoting them a company domain stays readable, so `<hash>@jarn.com` still says "company address at Jarn". Everywhere else the bare hash.
- A check fails when a readable address enters the repository again.

## Non-goals

- Rewriting the git history. The addresses stay in our history, as they stay in the history of the Plone repositories they come from. A request to erase one address (GDPR Art. 17) is handled one by one, outside this work.
- Hiding the addresses from someone who already knows them: the masking is a hash anyone can compute from a known address. That is intended, see "Masked form".
- The privacy notice and the opt-out procedure. They are a separate piece of work for the Plone Foundation Board.
- Changing any attribution, credit or count.

## Anti-goals

The work fails, even if it technically works, when:

- Evidence is lost: an identity, citation, snippet or affiliation that held before the migration no longer holds, or a contributor who was matched becomes unmatched. Per the project rule, losing a source is a red-flag bug.
- The derived data or the reports change because of the migration.
- Addresses come back readable through a tool that wasn't converted.

## The masking rule

Input: an address as found, stripped and lowercased.
The hash is always computed from the whole normalised address, so the same address gives the same hash wherever it appears.

| Kind of address | How it is recognised | Masked form |
|---|---|---|
| Company address | `is_company_domain(domain)` in `scripts/lib/commit_authors.py` is true | `<hash>@<domain>` |
| Address at a general mail service | domain matches `PERSONAL_DOMAINS` | `<hash>` |
| Machine name or placeholder | `is_local_name(domain)` | `<hash>` |
| Subversion-era commit address | domain matches `SVN_DOMAIN` (repository UUID, `localhost`, `users.sourceforge.net`) | unchanged |
| GitHub noreply address | `NOREPLY` | unchanged |

**Where the domain is kept** (decided with Jens): only in the excerpts below `curated/sources/excerpts/`, because there it is the organisation evidence that the affiliations cite, and, as a consequence, in the `snippet` cells of `identities.csv` and `citations.csv`, which quote those excerpts verbatim and must still be found in them. Everywhere else every masked address is the bare `<hash>`, whatever the domain: the `value` of a `kind=email` identity (it only serves matching, and no code reads a domain from it), `notes` and other free text in the curated CSV files, collected changelog signatures, docs, the archive.
So the table above gives the form *in excerpts and snippets*; elsewhere the company row reads `<hash>` as well.
Subversion-era and noreply identities stay unchanged, as in the table.

The existing list of general mail services, `PERSONAL_DOMAINS`, is reused as it is, and stays the single list.
A domain that is the person's own (`is_own_domain_for`) counts as a company domain here, as it does for the attribution rules, because a registered organisation always wins there; the local part is hashed in any case.

Decided with Jens: general services masked completely, company addresses as `<hash>@<domain>`, the archive included.

Decided with Jens: CVS and Subversion are out of scope. Their commit addresses (`SVN_DOMAIN`: repository UUID, `localhost`, `users.sourceforge.net`) stay as they are, and this work adds no handling for them.

Claude's call: GitHub noreply addresses stay readable as well. They are no mailboxes and carry only the public GitHub login, which is the evidence that links the commit to the account.

## Masked form

- Matching compares the bare hash of the incoming address with the identity value, exactly. The commit-domain collector and the evidence tools read the domain from the raw addresses in the clones and the GitHub API, as before, so the organisation attribution doesn't change.
- Hash: SHA-256 of the normalised address, hexadecimal, shortened to 16 characters, with a fixed prefix that makes a masked value recognisable, for example `h-1f3a9c0b7d4e5f60` and `h-1f3a…@jarn.com`. The exact prefix is the builder's choice; it must not be mistaken for a login or a name, and it must keep the masked company form a syntactically valid address-like string so the domain helpers (`domain_of`) work on it unchanged.
- No secret salt. Anyone who knows an address can compute its hash and find it in the data. This is what lets contributors and maintainers add or check identities without a secret, and it is fine for the purpose: the repository no longer serves addresses to someone who doesn't already have them.
- One function in `scripts/lib/` does the masking, and one regular expression finds addresses in free text. Every place uses these two.
- Because identity values carry no domain, matching doesn't depend on `PERSONAL_DOMAINS` or the other lists, and a change to them needs no re-masking. An excerpt keeps the form it was captured with; a superfluous domain there does no harm.

## Where addresses enter, and what changes

The builder should find every place; the known ones are:

- **Matching.** `Registry` indexes `kind=email` identities (`scripts/lib/model/registers.py`), `Finder` in `scripts/lib/commit_authors.py`, `scripts/tools/person.py`, `scripts/collect/plone_contributors.py`, `scripts/lib/changelogs.py` (email signatures of changelog entries, and the Subversion login index). Incoming raw addresses are hashed before lookup; stored values are already bare hashes. A lookup with a value that is already masked (bare or with a domain) must work too.
- **Capture.** `scripts/lib/capture/extract.py` builds `Author: Name <address>` for commits and extracts passages from pages, which can contain contact addresses. The capture masks every address in the excerpt text before it writes it, and masks a `--quote` the same way before it searches, so a snippet with an address is found in the masked excerpt. `SnippetInExcerpt` compares masked with masked.
- **Proposals and evidence tools.** `scripts/tools/address_proposals.py`, `scripts/tools/github_evidence.py` and any other tool that writes identities, citations or notes write masked values. Printing a raw address to the terminal of the person running the tool is fine; writing it to a tracked file is not.
- **Collectors.** The changelog collector writes unmatched signatures masked. If an id is computed from text that contains an address (`text_hash` in `scripts/lib/changelogs.py`), the builder decides whether to compute it before or after masking, and must make sure no reference to an existing id breaks.
- **Notes and free text.** `notes`, `snippet` and quote cells in the curated CSV files can contain addresses; the migration masks them in place.

## Migration

- A one-off migration masks every address in every tracked text file below `curated/`, `collected/`, `derived/`, `reports/`, `docs/`, `tests/` and `archive/`, applying the masking rule above. It keeps CSV quoting intact and changes nothing but the addresses.
- `archive/`: an explicit exception to the rule that the archive is never edited, for this one migration only. `archive/README.md` and `AGENTS.md` say so: the archive is kept unchanged except that mail addresses are masked.
- Tests: no real address in any test, decided with Jens, and that includes the Subversion-era forms (real logins such as `andyd_@localhost` become invented ones such as `jdoe@localhost`). Every test address is invented and uses a reserved top-level domain (RFC 2606/6761): `example.com` for a placeholder, `.test` for a company domain (`jane@acme.test`: `is_local_name` doesn't treat `.test` as a placeholder, so it counts as a company domain), and a `.test` name that matches a wildcard entry of `PERSONAL_DOMAINS` for a general mail service (`jane@gmx.test`, `jane@yahoo.test`). The guard enforces the domains; the invented Subversion logins are checked by hand in review.
- The migration itself is archived with its output, as earlier migrations were (`archive/migration-*`).

Acceptance of the migration (Claude's call):

- Run the derive and report stages before and after; `derived/` and `reports/` are identical, apart from masked addresses in text.
- An offline equivalence check for matching, instead of re-running the collectors (which would also pick up new commits): take every raw author address and name from the cached clones, and from the collected data where it still has them, look each up with the old registry and with the masked one, and require identical persons for all of them. No network needed.
- The checks (`make check`, the register checks, `make test`) pass.
- The builder records both comparisons in the pull request.

## The guard

A check, run by the test suite, fails on a readable mail address in any tracked text file. Allowed: masked values, Subversion-era and noreply addresses, and the domains reserved for examples and tests (`example.com`, `example.org`, `example.net`, `.example`, `.test`).
Addresses spelled out to fool harvesters (`jane at acme dot test`) are masked by the migration where it finds them, with the same rule; the guard doesn't try to recognise spelled-out forms (Claude's call: they are rare, the person chose to obscure them, and a pattern for them would raise false alarms). A small allowlist for addresses that are not a person's (for example a project's public contact address in the documentation) is the builder's choice; each allowlisted address says why.

## Documentation

In the same pull request, per the project rule:

- `docs/reference/mapping-files.md` and `docs/reference/data-files.md`: the masked form of `kind=email` identities and of addresses in excerpts.
- `docs/how-to/link-old-commits-to-a-person.md` and `docs/how-to/capture-a-source.md` (or wherever adding an address identity is described): how to add or look up an address — the tools mask it; a helper prints the masked form of a given address.
- `docs/explanation/attribution.md`: that company domains stay readable as evidence, and why the rest is masked.
- `docs/reference/tools.md`: the helper that prints the masked form of an address (bare for an identity, with domain for text).
- `curated/schemas/identities.json`: the description of `value` for `kind=email`, and a pattern if the builder adds one.
- `AGENTS.md` and `archive/README.md`: the archive exception.

## Left to the builder

- Module and function names, the prefix of the masked form, the regular expression for addresses in free text.
- How the migration is run and archived.
- The order of the work and how it is split into commits.
- The allowlist of the guard.

## Constraints

- Work in a git worktree on its own branch from `origin/main`.
- Code changes get offline pytest tests; the GitHub API is replaced by fakes.
- Commit messages and the pull request end with `Assisted-by: <model name>`, one line per model that contributed, and no other trailers (per `AGENTS.md`).
- Before the pull request, `python -m scripts.tools.attribution_changes` lists no person and year that counts for another organisation (per `AGENTS.md`); the pull request says so.
- As the last step before the pull request, this design and its plan go unchanged into `archive/specs-and-plans/` with a dated filename.
