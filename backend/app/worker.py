"""Dramatiq worker entrypoint.

Run with:
    uv run dramatiq app.worker

Import task modules here so Dramatiq discovers registered actors.
"""

from app.core.dramatiq import broker
from app.embeddings import tasks as embedding_tasks
from app.imports import tasks as import_tasks
from app.users import tasks as user_tasks

__all__ = ["broker", "embedding_tasks", "import_tasks", "user_tasks"]
