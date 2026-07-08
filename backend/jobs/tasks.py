"""
tasks.py — Celery task definitions for the processing pipeline.

Pipeline stages:
  1. process_job (orchestrator) — called by the view, chains the stages below
  2. _validate_file             — check file is readable, extract column names
  3. _generate_regex            — call LLM (or cache hit) to get regex
  4. _run_spark_transform       — apply regex via PySpark, write result file

Why one orchestrating task instead of a Celery chain?
  A single task gives us one place to update progress and handle errors.
  Celery chains are elegant but harder to attach progress reporting to.
  At this scale, simplicity wins.
"""

import logging
import traceback

from celery import shared_task
from django.conf import settings

from jobs.models import Job
from llm.cache import get_cached_regex, set_cached_regex
from llm.client import generate_regex_from_prompt
from spark_jobs.transforms import run_replacement

logger = logging.getLogger(__name__)


def _update_progress(job: Job, task_self, pct: int, message: str = ""):
    """
    Helper: write progress to both Postgres and Celery's result backend.

    Postgres write: survives Redis restarts; needed for admin/monitoring.
    Celery update_state: picked up by AsyncResult on the polling endpoint.
    """
    job.progress = pct
    job.save(update_fields=["progress", "updated_at"])
    task_self.update_state(
        state="PROGRESS",
        meta={"progress": pct, "message": message},
    )


@shared_task(
    bind=True,                     # `self` gives access to task metadata (task.id, etc.)
    max_retries=3,
    default_retry_delay=30,        # seconds before retry (Celery will exponential-backoff)
    acks_late=True,                # acknowledge message AFTER the task completes, not before.
                                   # If the worker crashes mid-task, the message goes back
                                   # to the queue rather than being lost.
    reject_on_worker_lost=True,    # pairs with acks_late: re-queue on worker crash
)
def process_job(self, job_id: str):
    """
    Main pipeline task. Runs entirely inside the Celery worker.
    The Django web process never touches this code.
    """
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"process_job called with unknown job_id={job_id}")
        return

    try:
        # ── Stage 1: mark as running ──────────────────────────────────────
        job.status = Job.Status.RUNNING
        job.save(update_fields=["status", "updated_at"])
        _update_progress(job, self, 5, "Job started")

        # ── Stage 2: LLM → regex (with Redis cache) ───────────────────────
        _update_progress(job, self, 10, "Generating regex from prompt")

        cached = get_cached_regex(job.nl_prompt)
        if cached:
            logger.info(f"[Job {job_id}] Regex cache hit for prompt: {job.nl_prompt[:60]}")
            regex = cached
        else:
            logger.info(f"[Job {job_id}] Calling LLM for regex")
            regex = generate_regex_from_prompt(job.nl_prompt)
            set_cached_regex(job.nl_prompt, regex)

        job.generated_regex = regex
        job.save(update_fields=["generated_regex", "updated_at"])
        _update_progress(job, self, 25, f"Regex generated: {regex}")

        # ── Stage 3: PySpark transformation ──────────────────────────────
        _update_progress(job, self, 30, "Submitting Spark job")

        target_cols = [c.strip() for c in job.target_columns.split(",")]

        import time, os
        file_path = job.upload_file.path
        for _ in range(30):
            if os.path.exists(file_path):
                break
            time.sleep(1)

        result_path, row_count = run_replacement(
            upload_path=job.upload_file.path,
            target_columns=target_cols,
            regex_pattern=regex,
            replacement_value=job.replacement_value,
            job_id=job_id,
            progress_callback=lambda pct, msg: _update_progress(job, self, pct, msg),
        )

        # ── Stage 4: mark complete ────────────────────────────────────────
        job.result_path = result_path
        job.result_row_count = row_count
        job.status = Job.Status.SUCCESS
        job.progress = 100
        job.save(update_fields=["result_path", "result_row_count", "status", "progress", "updated_at"])
        _update_progress(job, self, 100, "Complete")

        logger.info(f"[Job {job_id}] Completed. {row_count} rows written to {result_path}")

    except Exception as exc:
        logger.exception(f"[Job {job_id}] Failed: {exc}")

        job.status = Job.Status.FAILED
        job.error_message = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"
        job.save(update_fields=["status", "error_message", "updated_at"])

        # Retry with exponential backoff.
        # countdown doubles each retry: 30s → 60s → 120s.
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
