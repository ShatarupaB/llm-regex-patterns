"""
views.py — REST API views for the jobs app.

Endpoints:
  POST   /api/v1/jobs/                → upload file + start job → returns job ID immediately
  GET    /api/v1/jobs/                → list all jobs
  GET    /api/v1/jobs/{id}/           → poll job status + progress
  POST   /api/v1/jobs/{id}/cancel/    → revoke a running Celery task
  GET    /api/v1/jobs/{id}/result/    → paginated result rows

Critical rule: views NEVER do any heavy work.
They validate input, create the DB row, dispatch a Celery task, and return.
Everything else happens in tasks.py.
"""

import os
import csv
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from celery.result import AsyncResult

from .models import Job
from .serializers import JobCreateSerializer, JobStatusSerializer, JobListSerializer
from .tasks import process_job


class JobListCreateView(APIView):
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        """List all jobs, most recent first."""
        jobs = Job.objects.all()
        return Response(JobListSerializer(jobs, many=True).data)

    def post(self, request):
        """
        Accepts multipart form data: file + job parameters.
        Creates the Job row, fires a Celery task, returns the job ID.
        The response is immediate — the client polls /jobs/{id}/ for updates.
        """
        serializer = JobCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Save the job in QUEUED state — Celery will update it to RUNNING.
        job = serializer.save(status=Job.Status.QUEUED)

        # Dispatch the background task.
        # .delay() is shorthand for .apply_async() with no options.
        # The task receives the job UUID (as string) — never the full object,
        # because Celery tasks are serialised as JSON and Django model instances
        # are not JSON-serialisable.
        task = process_job.delay(str(job.id))

        # Store the Celery task ID so we can poll/cancel it later.
        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])

        return Response(
            {"job_id": str(job.id), "status": job.status},
            status=status.HTTP_202_ACCEPTED,  # 202: accepted but not yet processed
        )


class JobDetailView(APIView):

    def get(self, request, job_id):
        """
        Polling endpoint. Returns DB state + live Celery state merged together.

        Why merge both?
        - DB state (status, progress) is updated by the task itself and persists.
        - Celery AsyncResult gives us live metadata (time_start, etc.) that isn't
          worth writing to Postgres on every progress tick.
        """
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        data = JobStatusSerializer(job).data

        # Enrich with live Celery metadata if we have a task ID.
        if job.celery_task_id:
            result = AsyncResult(job.celery_task_id)
            data["celery_state"] = result.state
            # result.info is a dict when the task called update_state(meta={...})
            if isinstance(result.info, dict):
                data["celery_meta"] = result.info

        return Response(data)


class JobCancelView(APIView):

    def post(self, request, job_id):
        """
        Revoke a Celery task and mark the job as CANCELLED.

        terminate=True sends SIGTERM to the worker process if the task is
        already running. Without it, revoke() only prevents future execution
        (won't stop a task already mid-flight).
        """
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        if job.status in (Job.Status.SUCCESS, Job.Status.FAILED, Job.Status.CANCELLED):
            return Response(
                {"error": f"Cannot cancel a job with status {job.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.celery_task_id:
            AsyncResult(job.celery_task_id).revoke(terminate=True, signal="SIGTERM")

        job.status = Job.Status.CANCELLED
        job.save(update_fields=["status", "updated_at"])

        return Response({"job_id": str(job.id), "status": job.status})


class JobResultView(APIView):
    """
    Returns the processed data in paginated form.
    We read the Spark-written CSV result file line-by-line — never load
    the full file into memory.
    """

    PAGE_SIZE = 100  # rows per page

    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        if job.status != Job.Status.SUCCESS:
            return Response(
                {"error": f"Job is not complete (status: {job.status})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result_abs_path = os.path.join(settings.MEDIA_ROOT, job.result_path)
        if not os.path.exists(result_abs_path):
            return Response({"error": "Result file not found"}, status=status.HTTP_404_NOT_FOUND)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", self.PAGE_SIZE))
        offset = (page - 1) * page_size

        rows = []
        headers = []

        # Stream the CSV — do not read it all into memory.
        with open(result_abs_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for i, row in enumerate(reader):
                if i < offset:
                    continue
                if i >= offset + page_size:
                    break
                rows.append(row)

        return Response({
            "page": page,
            "page_size": page_size,
            "total_rows": job.result_row_count,
            "headers": headers,
            "rows": rows,
        })


class JobDownloadView(APIView):
    """Streams the result CSV as a file download."""

    def get(self, request, job_id):
        import mimetypes
        from django.http import FileResponse

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        if job.status != Job.Status.SUCCESS:
            return Response({"error": "Job not complete"}, status=status.HTTP_400_BAD_REQUEST)

        result_abs_path = os.path.join(settings.MEDIA_ROOT, job.result_path)
        if not os.path.exists(result_abs_path):
            return Response({"error": "Result file not found"}, status=status.HTTP_404_NOT_FOUND)

        filename = f"rhombus_result_{str(job.id)[:8]}.csv"
        response = FileResponse(
            open(result_abs_path, 'rb'),
            content_type='text/csv',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class JobDeleteView(APIView):
    def delete(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobBulkDeleteView(APIView):
    """Delete all jobs matching a status filter. e.g. ?status=FAILED"""
    def delete(self, request):
        status_filter = request.query_params.get('status')
        if status_filter:
            deleted, _ = Job.objects.filter(status=status_filter).delete()
        else:
            deleted, _ = Job.objects.all().delete()
        return Response({"deleted": deleted})


class FileListView(APIView):
    """Lists all previously uploaded files with their metadata."""

    def get(self, request):
        import os
        from django.conf import settings

        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        files = []

        for root, dirs, filenames in os.walk(uploads_dir):
            for fname in filenames:
                if fname.startswith('.'):
                    continue
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, settings.MEDIA_ROOT)
                size = os.path.getsize(abs_path)
                modified = os.path.getmtime(abs_path)
                files.append({
                    'path': rel_path.replace('\\', '/'),
                    'name': fname,
                    'size_mb': round(size / 1024 / 1024, 2),
                    'modified': modified,
                })

        # Most recent first
        files.sort(key=lambda x: x['modified'], reverse=True)
        return Response(files)


class JobFromExistingFileView(APIView):
    """Create a job using an already-uploaded file path."""

    def post(self, request):
        import os
        from django.conf import settings

        file_path = request.data.get('file_path')
        nl_prompt = request.data.get('nl_prompt')
        target_columns = request.data.get('target_columns')
        replacement_value = request.data.get('replacement_value')

        if not all([file_path, nl_prompt, target_columns, replacement_value]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        abs_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if not os.path.exists(abs_path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        from jobs.tasks import process_job
        job = Job.objects.create(
            upload_file=file_path,
            original_filename=os.path.basename(file_path),
            nl_prompt=nl_prompt,
            target_columns=target_columns,
            replacement_value=replacement_value,
            status=Job.Status.QUEUED,
        )
        task = process_job.delay(str(job.id))
        job.celery_task_id = task.id
        job.save(update_fields=['celery_task_id'])

        return Response({'job_id': str(job.id), 'status': job.status}, status=status.HTTP_202_ACCEPTED)
