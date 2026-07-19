from pathlib import Path

from app.imports.error_policy import render_import_error_policy_table

DOCUMENT_PATH = Path(__file__).resolve().parents[3] / "docs" / "import-error-handling.md"
TABLE_START = "<!-- IMPORT_ERROR_POLICY_TABLE:START -->"
TABLE_END = "<!-- IMPORT_ERROR_POLICY_TABLE:END -->"
REQUIRED_HEADINGS = {
    "# Import Error Handling and Retry Policy",
    "## Terminology",
    "## Stable error policy",
    "## Attempt limits",
    "## ImportJob state machine",
    "## Events and notifications",
    "## Artifact cleanup",
    "## Processing dispositions",
    "## Lambda partial-batch behavior",
    "## Message/infrastructure failures",
    "## Duplicate delivery and stale RUNNING jobs",
    "## Adding a new error code",
}


def test_import_error_policy_document_contains_every_required_section() -> None:
    document = DOCUMENT_PATH.read_text(encoding="utf-8")

    for heading in REQUIRED_HEADINGS:
        assert heading in document


def test_import_error_policy_document_table_matches_registry() -> None:
    document = DOCUMENT_PATH.read_text(encoding="utf-8")
    documented_table = document.split(TABLE_START, maxsplit=1)[1].split(TABLE_END, maxsplit=1)[0]

    assert documented_table.strip() == render_import_error_policy_table().strip()
