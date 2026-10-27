---
myst:
  html_meta:
    "description": "Draft privacy notice of the Plone contributor statistics: what personal data they hold, where it comes from, and how to correct it or object."
    "property=og:description": "Draft privacy notice of the Plone contributor statistics: what personal data they hold, where it comes from, and how to correct it or object."
    "property=og:title": "Privacy notice (draft)"
---

(reference-privacy)=

# Privacy notice (draft)

```{important}
This is a draft by the maintainers of the statistics.
The Plone Foundation Board has not approved it yet, and it may change.
```

This page says which personal data the contributor statistics and the {doc}`community page </explanation/community-page>` hold, where it comes from, and how you can have it corrected or object to it.

## Who is responsible

The statistics are kept in the repository [plone/plone-contributor-statistics](https://github.com/plone/plone-contributor-statistics) of the Plone GitHub organisation, which the Plone Foundation owns.
The Plone Foundation is responsible for them; its maintainers keep them on its behalf.
Contact: board@plone.org.

## Purpose

The statistics make contributions to Plone visible.
They recognise the work of the people in the community, show which organisations support Plone, and provide the data for the community recognition of the Plone Foundation, see {doc}`/explanation/community-recognition`.

## Data

The statistics hold, for each person they count:

- the GitHub login, and the name as it appears in commits, on the GitHub profile or on public pages;
- counts of contributions per year: commits, pull requests and reviews in the repositories of the Plone GitHub organisation, PLIPs, and talks, trainings, organising and team roles recorded on public pages;
- the organisations the person worked for in a year, each with the public record it rests on;
- commit email addresses, as a one-way hash only, see {ref}`masked-addresses`.

The statistics hold no readable email address, no postal address, and no special categories of personal data.

## Sources

All data comes from public records, and each entry cites its source:

- public commits, pull requests and profiles on GitHub;
- public pages, such as those of plone.org and the Plone conferences, and archived copies of such pages;
- statements a person made in public.

The passage an entry relies on is quoted in the source register of the repository, see {doc}`/reference/data-sources`.

## Legal basis

The statistics rest on the legitimate interest of the Plone Foundation and the community in recognising contributions and showing who supports Plone, Art. 6(1)(f) of the General Data Protection Regulation (GDPR).
You can object at any time, see {ref}`reference-privacy-rights`.

## Recipients and hosting

The statistics are public: anyone can read the community page and the repository it is built from.
Both are hosted by GitHub, Inc. in the United States, the repository on GitHub and the community page on GitHub Pages.

## Storage

The data is kept as long as the statistics are kept.
The repository keeps the history of every change.

## Decisions

The figures are computed by the published rules of this documentation, see {doc}`/explanation/counting-rules` and {doc}`/explanation/attribution`.
The recognition levels are set by the Plone Foundation Board and the Marketing Team, not by the computation alone.

(reference-privacy-rights)=

## Your rights

You have the right to know which data the statistics hold about you, to have it corrected, to object to its use, and to have it erased or its use restricted.
You also have the right to complain to a data protection supervisory authority.

- To correct a wrong organisation or year, follow {doc}`/how-to/add-an-affiliation`, or open an [issue](https://github.com/plone/plone-contributor-statistics/issues).
- For anything you would rather not raise in public, such as an objection or a request for erasure, write to board@plone.org.

The maintainers answer within one month.
Objections and requests for erasure are handled case by case.
The public records the statistics rest on, such as the commits in the Plone repositories, are not part of the statistics and stay where they are.
