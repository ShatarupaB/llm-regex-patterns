# NL-to-Regex Distributed Data Processing Platform

A full-stack web application that lets users upload CSV/Excel files, describe patterns in natural language, and apply regex transformations at scale using distributed processing.

**Live URL:** https://determined-illumination-production-62b3.up.railway.app

## Demo Video

[![Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://youtu.be/YOUR_VIDEO_ID)

---

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   React UI  │──HTTP──▶│   Django    │──tasks─ │   Celery  │
│  (Vite)     │         │   REST API  │          │   Worker    │
└─────────────┘         └──────┬──────┘          └──────┬──────┘
                               │                        │
                          ┌────▼────┐            ┌──────▼──────┐
                          │Postgres │            │   PySpark   │
                          │  Jobs   │            │  Transform  │
                          └─────────┘            └─────────────┘
                               │                        │
                          ┌────▼────────────────────────▼────┐
                          │              Redis                │
                          │  db/0: Celery broker + results   │
                          │  db/1: LLM regex cache           │
                          └───────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| API | Django 4.2 + Django REST Framework |
| Task queue | Celery 5.4 |
| Message broker + cache | Redis 7 |
| Data processing | PySpark 3.5 |
| LLM | Anthropic Claude (Gemini fallback) |
| Database | PostgreSQL 15 |
| Deployment | Railway |

---

## How It Works

1. User uploads a CSV/Excel file and describes a pattern in plain English
2. Django accepts the request, creates a Job record (status=QUEUED), and returns a job ID **immediately** — it never processes data inline
3. Celery picks up the job from the Redis message queue
4. **LLM stage**: Redis cache is checked first — cache hit returns instantly, cache miss calls the Anthropic API and stores the result (7-day TTL, keyed by SHA-256 hash of the prompt)
5. **Spark stage**: PySpark reads the file, applies `regexp_replace()` across all partitions in parallel, writes the result CSV
6. Job status updates to SUCCESS with result path
7. React frontend polls `GET /jobs/{id}/` every 2 seconds, displays live progress
8. Results served paginated (100 rows at a time), downloadable as CSV

---

## Architecture Decisions

**Django separate from Celery** — the web process must respond immediately. Processing a large file inline would time out. Django only accepts requests and dispatches work.

**Redis for both broker and cache** — separate database indices (db/0 for Celery, db/1 for cache) mean flushing the LLM cache never touches the task queue.

**PySpark over pandas** — `pandas.iterrows()` processes rows sequentially. Spark's `regexp_replace()` runs as a distributed transformation across partitions in parallel. For large datasets the difference is significant.

**Polling over WebSockets** — polling every 2 seconds is simple, self-healing, and sufficient for jobs that take 10-60 seconds. WebSockets would add complexity for marginal benefit at this scale.

**coalesce(1)** — output is written as a single CSV file for simplified HTTP serving. Trade-off: single writer is slower for very large datasets. For production, multiple partitions with a streaming API would be preferable.

---

## Partitioning and Parallelism

Files are read into Spark with automatic partitioning based on file size (128MB per partition via `spark.sql.files.maxPartitionBytes`). The regex transformation is applied as a lazy Spark transformation across all partitions simultaneously when an action (`.write()`) is triggered. Shuffle partitions are set to 8 rather than Spark's default of 200 to avoid creating many tiny files for typical dataset sizes.

---

## LLM Resilience

Three-tier fallback for regex generation:

1. **Redis cache** — identical prompts never re-hit the API (7-day TTL)
2. **Anthropic Claude API** — primary provider
3. **Google Gemini API** — automatic fallback if Anthropic fails

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs/` | Upload file + create job |
| `GET` | `/api/v1/jobs/` | List all jobs |
| `GET` | `/api/v1/jobs/{id}/` | Poll job status and progress |
| `POST` | `/api/v1/jobs/{id}/cancel/` | Cancel a running job |
| `GET` | `/api/v1/jobs/{id}/result/` | Paginated result rows |
| `GET` | `/api/v1/jobs/{id}/download/` | Download result as CSV |
| `DELETE` | `/api/v1/jobs/{id}/delete/` | Delete a job |
| `DELETE` | `/api/v1/jobs/bulk-delete/` | Bulk delete by status |

---

## Setup (Local Development)

### Prerequisites
- Docker + Docker Compose
- An Anthropic API key (console.anthropic.com)
- Optionally a Gemini API key (aistudio.google.com)

### Running Locally

**1. Clone the repo**
```bash
git clone https://github.com/ShatarupaB/llm-regex-patterns.git
cd llm-regex-patterns
```

**2. Create a `.env` file** in the root directory:
```env
DJANGO_SECRET_KEY=your-random-50-char-string
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_DEBUG=True

POSTGRES_DB=rhombus
POSTGRES_USER=rhombus
POSTGRES_PASSWORD=rhombus
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
REDIS_CACHE_URL=redis://redis:6379/1

ANTHROPIC_API_KEY=sk-ant-your-key-here
GEMINI_API_KEY=your-gemini-key-here

SPARK_MASTER_URL=local[*]
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

**3. Start all services**
```bash
docker-compose up --build
```

**4. Run migrations**
```bash
docker-compose exec web python manage.py migrate
```

**5. Open the app**
- Frontend: http://localhost:3000
- API: http://localhost:8000/api/v1/jobs/
- Celery monitor (Flower): http://localhost:5555

---

## Testing with Large Datasets

The demo uses a 10,000 row synthetic employee dataset generated with Python's Faker library, containing realistic names, emails, phone numbers, salaries and department information. The dataset intentionally includes some malformed entries (e.g. `invalid-email-123`) to demonstrate that the regex only replaces exact pattern matches, leaving non-matching values unchanged.

To generate your own test dataset:
```python
pip install faker
python generate_data.py
```

---

## Known Limitations

- **Semantic patterns**: Regex works best for structural patterns (emails, phone numbers, dates). Semantic patterns (first names, company names) may produce imprecise results — these require NLP rather than regex.
- **Excel files**: Large Excel files are converted via pandas before Spark processing. For very large Excel files, converting to CSV first is recommended.
- **Single output file**: Results use `coalesce(1)` for simplified serving. For datasets exceeding 10M rows, multiple output partitions with streaming would be more performant.
