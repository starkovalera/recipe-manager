from io import StringIO
import logging

from app.core.logging import configure_logging, log_info


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


def test_log_info_prints_stdout_fallback(capsys):
    logger = logging.getLogger("app.test")

    log_info(logger, "[recipes.http] Request handled", path="/recipes", statusCode=200)

    output = capsys.readouterr().out
    assert "[recipes.http] Request handled" in output
    assert '"path": "/recipes"' in output
