(how-to-find-a-contributor)=

# Find a contributor

This guide shows you how to find a person in the data, for example someone you worked with years ago.
The data knows people by their GitHub login or, for a person without one, as `person:` and their id in the register, such as `person:jane-doe`.

## Search by GitHub login

If you know the login, search the contributor files of all years:

```shell
grep -i "^janedoe," collected/contributors/*-plone-contributors.csv
```

Each match starts with the file name, which shows a year in which the person contributed; the rest of the line lists the repositories they worked on.
`-i` ignores case, because the files keep the login in the case it has on GitHub.

To see who the person is and which organisations they belonged to, find them in the register:

```shell
python -m scripts.tools.person janedoe
```

The tool finds a person by id, name, login or email, and prints their rows of `curated/mappings/people.csv`, `curated/mappings/identities.csv` and `curated/mappings/affiliations.csv`, each group under the name of its file.
To see the organisation of the person in each year, and the sources of each affiliation, run:

```shell
python -m scripts.tools.affiliation jane-doe 2017
```

The tool takes the id of the person, a GitHub login, or a username as the collected files write it, such as `person:jane-doe`.
It computes the organisation of each year from all affiliations of the person, see {doc}`/explanation/attribution`.

You can also search the files directly:

```shell
grep -i "janedoe" curated/mappings/identities.csv
grep ",jane-doe," curated/mappings/affiliations.csv
```

## Search by name

Curated data lists people by id, for example conference organisers, trainers, release managers and team leaders.
Find the id first, then search the community data for it:

```shell
grep -i "jane doe" curated/mappings/people.csv curated/mappings/identities.csv
grep -r "jane-doe" curated/community/
```

`curated/mappings/people.csv` links the id to the name, and `curated/mappings/identities.csv` to the GitHub login and to other spellings of the name.

## Browse a year

To see everyone who contributed in one year, open the contributor file of that year, for example `collected/contributors/YYYY-plone-contributors.csv`.
Files exist from 2003 on.

People without a GitHub account appear in the contributor files as `person:<id>`.
`curated/mappings/identities.csv` lists the old email addresses the statistics know, as identities of the kind `email`; the addresses of the Git years are masked, so search them with `python -m scripts.tools.person <address>`, which masks the address first, see {ref}`masked-addresses`.

To find people of the early years whose commits nobody could identify yet, look at the repositories' history directly.
The statistics leave their commits out:

```shell
git clone --filter=blob:none --bare https://github.com/plone/Products.CMFPlone.git
git -C Products.CMFPlone.git shortlog --all --summary --numbered --before=2006-01-01
```

If you know who is behind an old address, {doc}`link-old-commits-to-a-person` shows how to add it.
{doc}`/explanation/history-and-coverage` explains why early contributors are often missing.
