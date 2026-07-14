"""Lazy environment resolution for HTTP integration tests.

Doctrine: never resolve service endpoints at module import time, and never
use machine-absolute paths. The backend base URL comes from, in order:

1. the ``REACT_APP_BACKEND_URL`` environment variable,
2. ``frontend/.env`` located relative to the repo root (derived from this
   file's own location - works on any checkout, any OS),
3. otherwise ``None`` - callers must skip, never fail at collection.
"""
import os

# .../<repo>/backend/tests/helpers/env.py -> four dirname hops to <repo>
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

SKIP_REASON = "backend URL not configured - set REACT_APP_BACKEND_URL"


def resolve_backend_base_url():
    """Return the backend base URL without a trailing slash, or None."""
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if url and url.strip():
        return url.strip().rstrip("/")
    env_path = os.path.join(_REPO_ROOT, "frontend", ".env")
    try:
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("REACT_APP_BACKEND_URL="):
                    value = stripped.split("=", 1)[1].strip()
                    if value:
                        return value.rstrip("/")
    except OSError:
        return None
    return None
