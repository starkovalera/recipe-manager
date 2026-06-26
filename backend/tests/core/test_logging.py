from io import StringIO
import logging

from app.core.logging import configure_logging


def test_configure_logging_overrides_existing_handlers():
    stream = StringIO()
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    try:
        root.handlers = [logging.NullHandler()]
        root.setLevel(logging.WARNING)

        configure_logging(stream=stream, force=True)
        logging.getLogger("app.main").info("[recipes.http] Request handled")

        assert "[recipes.http] Request handled" in stream.getvalue()
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
