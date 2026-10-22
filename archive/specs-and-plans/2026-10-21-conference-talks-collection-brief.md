# Brief: collect the talks of one Plone Conference

You collect the programme of one year's Plone Conference for the repository `plone-contributor-statistics`, which records community contributions with a public record for every row. You do not edit the repository; you write one JSON file and report. Another agent builds the CSV, adds people to the register and re-fetches every address you give, so every address must be one you fetched yourself and that shows what you claim.

## What counts

- A **keynote**, a **talk** or a **panel** in the conference programme (type `Keynote`, `Talk`, `Panel`, as the programme calls it; a panel is a discussion with several named participants, all of them its speakers).
- Not counted: trainings and tutorials, lightning-talk sessions, open spaces, sprints, social events, the welcome and closing sessions, the annual Foundation meeting. A talk given twice is one row.
- Every speaker the programme names. Where a talk names a company team instead of people, record the team's name in `organisations_text`.

## Where to look

1. The conference site of the year (`YYYY.ploneconf.org` or the older `ploneconfYYYY.org`, or the plone.org conference pages for the early years), live or in the Wayback Machine (`http://web.archive.org/web/<timestamp>id_/<url>`; `id_` gives the raw page; the CDX API `http://web.archive.org/cdx/search/cdx?url=<host>/*&from=YYYY&to=YYYY+2&filter=statuscode:200&fl=original,timestamp&collapse=urlkey&limit=2000` lists what is archived). Sites built with Volto render only an empty shell: use the archived `++api++` JSON or the talk pages, and the printed schedule (a PDF or the schedule page) if there is one.
2. The recordings: the Plone channel on YouTube has a playlist per conference (search the channel `https://www.youtube.com/@plone` or the playlist list `https://www.youtube.com/@plone/playlists`); `yt-dlp --flat-playlist -J <playlist url>` lists ids and titles, `yt-dlp -J <video url>` gives a video's description, which often names the speaker and the talk page. Older conferences published on plone.tv, Vimeo or blip.tv, archived.
3. Speaker pages or bios on the conference site: they give the GitHub login (often shown as a handle) and the speaker's organisation of that year.

Fetch with `curl -sL --compressed --max-time 90 -A 'Mozilla/5.0'`. The Wayback Machine returns empty bodies or "Temporarily Offline" pages at times: wait 30 seconds and retry up to five times, and pace your requests (one every two seconds). Tools that help: `pdftotext` for PDFs, `python3` for HTML to text (`re.sub(r'<[^>]+>', ' ', html)`), `yt-dlp`.

## What you deliver

Write `OUTPUT_PATH` (given in your task) as JSON:

```json
{
  "event": "Plone Conference 2019",
  "scope": "global",
  "sources_used": ["<every programme, schedule, playlist or speaker index address you read>"],
  "talks": [
    {"type": "Talk", "title": "<as the programme prints it>",
     "speakers": [{"name": "<as printed>", "github": "<login or null>", "page": "<speaker page or bio address or null>"}],
     "organisations_text": [],
     "video": "<recording address or null>",
     "source": "<the address that proves the talk: its programme or talk page, preferably archived; else the recording>",
     "notes": "<anything the builder must know, else empty>"}
  ],
  "affiliations": [
    {"name": "<speaker>", "organisation": "<as the page says>", "quote": "<the sentence>", "page": "<address>"}
  ],
  "gaps": ["<what you could not find, and what you tried>"]
}
```

Rules for the addresses: an archived page is cited with its Wayback address including the timestamp; a live page with its live address; a recording with its watch address (`https://www.youtube.com/watch?v=<id>`). Never invent or guess an address, never cite a page you did not open. A speaker whose name you could not find on any page stays out.

Rules for the speakers: names as printed on the programme; the GitHub login only when a page of the conference or the person's own site shows it (say which page in `page`); when you recognise a speaker from the people register (`curated/mappings/people.csv` in the repository, read-only), you may add `"id": "<register id>"`.

Rules for the affiliations: one entry per speaker page or bio that names the speaker's employer or company that year, quoted; this is the evidence the project needs most, do not skip it. A role in the Plone Foundation or a user group is not an employer.

## Report

Reply with: the number of talks found, how many have a recording, how many speakers have a GitHub login, the gaps, and the path of the JSON file. Keep the report short; the file carries the data. End with `Assisted-by: <your model name>`.
