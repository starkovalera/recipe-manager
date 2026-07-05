from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    NOTE_TOO_LONG = "NOTE_TOO_LONG"
    RECIPE_TOO_LONG = "RECIPE_TOO_LONG"
    NO_IMPORT_SOURCES = "NO_IMPORT_SOURCES"
    TOO_MANY_FILES = "TOO_MANY_FILES"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    ACTIVE_IMPORT_EXISTS = "ACTIVE_IMPORT_EXISTS"
    INVALID_INGREDIENT = "INVALID_INGREDIENT"
    IMPORT_NOT_FOUND = "IMPORT_NOT_FOUND"
    NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"
    RECIPE_NOT_FOUND = "RECIPE_NOT_FOUND"
    STORAGE_NOT_FOUND = "STORAGE_NOT_FOUND"
    TAG_NOT_FOUND = "TAG_NOT_FOUND"
    DUPLICATE_TAG = "DUPLICATE_TAG"
    TAG_LIMIT_EXCEEDED = "TAG_LIMIT_EXCEEDED"
    INVALID_TAG = "INVALID_TAG"
    FORBIDDEN = "FORBIDDEN"


class ApiError(Exception):
    status_code: int = 400
    error_code: ApiErrorCode | str | None = None
    message: str = "Request failed."
    extra: dict[str, Any] | None = None

    def __init__(
        self,
        error_code: ApiErrorCode | str | None = None,
        message: str | None = None,
        status_code: int | None = None,
        **extra: Any,
    ):
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        if error_code is not None:
            self.error_code = error_code
        if extra:
            self.extra = extra
        super().__init__(self.message)

    def _error_code_value(self) -> str | None:
        if isinstance(self.error_code, ApiErrorCode):
            return self.error_code.value
        return self.error_code

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"errorCode": self._error_code_value(), "message": self.message}
        if self.extra:
            result["extra"] = self.extra
        return result

    def __str__(self) -> str:
        return f"<[{self.status_code}] {self.__class__.__name__}>: {self.to_dict()}"


class ApiValidationError(ApiError):
    status_code = 400


class ApiNotFoundError(ApiError):
    status_code = 404


class ApiConflictError(ApiError):
    status_code = 409


class ForbiddenError(ApiError):
    status_code = 403
    error_code = ApiErrorCode.FORBIDDEN
    message = "Admin access is required."


class InvalidUrlError(ApiValidationError):
    error_code = ApiErrorCode.INVALID_URL
    message = "URL is not supported."


class TextTooLongError(ApiValidationError):
    error_code = ApiErrorCode.TEXT_TOO_LONG
    message = "Text input is too long."


class NoteTooLongError(ApiValidationError):
    error_code = ApiErrorCode.NOTE_TOO_LONG
    message = "Recipe note is too long."


class RecipeTooLongError(ApiValidationError):
    error_code = ApiErrorCode.RECIPE_TOO_LONG
    message = "Recipe is too long."


class NoImportSourcesError(ApiValidationError):
    error_code = ApiErrorCode.NO_IMPORT_SOURCES
    message = "Add a recipe URL, upload at least one recipe image, or add recipe text."


class TooManyFilesError(ApiValidationError):
    error_code = ApiErrorCode.TOO_MANY_FILES
    message = "Too many uploaded files."


class InvalidFileTypeError(ApiValidationError):
    error_code = ApiErrorCode.INVALID_FILE_TYPE
    message = "Upload JPEG, PNG, or WebP images."


class FileTooLargeError(ApiValidationError):
    error_code = ApiErrorCode.FILE_TOO_LARGE
    message = "Uploaded image is too large."


class ActiveImportExistsError(ApiValidationError):
    error_code = ApiErrorCode.ACTIVE_IMPORT_EXISTS
    message = "Too many active imports for this user."


class InvalidIngredientError(ApiValidationError):
    error_code = ApiErrorCode.INVALID_INGREDIENT
    message = "Ingredient name is required."


class InvalidTagError(ApiValidationError):
    error_code = ApiErrorCode.INVALID_TAG
    message = "Some tags are invalid."


class UnsupportedSourceStatusError(ApiValidationError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Unsupported source status."


class ImportNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.IMPORT_NOT_FOUND
    message = "Import job not found."


class NotificationNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.NOTIFICATION_NOT_FOUND
    message = "Notification not found."


class RecipeNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Recipe not found."


class CollectionNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Collection not found."


class CollectionRecipeNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Collection or recipe not found."


class IngredientNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Ingredient not found."


class CoverImageNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Cover image not found."


class ReviewFlagNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Review flag not found."


class RecipeResourceNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Recipe resource not found."


class StorageNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.STORAGE_NOT_FOUND
    message = "Media file not found."


class TagNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.TAG_NOT_FOUND
    message = "Tag not found."


class RecipeEmbeddingNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Recipe embedding not found."


class DuplicateTagError(ApiConflictError):
    error_code = ApiErrorCode.DUPLICATE_TAG
    message = "Tag already exists."


class CurrentCoverResourceDeleteError(ApiConflictError):
    error_code = ApiErrorCode.RECIPE_NOT_FOUND
    message = "Current cover resource cannot be deleted."


class TagLimitExceededError(ApiValidationError):
    error_code = ApiErrorCode.TAG_LIMIT_EXCEEDED
    message = "Tag limit exceeded."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
