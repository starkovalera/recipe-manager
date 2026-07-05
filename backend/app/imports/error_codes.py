from enum import Enum
from typing import Any


class ImportCreationErrorCode(str, Enum):
    RESOURCE_UPLOAD_FAILED = "RESOURCE_UPLOAD_FAILED"


class ImportProcessingErrorCode(str, Enum):
    SECONDARY_RESOURCE_UPLOADING_FAILED = "SECONDARY_RESOURCE_UPLOADING_FAILED"


class ImportExtractionErrorCode(str, Enum):
    # AI returned a response that could not be parsed as JSON.
    AI_PARSE_FAILED = "AI_PARSE_FAILED"
    # AI returned a recipe-shaped response that does not satisfy the schema.
    INVALID_EXTRACTION_RESULT = "INVALID_EXTRACTION_RESULT"
    # AI returned an explicit not-a-recipe marker.
    NOT_A_RECIPE = "NOT_A_RECIPE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    RECIPE_TOO_LONG = "RECIPE_TOO_LONG"


class ImportCreationError(Exception):
    def __init__(
        self,
        detail_code: ImportCreationErrorCode | None = None,
        diagnostic_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ):
        self.detail_code = detail_code
        self.diagnostic_message = diagnostic_message
        self.payload = payload or {}


class ImportProcessingError(Exception):
    def __init__(
        self,
        detail_code: ImportProcessingErrorCode | None = None,
        diagnostic_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ):
        self.detail_code = detail_code
        self.diagnostic_message = diagnostic_message
        self.payload = payload or {}


class ImportExtractionError(Exception):
    def __init__(
        self,
        detail_code: ImportExtractionErrorCode,
        diagnostic_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ):
        self.detail_code = detail_code
        self.diagnostic_message = diagnostic_message
        self.payload = payload or {}
