# Capture of the cited sources, 2026-10-22

One bulk run that fetched the web pages, commits, issues, profiles and videos which the mapping files in `curated/mappings/` cite, and stored the passages around the quoted words in the source register (`curated/sources/`).
It ran once, on 2026-10-22, as plan 2a of the data structure work; plan 2c reads these files to attach sources to the affiliation rows.

## Files

- `worklist.jsonl`: one line per cited URL to capture, with the quotes the mapping cells give for it.
- `searches.json`: the GitHub commit searches that were expanded into commit URLs (each search URL in a cell became the commits it found).
- `review.jsonl`: segments the work list could not attach with certainty: quote-only segments without an address of their own, and addresses that carry the quotes of a neighbouring segment.
- `capture-results.jsonl`: one line per work list item: `url`, `source_id`, `created`, `added` (passages stored), `missing` (quotes not found), `unreachable`, `error`.
  A `source_id` of `null` without an `error` means nothing was recorded for that URL.

## Commands

```sh
GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.cited_sources \
  --worklist archive/migration-to-sources/worklist.jsonl \
  --searches archive/migration-to-sources/searches.json \
  --review archive/migration-to-sources/review.jsonl
GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.capture \
  --batch archive/migration-to-sources/worklist.jsonl \
  --results archive/migration-to-sources/capture-results.jsonl
```

The batch command resumes: run it again after an interruption and it skips the items that already have a result.
Output: `curated/sources/sources.csv` and the passages in `curated/sources/excerpts/` (one file per source).

## Run notes

- The Internet Archive was asked at most once every 4 s, which made the first run last a few hours.
- The first pass downloaded YouTube captions without a pause and YouTube answered with HTTP 429.
  The adapter was fixed (original caption track only, 30 s pace, distinct "rate limited" error) and the video items were retried.
  75 videos are still rate limited in the results and **pending a retry**: delete their lines from `capture-results.jsonl` (the ones whose `error` starts with `https://www.youtube.com/watch?v=` and contains `yt-dlp failed`) and run the batch command again once the limit has cooled down; it fetches only the missing items.
- GitHub profiles captured before the fix that every profile text starts with `Login: <login>` lack that line.
- GitHub's commit search intermittently answered with incomplete or empty results; empty answers were cleared and asked again up to four times.
- After fixes for bare names, role brackets in names and plone.org `text7` blocks, the work list was regenerated and the 80 items that had stored nothing (or whose source id dangled) were captured again: 18 stored, 62 still nothing.
  Non-video errors were retried twice; seven stayed.

## Summary

- Work list: 2,123 items, 1,030 of them with quotes; 58 searches expanded to 151 commits, two searches found nothing after retries.
- Review file: 26 quote-only segments and 464 carried-quote addresses.
- Results: 2,123 lines.
  - Stored: 1,979, of which 674 miss some quotes.
  - Nothing found (no source id, no error): 62.
  - Errors: 82. 75 YouTube rate limits (pending retry), 2 YouTube videos without captions, 1 HTTP 999 (LinkedIn), 1 HTTP 403, 1 connection timeout, 1 gzip error on an archived page, 1 Wayback address with a short timestamp.
- Top hosts by items: github.com 928, web.archive.org 441, plone.org 124, sourceforge.net 86, www.youtube.com 77, then the ploneconf.org yearly sites with about 45 to 50 each.
- The repository stores passages only: the whole text only for commits, profiles and issues of this repository.
