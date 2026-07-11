import os

# Tests exercise the explicit no-auth local mode. Dedicated route tests create
# secure Settings instances to verify production token enforcement.
os.environ.setdefault("AI_LOCAL_DEV_MODE", "true")
os.environ.setdefault("AI_ALLOWED_IMAGE_HOSTS", "example.com,*.objects.example.edu")
