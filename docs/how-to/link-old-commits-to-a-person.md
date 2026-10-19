(how-to-link-old-commits-to-a-person)=

# Link old commits to a person

This guide shows you how to credit commits to a person when GitHub doesn't link their email address to an account.
This is common for commits from the Subversion years, with addresses like `name@localhost`, and for old company addresses.
You need to know who is behind the address, and a source for it.

## Find the address

1.  Find the commits in the repository's history, for example with `git log --author=name@localhost` in a clone of the repository.
2.  Check that the address isn't listed in `curated/mappings/commit_authors.csv` yet.

## Add the person

Add one row to `curated/mappings/commit_authors.csv`:

```text
email,github_username,name,source
name@localhost,janedoe,Jane Doe,Same name in commits linked to this account
```

- Write the email address in lower case.
- If the person has a GitHub account, put their login in `github_username`.
- If the person has no GitHub account, leave `github_username` empty; the commits are then counted under `name`.
- For addresses from the CVS and Subversion years, a public record is often impossible. There, the source may be a confirmation by people who worked with the person; say so in `source`.
- In `source`, say how you know: the same name in commits that are linked to the account, an entry in the [credits of Plone 2.0](https://github.com/plone/Products.CMFPlone/blob/2.0/CREDITS.txt), the account profile, or a confirmation by the person or by people who worked with them.

## Merge a second account

If GitHub links the address to a second account of a person, add a row to `curated/mappings/account_aliases.csv` instead:

```text
alias,github_username,source
oldaccount,janedoe,The account has no name or repositories; the commits are by Jane Doe
```

## Link a changelog name

Old changelog entries end with the name of the person who made the change, often a nickname such as `[alecm]`.
Names that no mapping file links to a person count as written, see {doc}`/explanation/counting-rules`.

1.  List the names without a mapping, by their number of entries:

    ```shell
    python -m scripts.tools.unmatched_changelog_names
    ```

    It reads the changelogs from the clones in `.cache/repositories/`, so run `make run-changelogs` first.
    It lists the names of 2004 to 2012; `--from-year` and `--to-year` choose other years.

2.  Let the tool propose people from the commits whose message repeats an entry with the name:

    ```shell
    python -m scripts.tools.unmatched_changelog_names --propose
    ```

    It needs `GITHUB_TOKEN` in `.env` or in the environment, see {doc}`collect-data-again`.
    It proposes the author of most of these commits, with the GitHub account that GitHub links to the commit, or the account in `curated/mappings/commit_authors.csv`.
    Each row links a changelog entry with the name and the commit that repeats it.
    The last three columns, the number of entries, of matching commits and the author's share of them, are for your review and don't go into the file.

3.  Check each proposal before you add it.
    A commit names the committer, and in the Subversion years people often committed the patches of others, so the proposed person may be the one who committed the work, not the one who did it.
    Open the linked entry and commit, and look at a few more entries with the name.
    A short name that several people may have used, such as a first name, needs particular care.

4.  Add the row to `curated/mappings/changelog_names.csv`, sorted by name:

    ```text
    changelog_name,github_username,name,source
    alecm,alecpm,,Changelog entry: https://github.com/plone/Products.CMFPlone/blob/<commit>/HISTORY.txt#L123; the commit by Alec Mitchell that repeats it: https://github.com/plone/Products.CMFPlone/commit/<commit>
    ```

    If the person has no GitHub account, leave `github_username` empty and write their name in `name`.

5.  Collect the changelog entries again, and regenerate the statistics as described in {doc}`regenerate-after-a-mapping-change`:

    ```shell
    make run-changelogs
    ```

## Check and send the change

1.  Run the format tests:

    ```shell
    make test
    ```

2.  Open a pull request and name the source in its description.

The change takes effect with the next collection, see {doc}`collect-data-again`.

{doc}`/explanation/counting-rules` explains how commits are linked to people, and {doc}`/reference/mapping-files` describes the file formats.
