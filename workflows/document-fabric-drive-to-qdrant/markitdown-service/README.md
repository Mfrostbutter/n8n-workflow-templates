# MarkItDown converter service

The Document Fabric workflow converts every incoming file to Markdown before it tags and chunks it. It does that by POSTing the file to an HTTP endpoint that returns `{ "markdown": "..." }`. [Microsoft MarkItDown](https://github.com/microsoft/markitdown) is a CLI/library, not a server, so this folder is a tiny FastAPI wrapper that turns it into the `POST /convert` endpoint the workflow expects. Stand it up once and point the workflow at it.

You don't have to use MarkItDown. Any service that accepts a file upload and returns `{ "markdown": "..." }` works ([Docling](https://github.com/DS4SD/docling), [Unstructured](https://unstructured.io), or your own). MarkItDown is just the simplest self-hosted default.

## Run it with Docker

```bash
cd markitdown-service
docker compose up -d --build
```

First build takes a few minutes (`markitdown[all]` pulls a lot of converters). Then:

```bash
# health
curl http://localhost:8080/health          # -> {"status":"ok"}

# convert a file
curl -F "file=@/path/to/doc.pdf" http://localhost:8080/convert
```

The response is `{ "markdown": "...", "title": ..., "filename": ... }`.

## Point the workflow at it

The workflow's **MarkItDown Convert** node ships with the URL `http://markitdown:8080/convert`. Which value you use depends on where n8n runs:

- **n8n in the same Docker network** as this service: `http://markitdown:8080/convert` works as-is (`markitdown` is the container name).
- **n8n elsewhere** (another host, n8n Cloud, a separate compose project): use the host's address, e.g. `http://YOUR_CONVERTER_HOST:8080/convert`. Make sure the port is reachable from n8n.

The endpoint must return JSON shaped `{ "markdown": "..." }`. If you swap in a different converter that uses another field name or returns raw text, adjust the Information Extractor's `text` expression and the Assemble Metadata node's `.json.markdown` reference to match.

## Notes

- **Image size:** `markitdown[all]` installs every converter. If you only ingest, say, PDFs and Word docs, change `[all]` to `markitdown` in the `Dockerfile` for a much smaller image.
- **Resources:** the service is light at idle; conversion is CPU-bound and brief. 1-2 vCPU / 1-2 GB RAM is plenty for typical documents.
- **Not just Docker:** the same `app.py` runs anywhere Python does. To run it natively: `pip install 'markitdown[all]' fastapi 'uvicorn[standard]' python-multipart` then `uvicorn app:app --host 0.0.0.0 --port 8080`.
