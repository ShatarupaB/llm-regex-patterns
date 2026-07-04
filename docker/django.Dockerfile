# ── Django web process ────────────────────────────────────────────────────────
# Intentionally lightweight — no Java, no PySpark.
# The web process only handles HTTP: it dispatches tasks to Celery and returns
# job IDs. Heavy lifting never happens here.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim-bookworm 

# Prevents Python from writing .pyc files and buffers stdout immediately,
# which keeps Docker logs readable in real time.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS-level deps (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create the media directory so Django can write uploads immediately on start.
RUN mkdir -p /app/media/uploads /app/media/results

EXPOSE 8000
