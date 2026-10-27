(how-to-link-old-commits-to-a-person)=

# Link old commits to a person

This guide shows you how to credit commits to a person when GitHub doesn't link their email address to an account.
This is common for commits from the Subversion years, with addresses like `name@localhost`, and for old company addresses.
You need to know who is behind the address, and a source for it.

## Find the address

A company address of the Git years is masked in the register, so look it up with its masked form: `python -m scripts.tools.person jane.doe@kitconcept.example` masks the address before it searches.

1.  Find the commits in the repository's history, for example with `git log --author=name@localhost` in a clone of the repository.
2.  Check that the address isn't an identity yet:

    ```shell
    grep -i "name@localhost" curated/mappings/identities.csv
    ```

## Add the person and the identity

Find the person, or add them if they are not in the register, see {doc}`add-a-person`.
Capture the record that connects the address to the person, such as a commit linked to the person's account or the [credits of Plone 2.0](https://github.com/plone/Products.CMFPlone/blob/2.0/CREDITS.txt), see {doc}`capture-a-source`:

```shell
python -m scripts.tools.capture https://github.com/plone/plone.api/commit/<commit> --name "name@localhost"
```

Then add one row to `curated/mappings/identities.csv`, sorted by person, kind and value:

```text
person,kind,value,source,snippet,notes
jane-doe,email,name@localhost,0123456789ab,name@localhost,Same name in commits linked to this account
```

- Use the kind `email`. For an address of GitHub's own forms or of the Subversion years, such as `name@localhost`, write it in lower case. For any other address, write the masked address (see {ref}`masked-addresses`), which `python -m scripts.tools.mask_address jane.doe@kitconcept.example` prints: the first form, `h-<hash>`, is the value, and the second, `h-<hash>@kitconcept.example`, is how the excerpt and the snippet quote a company address. `make check` rejects a raw address as the value.
- `source` is the id of the source that the tool printed, and `snippet` the words of its excerpt that make the connection, such as the address; leave the snippet empty when the excerpt has no such words.
- In `notes`, say how you know: the same name in commits that are linked to the account, an entry in the credits, the account profile, or a confirmation by the person in public.
- A person with a GitHub account is counted under their login, a person without one as `person:<id>`.
- For addresses from the CVS and Subversion years, a public record is often impossible. There, the identification may rest on a confirmation by people who worked with the person: leave `source` empty and say in `notes` what the identification rests on. Only an identity of the kind `email` may be without a source.

## Merge a second account

If GitHub links the address to a second account of a person, add the account as an identity of the kind `github-alias` instead:

```text
person,kind,value,source,snippet,notes
jane-doe,github-alias,oldaccount,0123456789ab,,the account has no name or repositories; the commits are by Jane Doe
```

Its source is the captured profile of the account or a commit of it.
The commits and pull requests of the further account count for the person, under the login of their `github` identity.

## Link a changelog name

Old changelog entries end with the name of the person who made the change, often a nickname such as `[alecm]`.
Names that no identity links to a person count as written, see {doc}`/explanation/counting-rules`.

1.  List the names without a mapping, by their number of entries:

    ```shell
    python -m scripts.tools.unmatched_changelog_names
    ```

    It reads the changelogs from the clones in `.cache/repositories/` of the current directory, so run `make run-changelogs` first.
    Without clones it reports `0 changelog names without a mapping`, without saying that the clones are missing; in a worktree, see {doc}`/explanation/known-limitations`.
    It lists the names of 2004 to 2012; `--from-year` and `--to-year` choose other years.

2.  Let the tool propose people from the commits whose message repeats an entry with the name:

    ```shell
    python -m scripts.tools.unmatched_changelog_names --propose
    ```

    It needs `GITHUB_TOKEN` in `.env` or in the environment, see {doc}`collect-data-again`.
    It prints rows for `curated/mappings/identities.csv`: the author of most of these commits, with the GitHub account that GitHub links to the commit, or the person that an email identity gives.
    Each row cites the commit that repeats an entry with the name, by the id its source will have, with the `Author:` line of the commit as the snippet, and its notes link the changelog entry and the commit.
    The tool writes nothing: above each row it prints the command that captures the commit, as `# capture first: …`.
    The last three columns, the number of entries, of matching commits and the author's share of them, are for your review and don't go into the file.

3.  Check each proposal before you add it.
    A commit names the committer, and in the Subversion years people often committed the patches of others, so the proposed person may be the one who committed the work, not the one who did it.
    Open the linked entry and commit, and look at a few more entries with the name.
    A short name that several people may have used, such as a first name, needs particular care.

4.  Run the capture command of each row you accept, then add the row to `curated/mappings/identities.csv`, with the kind `name`, in its place sorted by person, kind and value:

    ```text
    person,kind,value,source,snippet,notes
    alec-mitchell,name,alecm,0123456789ab,Author: Alec Mitchell <h-<hash>>,Changelog entry: https://github.com/plone/Products.CMFPlone/blob/<commit>/HISTORY.txt#L123; the commit by Alec Mitchell that repeats it: https://github.com/plone/Products.CMFPlone/commit/<commit>
    ```

    A row whose person starts with `?no person for` names someone the register doesn't have: add the person first, see {doc}`add-a-person`, and put their id in the row.
    A name of one word matches like any other name, so check that no other person used it.

5.  Collect the changelog entries again, and regenerate the statistics as described in {doc}`regenerate-after-a-mapping-change`:

    ```shell
    make run-changelogs
    ```

## Check and send the change

1.  Validate the files and run the tests:

    ```shell
    make check
    make test
    ```

2.  Open a pull request and name the source in its description.

The change takes effect with the next collection, see {doc}`collect-data-again`.

{doc}`/explanation/counting-rules` explains how commits are linked to people, and {ref}`reference-curated-files` describes the file formats.
