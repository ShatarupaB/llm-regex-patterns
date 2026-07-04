"""
session.py — SparkSession factory.

Why a factory function instead of a module-level singleton?
  Celery workers can run multiple tasks. A module-level session would be shared
  across them and is hard to tear down cleanly. A factory lets each task
  get-or-create a session scoped to the worker process.

  In practice, `getOrCreate()` returns the existing session if one exists in
  the JVM process, so the factory pattern doesn't create redundant sessions —
  it just makes the lifecycle explicit.
"""

import logging
from django.conf import settings
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


def get_spark_session(app_name: str = "RhombusRegex") -> SparkSession:
    """
    Returns an existing SparkSession or creates a new one.

    SPARK_MASTER_URL from settings:
      - "local[*]"                → dev: use all CPU cores on the worker machine
      - "spark://spark-master:7077" → prod: connect to the docker-compose cluster

    Switching between them requires only an env var change — no code change.
    """
    master = getattr(settings, "SPARK_MASTER_URL", "local[*]")
    logger.info(f"Connecting to Spark master: {master}")

    session = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        # Keep shuffle partitions low for small-to-medium files.
        # Spark defaults to 200, which creates 200 tiny files for small datasets.
        # We set it to 8 (can be overridden per job) — tune upward for millions of rows.
        .config("spark.sql.shuffle.partitions", "8")
        # Write a single output file per job to simplify result reading.
        # Trade-off: single writer is slower for huge datasets, but simplifies
        # the result serving API. For production, write multiple partitions
        # and serve them as a stream.
        .config("spark.sql.files.maxPartitionBytes", "134217728")  # 128 MB
        .getOrCreate()
    )

    # Suppress verbose Spark logging in the Celery worker logs.
    session.sparkContext.setLogLevel("WARN")

    return session
