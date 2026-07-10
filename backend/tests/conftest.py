"""Shared pytest fixtures/config.

Ensures /app/backend is on sys.path so tests can `import core.kernel`,
`import domains.registry`, etc. (backend/server.py runs from /app/backend
as cwd via supervisor, but pytest invoked from /app or elsewhere doesn't
automatically add /app/backend to sys.path since there's no package
__init__.py chain linking tests/ to the backend root).
"""
import os
import sys

from dotenv import load_dotenv

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

load_dotenv(os.path.join(BACKEND_ROOT, ".env"))
