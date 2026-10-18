(how-to-link-old-commits-to-a-person)=

# Link old commits to a person

This guide shows you how to credit commits to a person when GitHub doesn't link their email address to an account.
This is common for commits from the Subversion years, with addresses like `name@localhost`, and for old company addresses.
You need to know who is behind the address, and a source for it.

## Find the address

1.  Find the commits in the repository's history, for example with `git log --author=name@localhost` in a clone of the repository.
2.  Check that the address isn't listed in `commit_authors.csv` yet.

## Add the person

Add one row to `commit_authors.csv`:

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

If GitHub links the address to a second account of a person, add a row to `account_aliases.csv` instead:

```text
alias,github_username,source
oldaccount,janedoe,The account has no name or repositories; the commits are by Jane Doe
```

## Check and send the change

1.  Run the format tests:

    ```shell
    make test
    ```

2.  Open a pull request and name the source in its description.

The change takes effect with the next collection, see {doc}`collect-data-again`.

{doc}`/explanation/counting-rules` explains how commits are linked to people, and {doc}`/reference/mapping-files` describes the file formats.
