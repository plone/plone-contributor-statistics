# Plan: release managers 2004–2019 with sources

Part of #86: curated community data with a public record for every row, reaching back as far as the records do.

## Definition

A release manager is someone approved by the Board or listed on the Release Team page (docs/explanation/curated-community-data.md).
A person counts for a year when a source shows them appointed, confirmed, paid or acting as release manager in that year.
Years between records are not filled in.

## Sources

- The Board minutes on plone.org, read once into a local copy for searching.
- plone.org news: appointments and release announcements that name the release manager.
- Archived plone.org release pages, whose "Release Manager" field names the release manager of each release.
- Conference pages that describe the person as release manager.

## Steps

1. Collect one row per person and year, with a verbatim quote and the URL of the record.
2. Take the GitHub login from the account's profile or commits, and the organisation from the organisation mapping for that year, citing its source; otherwise Unmapped.
3. Write the files 2004–2019 in the format of 2020–2025, `Name,Github,Organisation,Source`.
4. Add the missing source to the 2025 file, and fix its login and spelling.
5. Add a format check, update the docs, and regenerate the community recognition report.
