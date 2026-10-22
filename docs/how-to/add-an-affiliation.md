(how-to-add-an-affiliation)=

# Add an affiliation

This guide shows you how to record that a person belonged to an organisation in a range of years, so that their work is counted for it.
You need a GitHub account, and a public record for the affiliation: a link, or a confirmation by the person in the pull request.

1.  Find the person and the organisation:

    ```shell
    python -m scripts.tools.person janedoe
    grep -i "example" curated/mappings/organisations.csv
    ```

    The tool finds a person by id, name, login or email, and prints their rows of `curated/mappings/people.csv`, `curated/mappings/identities.csv` and `curated/mappings/affiliations.csv`, each group under the name of its file.
    If the person is not in the register, add them first, see {doc}`add-a-person`.
    If the organisation is not in `curated/mappings/organisations.csv`, add a row for it, in its place sorted by id, with the columns `id,name,kind,github,aliases,notes`: a new id in lower-case letters, digits and hyphens, the name, the kind `organisation`, the login of the organisation's GitHub organisation if it has one, and empty `aliases` and `notes`.
    A person who contributes privately or as a volunteer gets an organisation of the kind `independent`, named after them, such as `Jane Doe (independent)`.

2.  Capture the public record into the source register, with the sentence that names the organisation as its quote:

    ```shell
    python -m scripts.tools.capture https://example.com/team --quote "Jane Doe, developer at Example Company"
    ```

    The tool prints the id of the source, such as `0123456789ab`, and stores the passage around the quote in its excerpt file.
    A confirmation by the person in the pull request is a record too: capture their comment by its `#issuecomment-…` address.
    {doc}`capture-a-source` describes the options, and what to do when a quote is not found.

3.  Add a row to `curated/mappings/affiliations.csv`, in its place sorted by person, first year and organisation:

    ```text
    id,person,organisation,from,to,status,checked,notes
    a1b2c3d4e,jane-doe,example-company,2015,2019,stated,2024-05-01,
    ```

    `from` is the first year and `to` the last.
    Leave `to` empty if the affiliation lasts up to the present, and fill in `checked` with the date you read the record, as `YYYY-MM-DD`.
    The status is `stated` when the record says so for these years.
    It is `assumed` when the row extends a range beyond its records, for example back from today's organisation to the first year of the person's activity; then say in `notes` what the years rest on.
    If the record covers only some of the years, say which in `notes`.

    The `id` is opaque: make it once from the person, the organisation and the years, and never change it afterwards, even when the years change:

    ```shell
    python -c "from scripts.lib.model import affiliation_id; print(affiliation_id('jane-doe', 'example-company', 2015, 2019))"
    ```

    Write `None` for an empty `to`.

4.  Cite the source: add a row to `curated/mappings/citations.csv`, in its place sorted by affiliation, source and snippet:

    ```text
    affiliation,source,snippet,supersedes,notes
    a1b2c3d4e,0123456789ab,"Jane Doe, developer at Example Company",,
    ```

    The snippet is the quote, as the excerpt of the source holds it; `make check` looks for it there.
    A source with several quotes for the affiliation gets one row per quote.
    Leave the snippet empty only when no passage of the source says it, and say in `notes` what the source shows.
    An affiliation that rests on several sources cites each of them.

5.  Do not write a row for a year in which the affiliation is unknown.
    A year that no row covers is Unmapped, and `Unmapped` is never written.
    If the person moved, give the earlier organisation its own row.
    Two records of the same organisation cover the years between them, so a row that bridges them covers those years and cites both records.
    Rows of one person may overlap, when records name two organisations for the same year; the rules in {ref}`explanation-attribution-rules` decide which one counts.
    A finding that no record supports some years, with what was checked, goes into the `notes` of the neighbouring row, so that a later reviewer knows what was looked at.
    A row never loses a source: new evidence is a new citation, and a year changes its organisation only for stronger evidence, see {doc}`/explanation/attribution`.

