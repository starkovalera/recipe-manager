from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    NOTE_TOO_LONG = "NOTE_TOO_LONG"
    NO_IMPORT_SOURCES = "NO_IMPORT_SOURCES"
    TOO_MANY_FILES = "TOO_MANY_FILES"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    ACTIVE_IMPORT_EXISTS = "ACTIVE_IMPORT_EXISTS"
    IMPORT_CREATION_FAILED = "IMPORT_CREATION_FAILED"
    IMPORT_ATTEMPTS_EXHAUSTED = "IMPORT_ATTEMPTS_EXHAUSTED"
    IMPORT_NOT_RETRYABLE = "IMPORT_NOT_RETRYABLE"
    IMPORT_RETRY_FAILED = "IMPORT_RETRY_FAILED"
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
    ACCESS_USER_NOT_FOUND = "ACCESS_USER_NOT_FOUND"
    LAST_SUPERADMIN = "LAST_SUPERADMIN"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TRUSTED_IDENTITY = "INVALID_TRUSTED_IDENTITY"
    USER_NOT_PROVISIONED = "USER_NOT_PROVISIONED"
    AUTH_USER_LOOKUP_FAILED = "AUTH_USER_LOOKUP_FAILED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
    ACCOUNT_DELETION_PENDING = "ACCOUNT_DELETION_PENDING"
    ACCOUNT_DELETION_FAILED = "ACCOUNT_DELETION_FAILED"
    EMAIL_ALREADY_LINKED = "EMAIL_ALREADY_LINKED"


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


class ApiAuthenticationError(ApiError):
    status_code = 401


class ApiUpstreamError(ApiError):
    status_code = 502


class ForbiddenError(ApiError):
    status_code = 403
    error_code = ApiErrorCode.FORBIDDEN
    message = "Admin access is required."


class AccessUserNotFoundError(ApiNotFoundError):
    error_code = ApiErrorCode.ACCESS_USER_NOT_FOUND
    message = "User not found."


class LastSuperadminError(ApiConflictError):
    error_code = ApiErrorCode.LAST_SUPERADMIN
    message = "The last superadmin role cannot be removed."


class AuthenticationRequiredError(ApiAuthenticationError):
    error_code = ApiErrorCode.AUTHENTICATION_REQUIRED
    message = "Authentication is required."


class InvalidTrustedIdentityError(ApiAuthenticationError):
    error_code = ApiErrorCode.INVALID_TRUSTED_IDENTITY
    message = "Authenticated identity is invalid."


class UserNotProvisionedError(ApiConflictError):
    error_code = ApiErrorCode.USER_NOT_PROVISIONED
    message = "The authenticated user has not been provisioned."


class AuthUserLookupError(ApiUpstreamError):
    error_code = ApiErrorCode.AUTH_USER_LOOKUP_FAILED
    message = "Unable to resolve the authenticated user."


class AccountDeactivatedError(ForbiddenError):
    error_code = ApiErrorCode.ACCOUNT_DEACTIVATED
    message = "This account is deactivated."


class AccountDeletionPendingError(ForbiddenError):
    error_code = ApiErrorCode.ACCOUNT_DELETION_PENDING
    message = "Account deletion is in progress."


class AccountDeletionFailedError(ApiError):
    status_code = 500
    error_code = ApiErrorCode.ACCOUNT_DELETION_FAILED
    message = "Account deletion could not be started."


class EmailAlreadyLinkedError(ApiConflictError):
    error_code = ApiErrorCode.EMAIL_ALREADY_LINKED
    message = "This email is already linked to another account."


class InvalidUrlError(ApiValidationError):
    error_code = ApiErrorCode.INVALID_URL
    message = "URL is not supported."


class TextTooLongError(ApiValidationError):
    error_code = ApiErrorCode.TEXT_TOO_LONG
    message = "Text input is too long."


class NoteTooLongError(ApiValidationError):
    error_code = ApiErrorCode.NOTE_TOO_LONG
    message = "Recipe note is too long."


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


class ImportCreationError(ApiError):
    status_code = 500
    error_code = ApiErrorCode.IMPORT_CREATION_FAILED
    message = "Failed to create import. Please try again."


class ImportAttemptsExhaustedError(ApiConflictError):
    error_code = ApiErrorCode.IMPORT_ATTEMPTS_EXHAUSTED
    message = "Import retry attempts are exhausted."


class ImportNotRetryableError(ApiConflictError):
    error_code = ApiErrorCode.IMPORT_NOT_RETRYABLE
    message = "Import is not available for retry."


class ImportRetryFailedError(ApiError):
    status_code = 500
    error_code = ApiErrorCode.IMPORT_RETRY_FAILED
    message = "Failed to retry import. Please try again."


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
