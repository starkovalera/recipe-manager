from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.imports.error_codes import (
    ImportExtractionErrorCode,
    ImportGeneralErrorCode,
    ImportProcessingErrorCode,
    ImportRecipeError,
)
from app.models import ImportJobErrorCode


class ImportErrorStage(StrEnum):
    INTERNAL = "INTERNAL"
    PROCESSING = "PROCESSING"
    EXTRACTION = "EXTRACTION"


@dataclass(frozen=True)
class ImportErrorPolicy:
    import_job_error_code: ImportJobErrorCode
    stage: ImportErrorStage
    automatic_retry: bool
    manual_retry: bool
    description: str


IMPORT_ERROR_POLICIES = {
    ImportGeneralErrorCode.UNEXPECTED_ERROR: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_FAILED,
        stage=ImportErrorStage.INTERNAL,
        automatic_retry=True,
        manual_retry=True,
        description="Unexpected import processing failure.",
    ),
    ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_PROCESSING_FAILED,
        stage=ImportErrorStage.PROCESSING,
        automatic_retry=True,
        manual_retry=True,
        description="Required secondary URL or video evidence could not be loaded.",
    ),
    ImportProcessingErrorCode.STALE_IMPORT_RECOVERY: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_PROCESSING_FAILED,
        stage=ImportErrorStage.PROCESSING,
        automatic_retry=True,
        manual_retry=True,
        description="A queued or running import was recovered after exceeding the stale-processing threshold.",
    ),
    ImportExtractionErrorCode.RESULT_PARSE_FAILED: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        stage=ImportErrorStage.EXTRACTION,
        automatic_retry=True,
        manual_retry=True,
        description="The extractor response could not be parsed.",
    ),
    ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        stage=ImportErrorStage.EXTRACTION,
        automatic_retry=True,
        manual_retry=True,
        description="The extractor response did not satisfy the recipe schema.",
    ),
    ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        stage=ImportErrorStage.EXTRACTION,
        automatic_retry=True,
        manual_retry=True,
        description="The extraction provider or its network path was unavailable.",
    ),
    ImportExtractionErrorCode.NOT_A_RECIPE: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        stage=ImportErrorStage.EXTRACTION,
        automatic_retry=False,
        manual_retry=True,
        description="The supplied evidence was not accepted as a recipe, including low confidence.",
    ),
    ImportExtractionErrorCode.RECIPE_TOO_LONG: ImportErrorPolicy(
        import_job_error_code=ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        stage=ImportErrorStage.EXTRACTION,
        automatic_retry=False,
        manual_retry=True,
        description="The extracted recipe exceeded configured size limits.",
    ),
}


@dataclass(frozen=True)
class ClassifiedImportError:
    detailed_code: str
    message: str
    extra: dict[str, Any]
    policy: ImportErrorPolicy


def classify_import_error(error: Exception | None) -> ClassifiedImportError:
    if isinstance(error, ImportRecipeError):
        policy = IMPORT_ERROR_POLICIES.get(error.code)
        if policy is not None:
            return ClassifiedImportError(
                detailed_code=error.code,
                message=error.message,
                extra=dict(error.extra or {}),
                policy=policy,
            )

    code = ImportGeneralErrorCode.UNEXPECTED_ERROR
    return ClassifiedImportError(
        detailed_code=code,
        message=ImportRecipeError.message,
        extra={},
        policy=IMPORT_ERROR_POLICIES[code],
    )


def render_import_error_policy_table() -> str:
    lines = [
        "| Detailed code | High-level code | Stage | Automatic SQS retry | Manual retry |",
        "|---|---|---|---:|---:|",
    ]
    for detailed_code, policy in IMPORT_ERROR_POLICIES.items():
        automatic_retry = "Yes" if policy.automatic_retry else "No"
        manual_retry = "Yes, while attempts remain" if policy.manual_retry else "No"
        lines.append(
            f"| `{detailed_code}` | `{policy.import_job_error_code.value}` | `{policy.stage.value}` | {automatic_retry} | {manual_retry} |"
        )
    return "\n".join(lines)
