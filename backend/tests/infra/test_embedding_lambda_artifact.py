import json
from pathlib import Path

from app.embeddings.constants import EmbeddingProcessingDisposition
from app.embeddings.outcomes import EmbeddingProcessingResult
from app.lambdas import embeddings as embedding_lambda

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOT = REPOSITORY_ROOT / "docker" / "production"
DOCKERFILE = PRODUCTION_ROOT / "embedding.Dockerfile"
FIXTURE = PRODUCTION_ROOT / "fixtures" / "embedding-sqs-event.json"


def _event() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_embedding_artifact_consumes_shared_runtime_and_sets_lambda_handler() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG PACKAGING_IMAGE" in dockerfile
    assert "FROM ${PACKAGING_IMAGE}" in dockerfile
    assert 'CMD ["app.lambdas.embeddings.handler"]' in dockerfile
    assert 'com.recipe-manager.artifact="recipe-manager-embedding"' in dockerfile
    assert 'test "${TARGETPLATFORM}" = "linux/amd64"' in dockerfile
    assert 'test "${TARGETARCH}" = "amd64"' in dockerfile
    assert 'test "${#SOURCE_REVISION}" -eq 40' in dockerfile
    assert "ffmpeg" not in dockerfile.lower()
    assert "ffprobe" not in dockerfile.lower()

    for label in (
        "org.opencontainers.image.source",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.created",
        "org.opencontainers.image.version",
        "com.recipe-manager.target-architecture",
        "com.recipe-manager.source-date-epoch",
        "com.recipe-manager.packaging-contract",
    ):
        assert label in dockerfile


def test_embedding_fixture_is_an_id_only_sqs_event() -> None:
    event = _event()
    records = event["Records"]

    assert set(event) == {"Records"}
    assert isinstance(records, list)
    assert [record["messageId"] for record in records] == [
        "embedding-success-1",
        "embedding-noop-1",
        "embedding-busy-1",
        "embedding-retryable-1",
        "embedding-malformed-1",
    ]

    assert [json.loads(record["body"]) for record in records[:4]] == [
        {"recipeId": "fixture-success"},
        {"recipeId": "fixture-noop"},
        {"recipeId": "fixture-busy"},
        {"recipeId": "fixture-retryable"},
    ]
    assert json.loads(records[4]["body"]) == {
        "recipeId": "fixture-malformed",
        "unexpected": "rejected",
    }


def test_embedding_fixture_covers_acknowledged_retryable_and_malformed_results(monkeypatch) -> None:
    dispositions = {
        "fixture-success": EmbeddingProcessingDisposition.SUCCEEDED,
        "fixture-noop": EmbeddingProcessingDisposition.NOOP,
        "fixture-busy": EmbeddingProcessingDisposition.BUSY,
        "fixture-retryable": EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
    }
    processed: list[str] = []

    def process(recipe_id: str) -> EmbeddingProcessingResult:
        processed.append(recipe_id)
        return EmbeddingProcessingResult(recipe_id=recipe_id, disposition=dispositions[recipe_id])

    monkeypatch.setattr(embedding_lambda, "process_recipe_embedding", process)

    assert embedding_lambda.handler(_event(), None) == {
        "batchItemFailures": [
            {"itemIdentifier": "embedding-busy-1"},
            {"itemIdentifier": "embedding-retryable-1"},
            {"itemIdentifier": "embedding-malformed-1"},
        ]
    }
    assert processed == [
        "fixture-success",
        "fixture-noop",
        "fixture-busy",
        "fixture-retryable",
    ]


def test_embedding_artifact_runbook_documents_build_invocation_and_scan_contract() -> None:
    readme = (PRODUCTION_ROOT / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "embedding.Dockerfile",
        "recipe-manager-embedding",
        "PACKAGING_IMAGE",
        "app.lambdas.embeddings.handler",
        "embedding-sqs-event.json",
        "2015-03-31/functions/function/invocations",
        "--read-only",
        "--tmpfs /tmp:rw",
        "linux/amd64",
        "RepoDigests",
        "trivy",
        "ffmpeg",
        "ffprobe",
    ):
        assert required_text in readme
