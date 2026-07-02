import json
import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TextIO

SENSITIVE_KEYS = {"openai_api_key", "api_key", "authorization"}


@dataclass(frozen=True)
class BoundLogger:
    logger: logging.Logger
    context: Mapping[str, Any]

    def info(self, message: str, **meta: Any) -> None:
        log_info(self.logger, message, **self.context, **meta)

    def error(self, message: str, **meta: Any) -> None:
        log_error(self.logger, message, **self.context, **meta)


def bind_logger(logger: logging.Logger, **context: Any) -> BoundLogger:
    return BoundLogger(logger=logger, context=context)


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
    text = _format_log_message(message, meta)
    logger.info(text)
    _print_fallback("INFO", logger.name, text)


def log_error(logger: logging.Logger, message: str, **meta: Any) -> None:
    text = _format_log_message(message, meta)
    logger.error(text)
    _print_fallback("ERROR", logger.name, text)


def _format_log_message(message: str, meta: Mapping[str, Any]) -> str:
    if meta:
        return f"{message} {json.dumps(_safe_value(meta), sort_keys=True, ensure_ascii=False)}"
    return message


def _print_fallback(level: str, logger_name: str, text: str) -> None:
    enabled = os.environ.get("RECIPES_STDOUT_LOGS", "true").lower() not in {"0", "false", "no"}
    if not enabled:
        return
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    print(f"{timestamp} {level} {logger_name} {text}", file=sys.stdout, flush=True)


def configure_logging(stream: TextIO | None = None, force: bool | None = None) -> None:
    should_force = "PYTEST_CURRENT_TEST" not in os.environ if force is None else force
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=stream or sys.stdout,
        force=should_force,
    )
