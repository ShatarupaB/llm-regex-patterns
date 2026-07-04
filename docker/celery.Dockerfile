# ── Celery worker (+ Flower monitor) ─────────────────────────────────────────
# Heavier than the Django image because PySpark requires the JVM.
# This is deliberate: we keep Java out of the web process entirely.
# The worker is the only container that ever touches Spark.
# ─────────────────────────────────────────────────────────────────────────────

# FROM python:3.11-slim        ← remove this
FROM python:3.11-slim-bookworm 

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# JAVA_HOME is required by PySpark to locate the JVM at runtime.
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

# Install OpenJDK 17 (LTS) + libpq for DB access
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Verify Java is reachable — catches image issues early
RUN java -version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media/uploads /app/media/results
