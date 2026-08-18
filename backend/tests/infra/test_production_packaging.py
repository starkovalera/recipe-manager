from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGING_ROOT = REPOSITORY_ROOT / "docker" / "production"
DOCKERFILE = PACKAGING_ROOT / "Dockerfile"
DOCKERIGNORE = REPOSITORY_ROOT / ".dockerignore"


def test_shared_packaging_exposes_locked_runtime_targets_and_pinned_bases():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "AS python-dependencies" in dockerfile
    assert "AS python-runtime" in dockerfile
    assert "AS lambda-dependencies" in dockerfile
    assert "AS lambda-runtime" in dockerfile
    assert "uv sync --frozen --no-dev --no-install-project" in dockerfile
    assert "python:3.12-slim-bookworm@sha256:" in dockerfile
    assert "ghcr.io/astral-sh/uv:0.8.14-python3.12-bookworm-slim@sha256:" in dockerfile
    assert "public.ecr.aws/lambda/python:3.12@sha256:" in dockerfile


def test_shared_packaging_enforces_architecture_and_release_metadata():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert 'test "${TARGETPLATFORM}" = "linux/amd64"' in dockerfile
    assert 'test "${TARGETARCH}" = "amd64"' in dockerfile
    assert 'test "${#SOURCE_REVISION}" -eq 40' in dockerfile
    for label in (
        "org.opencontainers.image.source",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.created",
        "org.opencontainers.image.version",
        "org.opencontainers.image.base.name",
    ):
        assert label in dockerfile


def test_production_build_context_excludes_secrets_and_development_state():
    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8")

    for pattern in ("**/.env*", "backend/tests", "backend/storage", "backend/config/*.local.toml"):
        assert pattern in dockerignore

    assert "frontend" in dockerignore
    assert "design" in dockerignore
    assert "docs" in dockerignore


def test_packaging_contract_documents_clean_build_and_inspection_commands():
    readme = (PACKAGING_ROOT / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "docker buildx build --platform linux/amd64",
        "SOURCE_REPOSITORY",
        "SOURCE_REVISION",
        "SOURCE_DATE_EPOCH",
        "IMAGE_VERSION",
        "--read-only",
        "PACKAGING_IMAGE",
        "multi-architecture manifest",
        "#42",
        "#43–#46",
    ):
        assert required_text in readme
