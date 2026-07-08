FROM python:3.12-slim

# ffmpeg is only needed for audio/video transcription extras; harmless otherwise.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 'markitdown[all]' pulls converters for PDF, Word, PowerPoint, Excel, HTML,
# images, audio, and more. Drop '[all]' to 'markitdown' for a smaller image if
# you only need a subset.
RUN pip install --no-cache-dir 'markitdown[all]' fastapi 'uvicorn[standard]' python-multipart

COPY app.py .

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
