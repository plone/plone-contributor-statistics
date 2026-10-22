(how-to-capture-a-source)=

# Capture a source

This guide shows you how to put a web page into the source register, so that a row of curated data can cite it.
Do this when a fact rests on a page, a profile, a commit or a video, and you want the passage that supports it to stay readable even if the page changes or disappears.

1.  Pick the quote: a sentence from the page that supports the fact, written as it stands there.
    Typographic quotes, dashes, line breaks and non-breaking spaces do not matter, and `…` stands for text you skip.

2.  Capture the page with the tool.
    A GitHub profile or commit is read through the GitHub API, so set `GITHUB_TOKEN` in the environment for those; never pass a token on the command line.

    ```shell
    python -m scripts.tools.capture "http://web.archive.org/web/20100125023558/http://limi.net:80/about" \
        --quote "In 2006, he moved from Norway to San Francisco"
    ```

    The tool prints the id of the source, then one line for each passage it added.
    Repeat `--quote` for more passages of the same page.
    At least one quote is required for a new source.
    `--kind`, `--title` and `--date` override what the tool finds on the page.

3.  Check the result: a row in `curated/sources/sources.csv` and the passage in the excerpt file `curated/sources/excerpts/<id>.md`.
    Do not edit these files by hand.
    Then validate the files:

    ```shell
    make check
    ```

4.  Cite the source by its id in the `source` column of the row that rests on it, and open a pull request.

## Why only passages are stored

The repository keeps the paragraph around each quote, in the page's own spelling, and never the whole page.
A short quotation to support a statement is allowed; a copy of a page, of a Wayback capture or of a full caption is not.
The complete download goes to the local cache `.cache/sources/`, which Git ignores and which nobody publishes.

## The local cache and the limits

A page that is in the cache is not fetched again, so running the tool twice makes one request.
This also lets you finish a capture that was interrupted without asking the web again.
The tool waits between requests: about one second between requests to the same host, and four seconds for `web.archive.org` and `archive.org`.

## A quote is not found

The tool prints `! not found: <quote>` and exits with status 1; it stores nothing for that quote.
Open the page, copy the sentence again and check the spelling.
The text may sit in a part of the page that is not part of the article, in which case the tool also searches the rest of the page.
Do not shorten a quote until it matches something that does not say what you cite.

## A page is not reachable

When the address is gone, the tool looks for the nearest Wayback capture and records that one.
Without a capture, it records the source as unreachable with a note, and prints `! unreachable`.
A fetch error such as a refusal or a timeout is not a gone page: the tool prints `! <message>`, exits with status 1 and writes nothing.

## Refresh a page that changes

Profiles and other live pages change.
Fetch such a page again with `--refresh`, which replaces the cached copy and updates the fetch time of the row.
Passages that are already stored stay as they are.

{ref}`reference-curated-files` describes the fields of `curated/sources/sources.csv`.
