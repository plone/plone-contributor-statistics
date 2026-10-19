# Plan: public records for the most active unmapped contributors

Refs #70, #86.

## Research

- Take the 50 logins with the most commits and merged pull requests in years where they count as Unmapped.
- Read the earlier mapping pull requests, so that rejected evidence is not proposed again.
- Search public records for the unmapped years: mailing-list signatures and sender addresses, plone.org news, nominations and conference pages, the speaker bios of the conferences, archived company team pages, register entries, and company addresses in commits made in Git.
- Mark each finding `record` or `weak`.

## Decisions (Jens Klein)

1. An employer counts, also when it is no Plone company, as long as no record says that the Plone work was done in free time (Friends of the Earth Netherlands for svx in 2014, Stanford for lrowe in 2014–2015).
2. Google Summer of Code is not an employer.
3. A personal website is no employer, but what it says about an employer or the person's own business is evidence (garbas, dextermilo, jcbrand 2015).
4. The sender address of a list message counts for the year of the message (hannosch 2005).
5. sneridagh 2010–2015: the Universitat Politècnica de Catalunya; "independent" on the Board pages of 2015–2017 meant no company.
   do3cc 2015–2016: Zumtobel Group, from his commit address; the Starzel team page was probably not updated.
   lrowe 2010: Jarn, from the January 2010 team page.
6. Where one record names two organisations, the first one counts (hvelarde 2013).
7. Spelling: Niteo for NiteoWeb; Ecréall only.
8. Logins without a current entry get overrides for the years with records only.
9. Weak rows that only bridge years between records stay out.

## Changes

- Replace the "no public record" overrides where a record now exists; add the new overrides.
- Move the proposals that are now records to the overrides, and remove the proposals whose evidence was a commit address from the Subversion period.
- Add the new organisations; merge Ecreall into Ecréall.
- Update the curated rows whose organisation came from the mapping as Unmapped.
- Document decisions 1–4 and 6 in `docs/explanation/attribution.md`.
- Regenerate the derived data and reports.
