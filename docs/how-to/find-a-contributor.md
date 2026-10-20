(how-to-find-a-contributor)=

# Find a contributor

This guide shows you how to find a person in the data, for example someone you worked with years ago.
The data knows people by their GitHub login or, for a person without one, by their id in the register, such as `person:jane-doe`.

## Search by GitHub login

If you know the login, search the contributor files of all years:

```shell
grep -l "^janedoe," collected/contributors/*-plone-contributors.csv
```

Each file name shows a year in which the person contributed.
The matching line lists the repositories they worked on.

To see who the person is and which organisations they belonged to, find them in the register:

```shell
python -m scripts.tools.person janedoe
```

The tool finds a person by id, name, login or email, and prints their rows of `curated/mappings/people.csv`, `curated/mappings/identities.csv` and `curated/mappings/affiliations.csv`, each group under the name of its file.
To see which affiliation row gives the organisation in a year, run:

```shell
python -m scripts.tools.affiliation jane-doe 2017
```

The tool takes the id of the person, a GitHub login, or a username as the collected files write it, such as `person:jane-doe`.

You can also search the files directly:

```shell
grep -i "janedoe" curated/mappings/people.csv curated/mappings/identities.csv
grep "^jane-doe," curated/mappings/affiliations.csv
```

## Search by name

Curated data lists people by id, for example conference organisers, trainers, release managers and team leaders.
Find the id first, then search the community data for it:

```shell
grep -i "jane doe" curated/mappings/people.csv curated/mappings/identities.csv
grep -r "jane-doe" curated/community-contributions/
```

`curated/mappings/people.csv` links the id to the name and the GitHub login, and `curated/mappings/identities.csv` to other spellings of the name.

## Browse a year

To see everyone who contributed in one year, open the contributor file of that year, for example `collected/contributors/YYYY-plone-contributors.csv`.
Files exist from 2003 on.

People without a GitHub account appear in the contributor files as `person:<id>`.
`curated/mappings/identities.csv` lists the old email addresses the statistics know, as identities of the kind `email`.

To find people of the early years whose commits nobody could identify yet, look at the repositories' history directly.
The statistics leave their commits out:

```shell
git clone --filter=blob:none --bare https://github.com/plone/Products.CMFPlone.git
git -C Products.CMFPlone.git shortlog --all --summary --numbered --before=2006-01-01
```

If you know who is behind an old address, {doc}`link-old-commits-to-a-person` shows how to add it.
{doc}`/explanation/history-and-coverage` explains why early contributors are often missing.
