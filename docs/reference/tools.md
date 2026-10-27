(reference-tools)=

# Tools

The modules in `scripts/tools/` help maintainers with the curated data, the evidence and the documentation.
Run them as modules from the repository root, such as `python -m scripts.tools.person janedoe`; each one answers `--help` with its options.
Most of them have no Make target, and the how-to guides show them at work.

| Module | Does | Main options | See |
|---|---|---|---|
| `person` | Finds a person by id, name, login or email (also a raw address, which it masks before it searches), or adds one with an identity that cites a source. | `--add`, `--github`, `--source` | {doc}`/how-to/add-a-person` |
| `capture` | Puts a source into the source register, with the passages around the quotes, and prints its id. | `--quote`, `--name`, `--kind`, `--date`, `--refresh`, `--batch` | {doc}`/how-to/capture-a-source` |
| `cite_snippets` | Fills empty snippets of citations and identities from the quotes in their notes, once the source is captured. | `--write` | {ref}`how-to-capture-a-source-not-read` |
| `affiliation` | Prints the organisation a person counts for in each year, with the rule, and every affiliation with its sources. | person, years | {ref}`how-to-add-an-affiliation-check` |
| `attribution_changes` | Lists the person-years whose organisation differs from a base commit. | `--base`, `--all-years`, `--markdown` | {doc}`/how-to/regenerate-after-a-mapping-change` |
| `decisions_review` | Lists the decisions with their status and the sources dated after them, and the open cases. | | {doc}`/explanation/attribution` |
| `address_proposals` | Proposes affiliations from company addresses in the commits of the cached clones. | `--person`, `--since`, `--cache`, `--write` | {ref}`find-affiliations-in-commit-addresses` |
| `github_evidence` | Proposes affiliations for the years that assumed rows guess, from the GitHub commit search; needs `GITHUB_TOKEN`. | `--person`, `--all-years`, `--write`, `--refresh` | {ref}`find-affiliations-in-the-github-commit-search` |
| `unmatched_names` | Lists people of the register without a GitHub login who appear as a login. | `--propose` | {doc}`/how-to/prepare-a-new-year` |
| `unmatched_changelog_names` | Lists changelog names that no identity maps, and proposes the person from the commits. | `--from-year`, `--to-year`, `--propose` | {doc}`/how-to/link-old-commits-to-a-person` |
| `mask_address` | Prints the masked forms of mail addresses: for identities, for notes and for snippets. | addresses | {ref}`masked-addresses` |
| `get_github_name` | Prints the profile name of GitHub logins from the GitHub API. | logins | |
| `analyze_independent_contributors` | Lists the Unmapped contributors worth researching; `make analyze-independent` runs it. | `--year` | {doc}`/how-to/prepare-a-new-year` |
| `check` | Validates the curated data against the schemas and the checks beyond them; `make check` runs it. | | {ref}`reference-curated-files` |
| `datapackage` | Writes `curated/datapackage.json`. | | {ref}`reference-curated-files` |
| `schema_docs` | Writes `docs/reference/curated-files.md` from the schemas. | `--check` | {doc}`/contributing/documentation` |
