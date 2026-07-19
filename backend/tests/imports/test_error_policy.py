import pytest

from app.imports.error_codes import (
    ExtractorUnavailableError,
    ImportExtractionErrorCode,
    ImportGeneralErrorCode,
    ImportProcessingErrorCode,
    ImportRecipeError,
    InvalidExtractionResult,
    NotARecipeError,
    RecipeTooLongError,
    ResultParseError,
    SecondaryResourceUploadError,
)
from app.imports.error_policy import (
    IMPORT_ERROR_POLICIES,
    ImportErrorStage,
    classify_import_error,
    render_import_error_policy_table,
)
from app.models import ImportJobErrorCode

EXPECTED_CODES = {
    "UNEXPECTED_ERROR",
    "SECONDARY_RESOURCE_UPLOADING_FAILED",
    "RESULT_PARSE_FAILED",
    "INVALID_EXTRACTION_RESULT",
    "NOT_A_RECIPE",
    "EXTRACTOR_UNAVAILABLE",
    "RECIPE_TOO_LONG",
}
AUTOMATIC_RETRY_CODES = {
    "UNEXPECTED_ERROR",
    "SECONDARY_RESOURCE_UPLOADING_FAILED",
    "RESULT_PARSE_FAILED",
    "INVALID_EXTRACTION_RESULT",
    "EXTRACTOR_UNAVAILABLE",
}
NON_AUTOMATIC_RETRY_CODES = {
    "NOT_A_RECIPE",
    "RECIPE_TOO_LONG",
}
EXTRACTION_CODES = {
    "RESULT_PARSE_FAILED",
    "INVALID_EXTRACTION_RESULT",
    "NOT_A_RECIPE",
    "EXTRACTOR_UNAVAILABLE",
    "RECIPE_TOO_LONG",
}


def _declared_codes(constants_type: type) -> set[str]:
    return {value for name, value in vars(constants_type).items() if name.isupper() and isinstance(value, str)}


def test_registry_covers_every_declared_import_error_code() -> None:
    declared = (
        _declared_codes(ImportGeneralErrorCode) | _declared_codes(ImportProcessingErrorCode) | _declared_codes(ImportExtractionErrorCode)
    )

    assert declared == EXPECTED_CODES
    assert set(IMPORT_ERROR_POLICIES) == declared


def test_registry_defines_exact_automatic_retry_policy() -> None:
    automatic_retry_codes = {code for code, policy in IMPORT_ERROR_POLICIES.items() if policy.automatic_retry}
    non_automatic_retry_codes = {code for code, policy in IMPORT_ERROR_POLICIES.items() if not policy.automatic_retry}

    assert automatic_retry_codes == AUTOMATIC_RETRY_CODES
    assert non_automatic_retry_codes == NON_AUTOMATIC_RETRY_CODES
    assert all(policy.manual_retry for policy in IMPORT_ERROR_POLICIES.values())


def test_registry_defines_high_level_error_codes_and_stages() -> None:
    assert IMPORT_ERROR_POLICIES["UNEXPECTED_ERROR"].import_job_error_code is ImportJobErrorCode.IMPORT_FAILED
    assert IMPORT_ERROR_POLICIES["UNEXPECTED_ERROR"].stage is ImportErrorStage.INTERNAL
    assert IMPORT_ERROR_POLICIES["SECONDARY_RESOURCE_UPLOADING_FAILED"].import_job_error_code is ImportJobErrorCode.IMPORT_PROCESSING_FAILED
    assert IMPORT_ERROR_POLICIES["SECONDARY_RESOURCE_UPLOADING_FAILED"].stage is ImportErrorStage.PROCESSING

    for code in EXTRACTION_CODES:
        assert IMPORT_ERROR_POLICIES[code].import_job_error_code is ImportJobErrorCode.IMPORT_EXTRACTION_FAILED
        assert IMPORT_ERROR_POLICIES[code].stage is ImportErrorStage.EXTRACTION


@pytest.mark.parametrize(
    "error_type",
    [
        SecondaryResourceUploadError,
        ResultParseError,
        InvalidExtractionResult,
        NotARecipeError,
        ExtractorUnavailableError,
        RecipeTooLongError,
    ],
)
def test_exception_classes_match_registry_high_level_codes(error_type: type[ImportRecipeError]) -> None:
    policy = IMPORT_ERROR_POLICIES[error_type.code]

    assert policy.import_job_error_code is error_type.import_job_code


def test_classify_import_error_preserves_registered_domain_error() -> None:
    error = ExtractorUnavailableError(provider_message="private detail")

    classified = classify_import_error(error)

    assert classified.detailed_code == "EXTRACTOR_UNAVAILABLE"
    assert classified.message == ExtractorUnavailableError.message
    assert classified.extra == error.extra
    assert classified.policy.automatic_retry is True


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("secret or unstable detail"),
        ImportRecipeError(code="UNREGISTERED_IMPORT_ERROR", message="private detail"),
        None,
    ],
)
def test_classify_import_error_falls_back_to_stable_unexpected_error(error: Exception | None) -> None:
    classified = classify_import_error(error)

    assert classified.detailed_code == "UNEXPECTED_ERROR"
    assert classified.message == "Import failed."
    assert classified.extra == {}
    assert classified.policy is IMPORT_ERROR_POLICIES["UNEXPECTED_ERROR"]


def test_render_import_error_policy_table_uses_registry_order_and_values() -> None:
    table = render_import_error_policy_table()
    lines = table.splitlines()

    assert lines[:2] == [
        "| Detailed code | High-level code | Stage | Automatic SQS retry | Manual retry |",
        "|---|---|---|---:|---:|",
    ]
    assert [line.split("`")[1] for line in lines[2:]] == list(IMPORT_ERROR_POLICIES)
    assert lines[2] == ("| `UNEXPECTED_ERROR` | `IMPORT_FAILED` | `INTERNAL` | Yes | Yes, while attempts remain |")
    assert lines[-1] == ("| `RECIPE_TOO_LONG` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | No | Yes, while attempts remain |")
