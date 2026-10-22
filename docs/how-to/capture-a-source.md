(how-to-capture-a-source)=

# Capture a source

This guide shows you how to put a web page into the source register, so that a row of curated data can cite it.
Do this when a fact rests on a page, a profile, a commit or a video, and you want the passage that supports it to stay readable even if the page changes or disappears.

1.  Pick the quote: a sentence from the page that supports the fact, written as it stands there.
    Typographic quotes, dashes, line breaks and non-breaking spaces do not matter, and `…` stands for text you skip.

2.  Capture the page with the tool.
    A GitHub profile, commit, issue, pull request or comment is read through the GitHub API, so set `GITHUB_TOKEN` in the environment for those; never pass a token on the command line.
    A PDF is read with `pdftotext` from poppler, and a video with `yt-dlp`; install them to capture those.
    A Google Doc is read through its plain-text export, so only a public document can be captured; a private one, which asks to sign in, is refused with `not a public document`.
    Its spellings with `/edit`, `?usp=sharing` or a heading anchor are one source.
    A Wayback address needs the full 14-digit timestamp of the capture, as in the example.

    ```shell
    python -m scripts.tools.capture "http://web.archive.org/web/20100125023558/http://limi.net:80/about" \
        --quote "In 2006, he moved from Norway to San Francisco"
    ```

    The tool prints the id of the source, then one line for each passage it added.
    Repeat `--quote` for more passages of the same page.
    At least one quote or name is required for a new source.
    When the cell that cites the page has no quote, only a label in our own words, give the name of the person or organisation with `--name` instead; repeat it for several names.
    The tool then stores the paragraph around the first place where the page names them, ignoring case and accents, and prints `! not found: <name>` for a name the page does not show.
    A GitHub profile, a commit and an issue or comment of this repository are stored whole in that case, whether or not the name is found.
    Names are also used when you give quotes and the page shows none of them; they are ignored as soon as one quote is found.
    For a source that is already in the register, names without a quote add nothing and the tool does not fetch the page again; add `--refresh` to look for them.
    `--kind`, `--title` and `--date` override what the tool finds on the page.
    Give `--kind speaker-page` for the page of a speaker at a conference, because it is the person's own statement.
    A live page is dated by `--date`, else by the date the page shows, else by the day of the capture.
    A Wayback copy is dated by `--date`, else by the day of its capture; a date the page shows is not trusted for it, and a different one is kept in the `notes` of the new row as `page shows date YYYY-MM-DD`.
    The capture is the one the Archive actually served: when it redirects to a capture of another day, the source is recorded under that capture, with its own address and date.
    When it serves a capture of another page, the row keeps the address you gave and says in its `notes` which capture was read, as `served <Wayback address>`.

3.  Check the result: a row in `curated/sources/sources.csv` and the passage in the excerpt file `curated/sources/excerpts/<id>.md`.
    The passage of a page is the paragraph around the quote; the passage of a GitHub profile or commit is all of it, so the author and date of a commit stay with its message.
    For GitHub issues and comments, see {ref}`how-to-capture-a-source-github-issues`.
    Do not edit these files by hand.
    Then validate the files:

    ```shell
    make check
    ```

4.  Open a pull request with the new source.
    Nothing cites sources by their id yet: keep the address, with its quote, in the `source` cells of the rows that rest on it, as before.
    A later change switches the registers to citations of the source register.

(how-to-capture-a-source-github-issues)=

## GitHub issues, pull requests and comments

An address with a comment fragment, `#issuecomment-…`, `#discussion_r…` or `#pullrequestreview-…`, names one comment, review comment or review.
Each of them is a source of its own, apart from the issue or pull request and from its other comments, and the tool reads only that text.
An address without a fragment is the issue or pull request with the comments of its conversation.
The review comments on the code of a pull request are not part of it: cite such a comment by its `#discussion_r…` address.

