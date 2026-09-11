"""Session-scoped app/client: the API loads the real ~32k-player world
on startup (~1s) — too slow to redo per test, and these tests exercise
the real dataset on purpose (see tests/conftest.py's `cfg`/`dossier_donnees`
for the equivalent unit-test convention).
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
