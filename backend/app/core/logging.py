import json
import logging
import os
import sys
from collections.abc import Mapping
from typing import TextIO
from typing import Any


SENSITIVE_KEYS = {"dataUrl", "data_url", "bytes", "content", "openai_api_key", "api_key", "authorization"}


def _safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe_value(nested) for key, nested in value.items() if str(key) not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_value(item) for item in value]
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    text = str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
    if isinstance(text, str) and (text.startswith("data:image") or "base64," in text):
        return "<redacted>"
    return text


def log_info(logger: logging.Logger, message: str, **meta: Any) -> None:
    if meta:
        logger.info("%s %s", message, json.dumps(_safe_value(meta), sort_keys=True, ensure_ascii=False))
    else:
        logger.info(message)


def log_error(logger: logging.Logger, message: str, **meta: Any) -> None:
    if meta:
        logger.error("%s %s", message, json.dumps(_safe_value(meta), sort_keys=True, ensure_ascii=False))
    else:
        logger.error(message)


def configure_logging(stream: TextIO | None = None, force: bool | None = None) -> None:
    should_force = "PYTEST_CURRENT_TEST" not in os.environ if force is None else force
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=stream or sys.stdout,
        force=should_force,
    )
