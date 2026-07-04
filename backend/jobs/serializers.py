"""
serializers.py — DRF serializers control what goes in and out of the API.

Separate serializers for create vs read because the shape of the request
(file + prompt) is very different from the shape of the response (status + progress).
"""

from rest_framework import serializers
from .models import Job


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/v1/jobs/ — accepts the file upload and job parameters.
    """
    # target_columns comes in as a comma-separated string from the form.
    # We store it as-is; the Celery task splits it.
    target_columns = serializers.CharField()

    class Meta:
        model = Job
        fields = [
            "upload_file",
            "original_filename",
            "nl_prompt",
            "target_columns",
            "replacement_value",
        ]


class JobStatusSerializer(serializers.ModelSerializer):
    """
    Used for GET /api/v1/jobs/{id}/ — the polling endpoint.
    Returns only what the frontend needs to render job state.
    Never returns the full result data (that's paginated separately).
    """
    class Meta:
        model = Job
        fields = [
            "id",
            "status",
            "progress",
            "error_message",
            "generated_regex",
            "result_row_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobListSerializer(serializers.ModelSerializer):
    """
    Used for GET /api/v1/jobs/ — lightweight list view.
    """
    class Meta:
        model = Job
        fields = [
            "id",
            "original_filename",
            "nl_prompt",
            "status",
            "progress",
            "created_at",
        ]
