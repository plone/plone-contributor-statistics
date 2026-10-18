(how-to-find-a-contributor)=

# Find a contributor

This guide shows you how to find a person in the data, for example someone you worked with years ago.
The data knows people by their GitHub login, and the curated data also by name.

## Search by GitHub login

If you know the login, search the contributor files of all years:

```shell
grep -l "^janedoe," collected/contributors/*-plone-contributors.csv
```

Each file name shows a year in which the person contributed.
The matching line lists the repositories they worked on.

To see which organisation the person is mapped to, search the mapping files:

```shell
grep -i "janedoe" organisations.csv organisation_mapping_overrides.csv
```

## Search by name

Curated data lists people by name, for example conference organisers, trainers, release managers and team leaders:

```shell
grep -ri "jane doe" curated/community-contributions/
```

`curated/mappings/mapping-github-username-to-fullname.csv` has full names for some logins.

## Browse a year

To see everyone who contributed in one year, open the contributor file of that year, for example `collected/contributors/YYYY-plone-contributors.csv`.
Files exist from 2003 on.

People without a GitHub account appear in the contributor files under their name.
`curated/mappings/commit_authors.csv` lists the old email addresses the statistics know.

To find people of the early years whose commits nobody could identify yet, look at the repositories' history directly.
The statistics leave their commits out:

```shell
git clone --filter=blob:none --bare https://github.com/plone/Products.CMFPlone.git
git -C Products.CMFPlone.git shortlog --all --summary --numbered --before=2006-01-01
```

If you know who is behind an old address, {doc}`link-old-commits-to-a-person` shows how to add it.
{doc}`/explanation/history-and-coverage` explains why early contributors are often missing.
