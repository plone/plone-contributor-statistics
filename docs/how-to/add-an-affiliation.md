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

To check which row gives the organisation of a person in a year, run `python -m scripts.tools.affiliation jane-doe 2017`.
{doc}`/explanation/attribution` explains the rules the affiliations follow, and {ref}`reference-curated-files` describes the file formats.
