# yt-dlp captions service

A tiny HTTP wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp) that returns
a YouTube video's transcript. The n8n workflow calls it so it never has to run
yt-dlp itself (which keeps the workflow working on n8n Cloud).

Captions-only: no Whisper, no GPU. It grabs YouTube's own caption track (manual
subtitles first, then auto-generated). Videos with captions disabled return `422`.

## Run

```bash
docker build -t ytdlp-captions .
docker run -p 8080:8080 ytdlp-captions
```

Or without Docker:

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

## API

```
GET /transcript?url=<youtube url or 11-char id>
GET /health
```

Success (`200`):

```json
{
  "video_id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Video title",
  "channel": "Channel name",
  "duration_seconds": 213,
  "language": "en",
  "is_generated": false,
  "text": "the full transcript as plain text ..."
}
```

Errors: `400` (not a YouTube URL/id), `422` (no usable captions for this video).

## Notes

- Point the workflow's **Fetch Transcript** node at this service's URL (e.g.
  `http://ytdlp-captions:8080/transcript` on the same Docker network, or your
  hosted URL).
- `yt-dlp` needs occasional updates as YouTube changes. Rebuild the image to pull
  a newer `yt-dlp`.
- Consider putting it on a private network / behind auth; it will fetch any
  YouTube URL it is handed.
