import json
from pathlib import Path

from app.lambdas import account_deletion as account_deletion_lambda
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import AccountDeletionProcessingResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOT = REPOSITORY_ROOT / "docker" / "production"
DOCKERFILE = PRODUCTION_ROOT / "Dockerfile"
FIXTURE_ROOT = PRODUCTION_ROOT / "fixtures" / "account-deletion-lambda"


def _event(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _result(user_id: str, disposition: AccountDeletionProcessingDisposition) -> AccountDeletionProcessingResult:
    return AccountDeletionProcessingResult(
        user_id=user_id,
        disposition=disposition,
    )


def test_account_deletion_lambda_target_uses_shared_runtime_and_handler_command() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    target = dockerfile.split("FROM lambda-runtime AS account-deletion-lambda-runtime", maxsplit=1)[1]

    assert "FROM lambda-runtime AS account-deletion-lambda-runtime" in dockerfile
    assert 'CMD ["app.lambdas.account_deletion.handler"]' in target
    assert 'com.recipe-manager.artifact="recipe-manager-account-deletion"' in target
    assert 'test ! -e /usr/local/bin/ffmpeg' in target
    assert 'test ! -e /usr/local/bin/ffprobe' in target


def test_account_deletion_fixtures_cover_acknowledged_retryable_duplicate_and_malformed_records(monkeypatch) -> None:
    processed: list[str] = []
    dispositions = {
        "account-deletion-fixture-success": AccountDeletionProcessingDisposition.COMPLETED,
        "account-deletion-fixture-waiting": AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
        "account-deletion-fixture-retryable": AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
    }

    def process(user_id: str) -> AccountDeletionProcessingResult:
        processed.append(user_id)
        return _result(user_id, dispositions[user_id])

    monkeypatch.setattr(account_deletion_lambda, "process_account_deletion", process)

    assert account_deletion_lambda.handler(_event("success.json"), None) == {"batchItemFailures": []}
    assert account_deletion_lambda.handler(_event("waiting-for-imports.json"), None) == {
        "batchItemFailures": [{"itemIdentifier": "account-deletion-fixture-waiting"}]
    }
    assert account_deletion_lambda.handler(_event("retryable-failure.json"), None) == {
        "batchItemFailures": [{"itemIdentifier": "account-deletion-fixture-retryable"}]
    }

    duplicate_results = iter(
        (
            AccountDeletionProcessingDisposition.COMPLETED,
            AccountDeletionProcessingDisposition.NOOP,
        )
    )

    def process_duplicate(user_id: str) -> AccountDeletionProcessingResult:
        processed.append(user_id)
        return _result(user_id, next(duplicate_results))

    monkeypatch.setattr(account_deletion_lambda, "process_account_deletion", process_duplicate)
    assert account_deletion_lambda.handler(_event("duplicate-delivery.json"), None) == {"batchItemFailures": []}

    assert account_deletion_lambda.handler(_event("malformed-record.json"), None) == {
        "batchItemFailures": [{"itemIdentifier": "account-deletion-fixture-malformed"}]
    }
    assert processed == [
        "account-deletion-fixture-success",
        "account-deletion-fixture-waiting",
        "account-deletion-fixture-retryable",
        "account-deletion-fixture-duplicate",
        "account-deletion-fixture-duplicate",
    ]


def test_account_deletion_fixtures_keep_valid_messages_id_only() -> None:
    for filename in ("success.json", "waiting-for-imports.json", "retryable-failure.json", "duplicate-delivery.json"):
        event = _event(filename)
        assert set(event) == {"Records"}
        for record in event["Records"]:
            assert set(json.loads(record["body"])) == {"userId"}

    malformed = _event("malformed-record.json")
    assert json.loads(malformed["Records"][0]["body"]) == {
        "userId": "account-deletion-fixture-malformed",
        "unexpected": "rejected",
    }


def test_account_deletion_artifact_runbook_documents_build_invocation_and_scan_contract() -> None:
    runbook = (PRODUCTION_ROOT / "account-deletion-lambda.md").read_text(encoding="utf-8")

    for required_text in (
        "account-deletion-lambda-runtime",
        "recipe-manager-account-deletion",
        "app.lambdas.account_deletion.handler",
        "duplicate-delivery.json",
        "2015-03-31/functions/function/invocations",
        "-e APP_ENV=TEST",
        "--read-only",
        "--tmpfs /tmp:rw",
        "linux/amd64",
        "RepoDigests",
        "trivy",
        "ffmpeg",
        "ffprobe",
    ):
        assert required_text in runbook
