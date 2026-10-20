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
    If the organisation is not in `curated/mappings/organisations.csv`, add a row for it, in its place sorted by id, with the columns `id,name,kind,aliases,notes`: a new id in lower-case letters, digits and hyphens, the name, the kind `organisation`, and empty `aliases` and `notes`.
    A person who contributes privately or as a volunteer gets an organisation of the kind `independent`, named after them, such as `Jane Doe (independent)`.

2.  Add a row to `curated/mappings/affiliations.csv`, in its place sorted by person and first year:

    ```text
    person,organisation,from,to,source,checked,notes
    jane-doe,example-company,2015,2019,https://example.com/team,2024-05-01,
    ```

    `from` is the first year and `to` the last.
    Leave `to` empty if the affiliation lasts up to the present, and fill in `checked` with the date you read the record, as `YYYY-MM-DD`.
    In `source`, put a link to the public record: a profile, a company page, an archived page or a speaker biography.
    If the record covers only some of the years, say which in `notes`.

3.  Do not write a row for a year in which the affiliation is unknown.
    A year that no row covers is Unmapped, and `Unmapped` is never written.
    If the person moved, give the earlier organisation its own row and end it the year before the next one starts; the rows of one person must not overlap.

4.  If a statement has no accepted record yet, add it to `curated/mappings/affiliation_proposals.csv` with the evidence, instead of `curated/mappings/affiliations.csv`.
    No script reads that file.

5.  Validate the files:

    ```shell
    make check
    ```

    The checks name the file, the row and the column of every error.

6.  Open a pull request on [GitHub](https://github.com/plone/plone-contributor-statistics).
    Name the source in the description.
    If you want the statistics updated in the same pull request, follow {doc}`regenerate-after-a-mapping-change`.

(find-affiliations-in-commit-addresses)=

## Find affiliations in commit addresses

A company address in the commits of a person is evidence for the years of those commits, see {doc}`/explanation/attribution`.
Run the tool when you want candidates for affiliations without reading the history yourself.
It reads the author of every commit in the cached clones of the plone repositories, so it works offline; `make run-changelogs` fills the cache.

```shell
python -m scripts.tools.address_proposals                  # the report only
python -m scripts.tools.address_proposals --person jane-doe --since 2010
python -m scripts.tools.address_proposals --write          # also append the proposals
```

The tool finds the person of a commit by the GitHub noreply address, then by the address, then by the author name, as the registers know them; bots and unknown authors are left out.
It leaves out personal addresses (webmail, plone.org, noreply, local names), Subversion-era addresses, and domains that carry the person's own name unless an organisation of the register claims them, because they say nothing about an employer.
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

With `--write`, the proposals go to `curated/mappings/affiliation_proposals.csv`; a proposal that is in the file already is not written twice.
A run that has grown since the last `--write`, because newer commits extend it, is a different row and appears next to the earlier one; keep the longer one when you review.
The tool never writes `curated/mappings/affiliations.csv`.
Review each proposal as any other: check that the domain is a company's, and that the person worked for the company and not only used its address, then move the row into `curated/mappings/affiliations.csv` with the example commit as `source`, and run `make check`.
A match by a first word can be wrong, so look at the organisation before you accept it.

To check which row gives the organisation of a person in a year, run `python -m scripts.tools.affiliation jane-doe 2017`.
{doc}`/explanation/attribution` explains the rules the affiliations follow, and {ref}`reference-curated-files` describes the file formats.
