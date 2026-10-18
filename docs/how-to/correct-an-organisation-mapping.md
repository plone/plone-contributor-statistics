(how-to-correct-an-organisation-mapping)=

# Correct an organisation mapping

This guide shows you how to correct the organisation that a contributor's work is counted for.
You need a GitHub account, and a public record for the correction: a link, or a confirmation by the contributor in the pull request.

## Decide which file to change

If the contributor works for the organisation today, change `curated/mappings/organisations.csv`.

If the contributor worked for another organisation in past years, add an override to `curated/mappings/organisation_mapping_overrides.csv` instead, and leave `curated/mappings/organisations.csv` as it is.

## Change the current organisation

1.  Find the contributor's GitHub login, spelled exactly as on their GitHub profile.
2.  Remove the login from the `Team` cell of the organisation it is listed under, if any.
3.  Add the login to the `Team` cell of the right organisation, separated from the other logins by a semicolon.
4.  If the organisation is new, add a row for it, and keep the file sorted alphabetically by organisation.
5.  Add or update the contributor's row in `curated/mappings/organisation_mapping_sources.csv`, with a link to the public record and the date you checked it.
6.  If the contributor works on Plone privately or as a volunteer, use an organisation named after the person, such as `Jane Doe (independent)`.

## Add a past organisation

Add one row to `curated/mappings/organisation_mapping_overrides.csv`:

```text
github_username,organisation,from_year,to_year,source
janedoe,Example Company,2015,2019,https://example.com/team (archived 2017)
```

Leave `to_year` empty if the override applies up to the present.
If you know that the current organisation doesn't apply to some years, but not which one did, use `Unmapped` as the organisation for those years.
In `source`, say how you know, as in the pull request description.
Spell the organisation exactly as in `curated/mappings/organisations.csv`.

## Check and send the correction

1.  Run the format tests:

    ```shell
    make test
    ```

2.  Open a pull request on [GitHub](https://github.com/plone/plone-contributor-statistics).
    Name the source of the correction in the description: a link to a profile, a company page or a speaker biography, or a confirmation by the contributor.

3.  If you want the statistics updated in the same pull request, follow {doc}`regenerate-after-a-mapping-change`.

{doc}`/explanation/attribution` explains the rules the mapping follows, and {doc}`/reference/mapping-files` describes the file formats.