An issue or comment of this repository, `plone/plone-contributor-statistics`, is our own public record, so its passage is its whole text, with its title, author and date.
Of another repository, the tool keeps only the issue or comment that holds the quote, cuts the paragraph around the quote from it, and heads that paragraph with the `Author:` and `Date:` lines of the issue or comment, so the passage still says who wrote it.

## Why only passages are stored

The repository keeps the paragraph around each quote, in the page's own spelling, and never the whole page.
A short quotation to support a statement is allowed; a copy of a page, of a Wayback capture or of a full caption is not.
The complete download goes to the local cache, which Git ignores and which nobody publishes.

## The local cache and the limits

The cache is the folder `.cache/sources/` of the main checkout, so all worktrees of a checkout share it, also with a capture made in another worktree.
The environment variable `PLONE_STATS_CACHE` names another folder to use instead of `.cache/`.
The commit adapter reads commits from the clones of the collectors in `.cache/repositories/` of the main checkout, and asks the GitHub API only for a repository without a clone.

A page that is in the cache is not fetched again, so running the tool twice makes one request.
This also lets you finish a capture that was interrupted without asking the web again.
The tool waits between requests: about one second between requests to the same host, and four seconds between two requests to the Internet Archive, whether to `web.archive.org` or to `archive.org`.
It keeps the time of the last request to each host in the cache, so the pace holds across several runs of the tool.
When a server answers that there are too many requests and says how many seconds to wait, the tool waits that long before it tries again.

## A quote is not found

The tool prints `! not found: <quote>` and exits with status 1; it stores nothing for that quote.
When none of the quotes for a new source is found, it stores nothing at all, not even the row of the source.
Open the page, copy the sentence again and check the spelling.
The text may sit in a part of the page that is not part of the article, in which case the tool also searches the rest of the page.
For a video, the tool searches the captions in the spoken language first, then the captions in the other languages it downloaded.
It asks YouTube only for the original caption tracks, never for translations, and waits at least 30 seconds between two downloads, also across runs; a video that YouTube refuses with `rate limited:` can be captured again later.
Do not shorten a quote until it matches something that does not say what you cite.

## A page is not reachable

When the address is gone, the tool looks for the nearest Wayback capture and records that one.
Without a capture, it records the source as unreachable with a note, and prints `! unreachable`.
A fetch error such as a refusal or a timeout is not a gone page: the tool prints `! <message>`, exits with status 1 and writes nothing.

## Capture many sources at once

Capturing a few hundred sources one at a time is not practical.
For a migration, give the tool a work list and a results file:

```shell
python -m scripts.tools.capture --batch worklist.jsonl --results results.jsonl
```

The work list is a JSON lines file, one object per line, for example `{"url": "https://example.org/sprint", "quotes": ["a quote"], "names": [], "kind": null}`.
`quotes` and `names` work as `--quote` and `--name` do, `kind` is a kind of source or `null` to guess it.
The tool appends one line per source to the results file and writes it at once: `{"url": …, "source_id": …, "created": true, "added": […], "missing": […], "unreachable": false, "error": null}`.
A source the tool cannot capture gets `"source_id": null` and the message in `error`, and the run goes on; an error the tool does not expect reads `unexpected: <type>: <message>`.
`"source_id": null` without an error means that nothing was recorded: a new source on which none of its quotes and names was found.
It prints its progress to the error output every 25 sources and exits with status 0 when it reached the end, whatever the outcomes; read `missing`, `unreachable` and `error` in the results.

An interrupted run resumes when you start it again with the same two files: sources with a line in the results file are skipped, and a half-written last line is ignored.
`--batch` and `--results` go together, and no address or other option is allowed with them.
This mode is meant for migrations, not for everyday work.

## Refresh a page that changes

Profiles and other live pages change.
Fetch such a page again with `--refresh`, which replaces the cached copy and updates the fetch time of the row.
`--refresh` needs a `--quote` or a `--name` as well.
Passages that are already stored stay as they are.

{ref}`reference-curated-files` describes the fields of `curated/sources/sources.csv`.
