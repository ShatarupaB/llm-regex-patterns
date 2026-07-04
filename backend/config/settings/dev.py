"""
dev.py — development overrides.

Only things that DIFFER from base.py live here.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]  # permissive in dev; locked down in prod.py

# Allow the Vite dev server to call Django without CORS rejections.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# In dev, also allow credentials (cookies) across origins.
CORS_ALLOW_CREDENTIALS = True

# Print emails to console instead of sending them.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# DRF: add BrowsableAPIRenderer in dev so you can hit endpoints in a browser.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
