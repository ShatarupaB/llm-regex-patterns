"""
models.py — Job is the single source of truth for a user's processing request.

Design decisions:
- One Job row = one end-to-end user action (upload → regex → replace → result).
- Status + progress are stored in Postgres (not just Redis) so they survive
  a Redis restart and can be queried by the admin panel.
- result_path stores a relative file path, not the file content — we never
  store millions of rows in Postgres.
- celery_task_id lets us call AsyncResult(job.celery_task_id) from any view
  to check live Celery state, and revoke() to cancel a running job.
"""

import uuid
from django.db import models


class Job(models.Model):

    class Status(models.TextChoices):
        QUEUED   = "QUEUED",   "Queued"
        RUNNING  = "RUNNING",  "Running"
        SUCCESS  = "SUCCESS",  "Success"
        FAILED   = "FAILED",   "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    # Use UUID as the primary key so job IDs are unguessable and safe to
    # expose to the frontend without leaking sequential row counts.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Input ──────────────────────────────────────────────────────────────
    # upload_file: Django stores the actual file; we store the relative path.
    upload_file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)

    # The user's natural-language description of what they want to find.
    nl_prompt = models.TextField()

    # The column(s) the user wants to apply the regex to.
    # Stored as comma-separated names for simplicity; could be JSONField.
    target_columns = models.CharField(max_length=500)

    # What matched text should be replaced with.
    replacement_value = models.CharField(max_length=500)

    # ── LLM output ─────────────────────────────────────────────────────────
    # The regex the LLM generated. Stored here for auditability —
    # users can see what pattern was actually applied to their data.
    generated_regex = models.CharField(max_length=2000, blank=True)

    # ── State ──────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,   # we frequently filter by status in admin/monitoring
    )

    # 0–100 integer. Updated by the Celery task via update_state().
    progress = models.PositiveSmallIntegerField(default=0)

    # If the task failed, store why — surfaces as an error message in the UI.
    error_message = models.TextField(blank=True)

    # Celery task ID — used to check live state and to revoke/cancel.
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # ── Output ─────────────────────────────────────────────────────────────
    # Relative path to the Spark-written output file (Parquet or CSV).
    # Never store file content in the DB — just the path.
    result_path = models.CharField(max_length=500, blank=True)

    # Row count after processing — useful to display in the UI.
    result_row_count = models.BigIntegerField(null=True, blank=True)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.id} [{self.status}] — {self.original_filename}"
