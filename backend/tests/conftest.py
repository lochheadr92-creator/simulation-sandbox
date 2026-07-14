"""Shared pytest fixtures/config.

Puts the backend root (the parent of this tests/ directory) on sys.path so
tests can `import core.kernel`, `import domains.registry`, etc., regardless
of where pytest is invoked from - the path is derived from this file's own
location, never hardcoded to any machine layout.

Loads backend/.env when present, then applies import-safety defaults for
MONGO_URL/DB_NAME: core/db.py reads both from os.environ at import time, so
without defaults a machine with no Mongo configuration cannot even COLLECT
the storage-backed test modules. Motor connects lazily, so no connection is
attempted here; tests that actually need Mongo or the HTTP API are marked
`integration` (registered in backend/pytest.ini) and skip or deselect
cleanly instead of erroring.
"""
import os
import sys

from dotenv import load_dotenv

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

load_dotenv(os.path.join(BACKEND_ROOT, ".env"))

# Import-safety defaults only: real values come from the environment or
# backend/.env (see backend/.env.example). These never override configured
# values and exist solely so collection succeeds on clean machines.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "simulation_sandbox_test")
