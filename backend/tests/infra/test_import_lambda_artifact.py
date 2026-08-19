import json
from pathlib import Path

from app.lambdas import imports as import_lambda

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOT = REPOSITORY_ROOT / "docker" / "production"
DOCKERFILE = PRODUCTION_ROOT / "Dockerfile"
FIXTURE_ROOT = PRODUCTION_ROOT / "fixtures" / "import-lambda"


def test_import_lambda_target_uses_shared_runtime_and_pinned_ffmpeg_source() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM ${FFMPEG_IMAGE} AS ffmpeg-source" in dockerfile
    assert "FROM lambda-runtime AS import-lambda-runtime" in dockerfile
    assert "mwader/static-ffmpeg:8.1.2-amd64@sha256:3bfa407c614a29a4535f1e3220fd9f6bc9cd7c25483036962e3c8ff711b56e01" in dockerfile
    assert "COPY --chmod=0555 --from=ffmpeg-source /ffmpeg /usr/local/bin/ffmpeg" in dockerfile
    assert "COPY --chmod=0555 --from=ffmpeg-source /ffprobe /usr/local/bin/ffprobe" in dockerfile
    assert "COPY --from=ffmpeg-source /versions.json /opt/recipe-manager/ffmpeg/versions.json" in dockerfile
    assert 'CMD ["app.lambdas.imports.handler"]' in dockerfile


def test_import_lambda_verifies_native_tools_without_adding_them_to_shared_runtime() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    shared_runtime, import_target = dockerfile.split("FROM ${FFMPEG_IMAGE} AS ffmpeg-source", maxsplit=1)

    assert "COPY --from=ffmpeg-source" not in shared_runtime
    assert "/usr/local/bin/ffmpeg" not in shared_runtime
    assert "/usr/local/bin/ffprobe" not in shared_runtime
    assert 'test -x /usr/local/bin/ffmpeg' in import_target
    assert 'test -x /usr/local/bin/ffprobe' in import_target
    assert '/usr/local/bin/ffmpeg -version' in import_target
    assert '/usr/local/bin/ffprobe -version' in import_target
    assert 'com.recipe-manager.artifact="recipe-manager-import"' in import_target
    assert 'com.recipe-manager.ffmpeg.provenance="/opt/recipe-manager/ffmpeg/versions.json"' in import_target


def test_import_lambda_fixtures_cover_valid_empty_and_addressable_partial_failure_batches() -> None:
    success = json.loads((FIXTURE_ROOT / "success.json").read_text(encoding="utf-8"))
    partial_failure = json.loads((FIXTURE_ROOT / "partial-failure.json").read_text(encoding="utf-8"))

    assert success == {"Records": []}
    assert partial_failure == {
        "Records": [
            {
                "messageId": "import-fixture-invalid-body",
                "body": "{}",
            }
        ]
    }
    assert import_lambda.handler(success, None) == {"batchItemFailures": []}
    assert import_lambda.handler(partial_failure, None) == {
        "batchItemFailures": [
            {"itemIdentifier": "import-fixture-invalid-body"},
        ]
    }
