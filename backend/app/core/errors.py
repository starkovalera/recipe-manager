from enum import Enum

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    NOTE_TOO_LONG = "NOTE_TOO_LONG"
    RECIPE_TOO_LONG = "RECIPE_TOO_LONG"
    NOT_A_RECIPE = "NOT_A_RECIPE"
    TOO_MANY_FILES = "TOO_MANY_FILES"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    ACTIVE_IMPORT_EXISTS = "ACTIVE_IMPORT_EXISTS"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    INVALID_EXTRACTION_RESULT = "INVALID_EXTRACTION_RESULT"
    INVALID_INGREDIENT = "INVALID_INGREDIENT"
    MIXED_SOURCE_PLATFORMS = "MIXED_SOURCE_PLATFORMS"
    IMPORT_NOT_FOUND = "IMPORT_NOT_FOUND"
    NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"
    RECIPE_NOT_FOUND = "RECIPE_NOT_FOUND"
    STORAGE_NOT_FOUND = "STORAGE_NOT_FOUND"
    TAG_NOT_FOUND = "TAG_NOT_FOUND"
    DUPLICATE_TAG = "DUPLICATE_TAG"
    TAG_LIMIT_EXCEEDED = "TAG_LIMIT_EXCEEDED"
    INVALID_TAG = "INVALID_TAG"


class ApiError(Exception):
    def __init__(self, error_code: ErrorCode, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"errorCode": exc.error_code.value, "message": exc.message},
        )
