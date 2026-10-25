# Capture of the sources of the community data, 2026-10-25

One bulk run that fetched the web pages and videos which the curated community data in `curated/community-contributions/` cites, and stored the passages around the names and quotes in the source register (`curated/sources/`).
It ran on 2026-10-25, as plan 3a of the data structure work; plan 3b reads these files to attach the sources to the events.

## Files

- `worklist.jsonl`: one line per cited URL of the community data, without videos, with `url`, `quotes`, `names` (the names the row gives for it) and `kind`.
- `capture-results.jsonl`: one line per work list item: `url`, `source_id`, `created`, `added` (passages stored), `missing` (quotes not found), `unreachable`, `error`.
  A `source_id` of `null` without an `error` means nothing was recorded for that URL.
- `videos-worklist.jsonl` and `videos-capture-results.jsonl`: the same for the YouTube videos.

## Commands

```sh
GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.community_sources \
  --worklist archive/migration-to-events/worklist.jsonl --no-videos
GITHUB_TOKEN=$(gh auth token) python -m scripts.tools.capture \
  --batch archive/migration-to-events/worklist.jsonl \
  --results archive/migration-to-events/capture-results.jsonl
```

The videos work list was built first, with a scratch script that `community_sources` reproduces exactly (both give the same 234 unregistered videos, plus one playlist address), and run the same way with `videos-worklist.jsonl` and `videos-capture-results.jsonl`.
The batch command resumes: run it again after an interruption and it skips the items that already have a result.
Output: `curated/sources/sources.csv` and the passages in `curated/sources/excerpts/`.

## Run notes

- The Internet Archive was asked at most once every 4 s, YouTube once every 30 s.
- The video part needed a PO-token provider for yt-dlp, which Jens installed and started himself; YouTube refuses captions without it. No request was rate limited.
- The caption tracks are kept in the cache of the main checkout, `.cache/sources/video/`, one folder per video with a `tracks.json` manifest, and are reused: a video with cached tracks causes no further request to YouTube unless the capture is refreshed. The tracks are not committed.
- The video run went first and the page run after it, because two batches would race on `sources.csv`.
- The playlist address in the community data is refused: only single videos are captured.
- Items that ended in an error are permanent for this plan: addresses that name neither a quote nor a name, so nothing could be located, Wayback addresses with a short timestamp, one archived page whose gzip body could not be decoded (`ContentDecodingError`), which was not retried, and videos without captions.

## Counts

The counts are those after the final fixes: the pages of the Volto sites that came back with nothing found were captured again from the cache once their presenters were read (147 items, 47 of them now hold passages).

- Pages: 1,782 items.
  Stored: 1,408 sources.
  Of these, 1,105 got new passages and 303 were already in the register and got none.
  311 of the 1,408 miss some of their quotes or names, mostly names: 288 of those with new passages and 23 of those already in the register.
  Nothing found (no source id, no error): 278.
  Errors: 96 (87 without a quote or name, 8 short Wayback timestamps, 1 gzip body that could not be decoded, not retried).
- Top hosts of the pages: web.archive.org 980, plone.org 324, then the ploneconf.org yearly sites with about 50 each, community.plone.org 49, sourceforge.net 26.
- Videos: 235 items. Stored: 46 (25 miss some names). Nothing found: 146. Errors: 43 (35 without a usable name, 7 without captions, 1 playlist). 0 rate limited. 265 caption manifests in the cache.
