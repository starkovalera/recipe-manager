import os
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest

# Automated tests use isolated dependency overrides and never require Clerk.
os.environ["APP_ENV"] = "TEST"

TEST_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "storage" / "test" / "uploads"


@pytest.fixture(scope="session", autouse=True)
def clean_shared_test_uploads() -> Generator[None, None, None]:
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    try:
        yield
    finally:
        shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
