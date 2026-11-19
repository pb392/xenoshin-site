FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RAG_DB_PATH=/data/rag.sqlite3
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY corpus ./corpus

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

RUN useradd --create-home --uid 10001 rag && mkdir -p /data && chown rag /data
USER rag
VOLUME ["/data"]
EXPOSE 8000

# Import is repeatable: on every start it only embeds new or changed chunks.
# If the import fails (for example no API key yet), the app still starts.
CMD ["sh", "-c", "python -m app.importer > /data/last-import.json 2>&1 || echo 'import reported a problem; see /data/last-import.json'; exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
