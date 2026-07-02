"""Dramatiq worker entrypoint.

Run with:
    uv run dramatiq app.worker

Import task modules here so Dramatiq discovers registered actors.
"""

from app.core.dramatiq import broker
from app.imports import tasks as import_tasks

__all__ = ["broker", "import_tasks"]
