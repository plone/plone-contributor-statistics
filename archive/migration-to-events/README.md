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
- Items that ended in an error are permanent for this plan: addresses that name neither a quote nor a name, so nothing could be located, Wayback addresses with a short timestamp, one gzip error on an archived page, and videos without captions.

## Summary

- Pages: 1,782 items. Stored: 1,361, of which 1,058 added passages and 305 miss some quotes; the rest were already known. Nothing found (no source id, no error): 325. Errors: 96 (87 without a quote or name, 8 short Wayback timestamps, 1 gzip error).
- Top hosts of the pages: web.archive.org 980, plone.org 324, then the ploneconf.org yearly sites with about 50 each, community.plone.org 49, sourceforge.net 26.
- Videos: 235 items. Stored: 46 (25 miss some names). Nothing found: 146. Errors: 43 (35 without a usable name, 7 without captions, 1 playlist). 0 rate limited. 265 caption manifests in the cache.
