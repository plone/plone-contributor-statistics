(how-to-add-a-person)=

# Add a person

This guide shows you how to add a person to the register, so that data can refer to them by id.
Do this before you add an affiliation or a row of community data that names a person who is not in the register yet.
You need a public record that connects the person to their name and, if they have one, their GitHub login.

1.  Check that the person is not in the register yet, under another spelling:

    ```shell
    python -m scripts.tools.person "Jane Doe"
    ```

    The tool finds a person by id, name, login or email.

2.  Add the person with the tool:

    ```shell
    python -m scripts.tools.person --add "Jane Doe" --github janedoe --source https://github.com/janedoe
    ```

    Leave out `--github` for a person without a GitHub account.
    The tool creates a row in `curated/mappings/people.csv` with a generated id, such as `jane-doe`, and prints it.
    Do not choose or change an id by hand: ids are opaque, and once a row exists its id is never renamed.

3.  Use the name in the spelling the person uses in public, usually the name on their GitHub profile.
    A different spelling in a source, an email address of old commits or a second GitHub account is an identity, see {doc}`link-old-commits-to-a-person`.

4.  Validate the files:

    ```shell
    make check
    ```

5.  Open a pull request and name the record in its description.

{doc}`add-an-affiliation` shows how to record the organisation of the person, and {ref}`reference-curated-files` describes the fields of `curated/mappings/people.csv`.
