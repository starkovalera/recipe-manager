import ast
from pathlib import Path

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

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
ERROR_POLICY_PATH = APP_ROOT / "imports" / "error_policy.py"
FAILURE_STAGE_PATH = APP_ROOT / "imports" / "job_stages" / "failure.py"
IMPORT_LAMBDA_PATH = APP_ROOT / "lambdas" / "imports.py"

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


def _assigned_name(node: ast.Assign | ast.AnnAssign) -> str | None:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    if len(targets) == 1 and isinstance(targets[0], ast.Name):
        return targets[0].id
    return None


def _referenced_policy_codes(node: ast.AST) -> set[str]:
    codes: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if child.value in IMPORT_ERROR_POLICIES:
                codes.add(child.value)
        elif isinstance(child, ast.Attribute) and child.attr in IMPORT_ERROR_POLICIES:
            codes.add(child.attr)
    return codes


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


def test_application_has_no_second_import_retry_code_collection() -> None:
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        if path == ERROR_POLICY_PATH:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign | ast.AnnAssign):
                continue
            name = _assigned_name(node)
            if name is None or not name.isupper() or "RETRY" not in name or "CODE" not in name:
                continue
            value = node.value
            if value is not None and len(_referenced_policy_codes(value)) >= 2:
                violations.append(f"{path.relative_to(APP_ROOT).as_posix()}: {name}")

    assert violations == [], "Duplicate import retry code collections found outside error_policy.py:\n" + "\n".join(violations)


def test_failure_stage_owns_automatic_retry_classification() -> None:
    failure_tree = ast.parse(FAILURE_STAGE_PATH.read_text(encoding="utf-8"))
    lambda_tree = ast.parse(IMPORT_LAMBDA_PATH.read_text(encoding="utf-8"))

    failure_calls = {node.func.id for node in ast.walk(failure_tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    lambda_names = {node.id for node in ast.walk(lambda_tree) if isinstance(node, ast.Name)}

    assert "classify_import_error" in failure_calls
    assert "classify_import_error" not in lambda_names


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
