"""
base.py — settings shared across ALL environments (dev, prod).

Pattern: base.py holds everything that doesn't change between environments.
dev.py and prod.py import from here and override only what differs.
This means you never have copy-pasted settings blocks that drift out of sync.
"""

import os
from pathlib import Path

# BASE_DIR resolves to: rhombus/backend/
# (three parents up from this file: settings/ → config/ → backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "INSECURE-dev-key-change-in-production")

# Apps split into three groups for clarity.
# This pattern makes it obvious what's Django core, what's third-party, and
# what's yours — useful when onboarding reviewers.
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local apps
    "jobs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must be before CommonMiddleware to intercept OPTIONS requests
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
# All env vars have sane defaults matching docker-compose.yml values so the
# app works out of the box after `cp .env.example .env`.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "rhombus"),
        "USER": os.environ.get("POSTGRES_USER", "rhombus"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "rhombus"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # reuse DB connections for 60s (reduces connection overhead)
    }
}

# ── Cache (Redis db/1) ────────────────────────────────────────────────────────
# We use a separate Redis database index (db/1) for the cache so that
# flushing the cache never touches Celery's broker/results (db/0).
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_CACHE_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 60 * 60 * 24,  # 24h default TTL; overridden per-call in llm/cache.py
    }
}

# ── Celery ────────────────────────────────────────────────────────────────────
# Redis db/0 is used for both broker AND result backend.
# Broker: holds the task queue (messages waiting to be picked up by workers).
# Result backend: stores task return values and state (QUEUED/RUNNING/SUCCESS/FAILED).
# Using the same Redis instance for both is fine at this scale; split them
# onto separate Redis instances if you need to scale broker throughput independently.

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# Store task start time in result backend — needed to compute elapsed time in the UI.
CELERY_TASK_TRACK_STARTED = True

# JSON serialisation: human-readable, language-agnostic, no pickle security risk.
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True'
# How long Celery keeps task results in Redis before expiring them.
# 24h is enough for a user to come back and download their result.
CELERY_RESULT_EXPIRES = 60 * 60 * 24

# Retry policy defaults — individual tasks can override these.
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # seconds
# Fixes the CPendingDeprecationWarning you see in celery_worker logs
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ── File upload limits ────────────────────────────────────────────────────────
# Default Django limit is 2.5MB — way too small for large CSVs.
# Setting FILE_UPLOAD_MAX_MEMORY_SIZE to 1MB means files larger than 1MB
# are automatically streamed to a temp file instead of held in memory.
# This is exactly what we want for large dataset uploads.
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB max request size
FILE_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024    # stream to disk after 1MB

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.MultiPartParser",  # for file uploads
        "rest_framework.parsers.JSONParser",
    ],
}

# ── Media files ───────────────────────────────────────────────────────────────
# Uploads and Spark output are written here.
# In docker-compose this path is a named volume shared between web + celery_worker.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Spark ─────────────────────────────────────────────────────────────────────
# Accessed in spark_jobs/session.py. Keeping it in settings means you can
# change the Spark master URL without touching application code.
SPARK_MASTER_URL = os.environ.get("SPARK_MASTER_URL", "local[*]")

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
