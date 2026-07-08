from typing import Any

from app.models import ImportJobErrorCode


# error codes
class ImportGeneralErrorCode:
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class ImportCreationErrorCode:
    RESOURCE_UPLOAD_FAILED = "RESOURCE_UPLOAD_FAILED"


class ImportProcessingErrorCode:
    SECONDARY_RESOURCE_UPLOADING_FAILED = "SECONDARY_RESOURCE_UPLOADING_FAILED"


class ImportExtractionErrorCode:
    # AI returned a response that could not be parsed as JSON.
    RESULT_PARSE_FAILED = "RESULT_PARSE_FAILED"
    # AI returned a recipe-shaped response that does not satisfy the schema.
    INVALID_EXTRACTION_RESULT = "INVALID_EXTRACTION_RESULT"
    # AI returned an explicit not-a-recipe marker.
    NOT_A_RECIPE = "NOT_A_RECIPE"
    EXTRACTOR_UNAVAILABLE = "EXTRACTOR_UNAVAILABLE"
    RECIPE_TOO_LONG = "RECIPE_TOO_LONG"


# base
class ImportRecipeError(Exception):
    """Base exception class for import errors"""

    code: str = ImportGeneralErrorCode.UNEXPECTED_ERROR
    import_job_code: ImportJobErrorCode = ImportJobErrorCode.IMPORT_FAILED
    message: str = "Import failed."
    extra: dict[str, Any] | None = None

    def __init__(
        self,
        code: str | None = None,
        import_job_code: ImportJobErrorCode | None = None,
        message: str | None = None,
        **extra: Any,
    ) -> None:
        if code is not None:
            self.code = code
        if import_job_code is not None:
            self.import_job_code = import_job_code
        if message is not None:
            self.message = message
        self.extra = extra or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "import_job_code": self.import_job_code.value,
            "message": self.message,
        }
        if self.extra:
            result["extra"] = self.extra
        return result

    def __str__(self) -> str:
        return f"<[{self.code} | {self.import_job_code.value}] {self.__class__.__name__}>: {self.to_dict()}"


# creation
class ImportCreationError(ImportRecipeError):
    import_job_code: ImportJobErrorCode = ImportJobErrorCode.IMPORT_CREATION_FAILED
    message: str = "Import creation failed."


class ResourceUploadError(ImportCreationError):
    code: str = ImportCreationErrorCode.RESOURCE_UPLOAD_FAILED
    message: str = "Import creation failed due to resource upload issue."


# processing
class ImportProcessingError(ImportRecipeError):
    import_job_code: ImportJobErrorCode = ImportJobErrorCode.IMPORT_PROCESSING_FAILED
    message: str = "Import processing failed."


class SecondaryResourceUploadError(ImportProcessingError):
    code: str = ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED
    message: str = "Import processing failed due to secondary resource uploading issue."


# extraction
class ImportExtractionError(ImportRecipeError):
    import_job_code: ImportJobErrorCode = ImportJobErrorCode.IMPORT_EXTRACTION_FAILED
    message: str = "Import extraction failed."


class ResultParseError(ImportExtractionError):
    code: str = ImportExtractionErrorCode.RESULT_PARSE_FAILED
    message: str = "Import extraction failed: extractor returned response that cannot be parsed."


class InvalidExtractionResult(ImportExtractionError):
    code: str = ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT
    message: str = "Import extraction failed: result didn't pass validation."


class NotARecipeError(ImportExtractionError):
    code: str = ImportExtractionErrorCode.NOT_A_RECIPE
    message: str = "Import extraction failed: not able to extract a recipe."


class ExtractorUnavailableError(ImportExtractionError):
    code: str = ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE
    message: str = "Import extraction failed: extractor unavailable."


class RecipeTooLongError(ImportExtractionError):
    code: str = ImportExtractionErrorCode.RECIPE_TOO_LONG
    message: str = "Import extraction failed: extracted recipe too long."
