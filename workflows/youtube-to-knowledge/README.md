# YouTube → Knowledge

Paste a YouTube link into a form and get a structured markdown research note saved to Google Drive. The workflow pulls the video's captions, summarizes them into a dense, skimmable breakdown with an LLM, and files the result in Drive.

## Flow

```
Form (YouTube URL)
  → Fetch Transcript (yt-dlp captions service)
  → Build Prompt
  → Generate Breakdown (Claude Haiku)
  → Build Markdown (frontmatter + breakdown)
  → Save to Google Drive (Create From Text)
  → Completion screen with the Drive link
```

The LLM produces the same six-section breakdown shape as the AgeniusDesk youtube-research module: one-line thesis, key concepts, architectures/workflows, notable techniques, tools & people named, and how to apply it.

## Why a captions service (not the YouTube API)

YouTube's official Data API `captions.download` only works for videos **you own** (OAuth). To transcribe any public link you need [yt-dlp](https://github.com/yt-dlp/yt-dlp), which discovers and downloads the caption track YouTube already serves. Running yt-dlp inside n8n is awkward (and impossible on n8n Cloud), so this template calls a tiny HTTP service that wraps it. The service lives in [`service/`](service/) — build it and point the workflow at it.

Captions-only: no Whisper/GPU. Videos with captions disabled return a `422` and the run fails cleanly.

## What you need

- n8n (self-hosted or Cloud)
- The **yt-dlp captions service** from [`service/`](service/), reachable over HTTP
- **Anthropic** API key (Claude Haiku writes the breakdown; swap for any provider)
- **Google Drive** OAuth2 credential

## Setup

1. **Deploy the service** — see [`service/README.md`](service/README.md). Note its URL.
2. **Import** `youtube-to-knowledge.json` into n8n.
3. **Fetch Transcript** — set the URL to your service, e.g. `http://ytdlp-captions:8080/transcript`.
4. **Generate Breakdown** — attach your **Anthropic** credential (or repoint the HTTP node at another provider).
5. **Save to Google Drive** — attach your **Google Drive** credential and set the target folder (`YOUR_DRIVE_FOLDER_ID`).
6. Open the form's **Production URL** and paste a link.

## Customize

- **Deep dive:** add a second LLM call after the breakdown using the module's `DEEP_DIVE` prompt for a transcript-grounded extraction (exact numbers, command sequences, quotes), and save it as a second file.
- **Auto-filing:** classify the note into a topic folder before saving (the module does this) by adding a small LLM call + a Drive folder lookup.
- **Other sinks:** swap the Drive node for Notion, S3, or an n8n knowledge/RAG ingestion workflow.
- **Long videos:** very long transcripts can exceed the model's output budget; chunk + map-reduce, or raise `max_tokens` on the Generate Breakdown node.

## License

MIT
