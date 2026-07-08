"""Minimal HTTP wrapper around Microsoft MarkItDown.

Exposes POST /convert, which accepts a single uploaded file and returns
`{ "markdown": "...", "title": ..., "filename": ... }`. This is the shape the
n8n "MarkItDown Convert" node expects. MarkItDown ships as a CLI/library, not a
server, so this thin FastAPI wrapper is what turns it into the `/convert`
endpoint the workflow calls.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from markitdown import MarkItDown
import tempfile
import os

app = FastAPI(title="MarkItDown Converter")
md = MarkItDown()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    # Preserve the extension so MarkItDown picks the right converter.
    suffix = os.path.splitext(file.filename or "")[1] or ""
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            path = tmp.name
        result = md.convert(path)
        return {
            "markdown": result.text_content,
            "title": getattr(result, "title", None),
            "filename": file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"conversion failed: {e}")
    finally:
        if path:
            try:
                os.unlink(path)
            except Exception:
                pass
