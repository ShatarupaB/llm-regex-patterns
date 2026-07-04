from django.urls import path
from .views import (
    JobListCreateView, JobDetailView, JobCancelView,
    JobResultView, JobDownloadView, JobDeleteView, JobBulkDeleteView
)

urlpatterns = [
    path("jobs/",                         JobListCreateView.as_view(),  name="job-list-create"),
    path("jobs/bulk-delete/",             JobBulkDeleteView.as_view(),  name="job-bulk-delete"),
    path("jobs/<uuid:job_id>/",           JobDetailView.as_view(),      name="job-detail"),
    path("jobs/<uuid:job_id>/cancel/",    JobCancelView.as_view(),      name="job-cancel"),
    path("jobs/<uuid:job_id>/result/",    JobResultView.as_view(),      name="job-result"),
    path("jobs/<uuid:job_id>/download/",  JobDownloadView.as_view(),    name="job-download"),
    path("jobs/<uuid:job_id>/delete/",    JobDeleteView.as_view(),      name="job-delete"),
]
