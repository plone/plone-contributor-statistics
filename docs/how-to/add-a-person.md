(how-to-add-a-person)=

# Add a person

This guide shows you how to add a person to the register, so that data can refer to them by id.
Do this before you add an affiliation or a row of community data that names a person who is not in the register yet.
You need a public record that connects the person to their name and, if they have one, their GitHub login.

1.  Decide on the spelling of the name: the one the person uses in public, usually the name on their GitHub profile.
    A different spelling in a source, an email address of old commits (stored masked, see {ref}`masked-addresses`) or a second GitHub account is an identity, see {doc}`link-old-commits-to-a-person`.

2.  Check that the person is not in the register yet, under another spelling:

    ```shell
    python -m scripts.tools.person "Jane Doe"
    ```

    The tool finds a person by id, name, login or email.

3.  Capture the public record into the source register, for example the GitHub profile with the name:

    ```shell
    python -m scripts.tools.capture https://github.com/janedoe --name "Jane Doe"
    ```

    The tool prints the id of the source.
    A GitHub profile needs `GITHUB_TOKEN` in the environment, see {doc}`capture-a-source`.

4.  Add the person with the tool, citing the source by its id or its address:

    ```shell
    python -m scripts.tools.person --add "Jane Doe" --github janedoe --source https://github.com/janedoe
    ```

    The tool creates a row in `curated/mappings/people.csv` with a generated id, such as `jane-doe`, and a row in `curated/mappings/identities.csv` that cites the source: an identity of the kind `github` with the login, or, for a person without a GitHub account, of the kind `name` with the name.
    Leave out `--github` for a person without a GitHub account.
    A source that is not in the source register is refused; capture it first.
    Do not choose or change an id by hand: ids are opaque, and once a row exists its id is never renamed.
    To show the words of the record that connect the person to the login or the name, add them to the identity as its `snippet`, as the excerpt of the source holds them.

5.  Validate the files:

    ```shell
    make check
    ```

6.  Open a pull request and name the record in its description.

{doc}`add-an-affiliation` shows how to record the organisation of the person, and {ref}`reference-curated-files` describes the fields of `curated/mappings/people.csv` and `curated/mappings/identities.csv`.