6.  If a statement has no accepted record yet, add it with the status `proposed`, citing what it rests on; a proposed row never counts.
    A reviewer turns it into a `stated` or `assumed` row, and keeps its citations.
    A proposal that the review turns down becomes a `denied` row, with the reason in its `notes` and a citation of the public comment where it was decided, so that the tools below don't propose those years again.
    A denied row also removes its organisation from those years when another row covers them.

7.  Validate the files:

    ```shell
    make check
    ```

    The checks name the file, the row and the column of every error.
    They also compute the organisation of every year, and fail for a year that no rule decides; see {ref}`how-to-add-an-affiliation-check`.

8.  Open a pull request on [GitHub](https://github.com/plone/plone-contributor-statistics).
    Name the source in the description.
    If you want the statistics updated in the same pull request, follow {doc}`regenerate-after-a-mapping-change`.

(how-to-add-an-affiliation-check)=

## Check the organisation of a year

The organisation of a person in a year is computed from all their rows, see {ref}`explanation-attribution-rules`.
To see the result, and the sources each row cites, run the tool with the person and the years:

```shell
python -m scripts.tools.affiliation jane-doe 2016 2017
```

The tool takes the id of the person, a GitHub login, or a username as the collected files write it, such as `person:jane-doe`.
It prints the organisation of each year, then every affiliation of the person with its status, and under it the sources it cites, with their snippets and notes.
Without years, it shows the years of the person's affiliations.
A year that no rule decides shows as Unmapped with the organisations in conflict, and `make check` fails for it.

To settle such a conflict, decide in public: write a comment on the pull request or on an issue of this repository that says which organisation the year counts for, and why.
Capture the comment as a source of the kind `decision`, and cite it from the row of the organisation you chose:

```shell
python -m scripts.tools.capture "https://github.com/plone/plone-contributor-statistics/pull/123#issuecomment-456" \
    --kind decision --name "Example Company"
```

The latest decision for a person and year counts.
A decision that overrules an earlier one names the id of the earlier source in the `supersedes` column of its citation, separated by semicolons if there are several; `make check` fails until it does.

(find-affiliations-in-commit-addresses)=

## Find affiliations in commit addresses

A company address in the commits of a person is evidence for the years of those commits, see {doc}`/explanation/attribution`.
Run the tool when you want candidates for affiliations without reading the history yourself.
It reads the author of every commit in the cached clones of the plone repositories, so it works offline; `make run-changelogs` fills the cache.

```shell
python -m scripts.tools.address_proposals                  # the report only
python -m scripts.tools.address_proposals --person jane-doe --since 2010
python -m scripts.tools.address_proposals --write          # also capture and append the proposals
```

The tool finds the person of a commit by the GitHub noreply address, then by the address, then by the author name, as the registers know them; bots and unknown authors are left out.
It leaves out the commits imported from Subversion, because the migration assigned their addresses, see {doc}`/explanation/history-and-coverage`.
Of the rest, it leaves out personal addresses (webmail, plone.org, noreply, the mail aliases of professional societies, local names) and domains that carry the person's own name unless an organisation of the register claims them, because they say nothing about an employer.
The remaining domain is matched with the names and aliases of the organisations in `curated/mappings/organisations.csv`.

The report has three tables:

-   **Proposals**: per person and organisation, a run of years with the number of commits, the domain, how the domain was matched and an example commit.
    The match is `name` (the domain equals the name of the organisation), `alias` (it equals an alias) or `first word` (it equals the first word of a name, the weakest kind and the likeliest to be wrong).
    Years that an affiliation of the same organisation covers already are left out.
    The evidence names the domain, the years and the earliest commit of the run.
-   **Conflicts**: proposed years in which `curated/mappings/affiliations.csv` has another organisation.
    The address shows only that the person used it; decide from the other records which row is right, or whether the person worked for both.
-   **Unmapped domains**: company addresses that match no organisation, with the number of commits, the years and the number of people.
    If a domain belongs to an organisation, add it to the `aliases` cell of that organisation in `curated/mappings/organisations.csv`, separated by semicolons from the other aliases, for example `greenfinity;greenfinity.hu`, and run the tool again.
    If the organisation is not in the register, add it first, see step 1 above.
    Skip domains that are an employer of nobody, such as a university alumni address or a private domain with no person's name in it; a domain the tool takes for a company is not yet one.

With `--write`, the tool captures the example commit of each proposal as a source, from the clone, and writes the proposal to `curated/mappings/affiliations.csv` as a `proposed` row that cites the commit, with the `Author:` line of the commit as the snippet.
A proposal that is in the file already is not written twice.
A proposal whose commit could not be captured is not written; the report lists it with the reason, under **Not captured**.
The capture reads the clones of the shared cache of the main checkout; with another `--cache`, it may ask the GitHub API instead, which needs `GITHUB_TOKEN`.
A run that has grown since the last `--write`, because newer commits extend it, is a different row and appears next to the earlier one; keep the longer one when you review.
The tool never writes a row that counts.
Review each proposal as any other: check that the domain is a company's, and that the person worked for the company and not only used its address, then change its status from `proposed` to `stated`, keep its citation, and run `make check`.
A match by a first word can be wrong, so look at the organisation before you accept it.

(find-affiliations-in-the-github-commit-search)=

## Find affiliations in the GitHub commit search

Many rows of `curated/mappings/affiliations.csv` are `assumed`: the migration to the registers kept today's organisation for every year of a person's activity.
The GitHub commit search dates some of them.
It finds the commits of a person in a year in all public repositories, not only those of the plone organisation.
The tool needs a GitHub token in the environment variable `GITHUB_TOKEN`, never as an option, and the search allows 30 requests a minute, so a run takes a while.

```shell
GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.github_evidence --person jane-doe
python -m scripts.tools.github_evidence --write            # all assumed rows
```

Without `--person` the tool takes the people with a GitHub login and an `assumed` row, and the years of those rows in which the person has commits or pull requests in `collected/contributors/`.
With `--person` (repeat it for several people) it takes all rows of those people.
`--all-years` queries every year of the rows, `--refresh` asks GitHub again instead of reading the cache in `.cache/github-search/`, and `--cache` names another cache directory.
Every response is cached, so a run that stops resumes where it was.

For each person and year the tool makes up to two queries:

1.  The commits of the person in the year.
    A company address in them is judged like an address in the cached clones: personal domains and domains with the person's own name say nothing, the others are matched with the organisations of the register.
    Only the first 100 commits are read, the earliest first, and the earliest one is the example.
2.  When no address names an organisation: the commits of the person in the year in the GitHub organisation of an organisation of the person, from the row of the year or of a neighbouring year.
    Only organisations with a value in the `github` column of `curated/mappings/organisations.csv` are searched.

The report has four tables:

-   **Proposals**: per person and organisation, a run of years, with the number of commits, how it was found (an address and how it matched, or the GitHub organisation) and the example commit or search page.
    Years that a stated row of the same organisation covers are left out; an assumed row is what the evidence is for, so its years are proposed.
-   **Conflicts**: proposed years in which another organisation has a row, and whether that row is assumed.
-   **Unmapped domains**: company addresses that match no organisation, to add as `aliases`, as above.
-   **Organisations without a handle**: the organisations of assumed rows in the years that no address explained, with the number of person-years.
    Fill the `github` column for the organisations you can name a GitHub organisation for, and run the tool again.

With `--write`, the tool captures the example commit of each proposal as a source and writes the proposal as a `proposed` row citing it, as above.
A commit that the search in a GitHub organisation found is cited with the search in the notes of its citation.
Review the proposals like the address proposals.
A proposal that confirms an assumed row becomes a stated row of those years; the assumed row keeps the years that no record dates yet.
A proposal that contradicts an assumed row becomes a stated row too, which wins over the assumed one in its years; `make check` says when the assumed row has to stop before it, because the organisation of the assumed row returns after it.
A proposal against a dated record goes to the reviewer.
Commits in the GitHub organisation of an employer show that the person worked on its code, which an employee does, but so does a volunteer; check the organisation before you accept.

To check the organisation of a person in a year, run `python -m scripts.tools.affiliation jane-doe 2017`, see {ref}`how-to-add-an-affiliation-check`.
{doc}`/explanation/attribution` explains the rules the affiliations follow, and {ref}`reference-curated-files` describes the file formats.
