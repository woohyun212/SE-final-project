"""Shared pytest configuration — sets env vars required at module import time.

``app.routers.auth`` raises ``RuntimeError`` if ``SECRET_KEY`` is unset (security
hardening per PR #66). Without this conftest, every test module that imports
``app.main`` or the auth router fails during collection.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
