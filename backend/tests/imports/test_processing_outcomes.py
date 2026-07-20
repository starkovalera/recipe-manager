from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult


def test_success_result_has_no_error_code() -> None:
    result = ImportProcessingResult(
        import_job_id="job-1",
        disposition=ImportProcessingDisposition.SUCCEEDED,
    )

    assert result.import_job_id == "job-1"
    assert result.detailed_error_code is None


def test_failure_result_keeps_stable_detailed_code() -> None:
    result = ImportProcessingResult(
        import_job_id="job-1",
        disposition=ImportProcessingDisposition.RETRYABLE_FAILURE,
        detailed_error_code="EXTRACTOR_UNAVAILABLE",
    )

    assert result.detailed_error_code == "EXTRACTOR_UNAVAILABLE"
