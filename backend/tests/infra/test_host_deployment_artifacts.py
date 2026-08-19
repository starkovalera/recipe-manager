from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ROOT = REPOSITORY_ROOT / "docker" / "production"
KRAKEND_ROOT = REPOSITORY_ROOT / "infra" / "krakend"


def _service_block(compose: str, service: str, next_service: str | None) -> str:
    start = compose.index(f"  {service}:\n")
    if next_service is None:
        return compose[start : compose.index("\nnetworks:\n", start)]
    return compose[start : compose.index(f"  {next_service}:\n", start)]


def test_api_artifact_uses_shared_runtime_and_owns_the_production_command():
    dockerfile = (PRODUCTION_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python-runtime AS api-runtime" in dockerfile
    assert 'com.recipe-manager.artifact="recipe-manager-api"' in dockerfile
    assert 'USER recipe\nCMD ["python", "--version"]' in dockerfile
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile
    assert "http://127.0.0.1:8000/health" in dockerfile
    assert "COPY backend/alembic ./alembic" in dockerfile
    assert "COPY backend/alembic.ini ./alembic.ini" in dockerfile


def test_krakend_artifact_is_pinned_labeled_and_validates_production_configuration():
    dockerfile = (KRAKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production_settings = (KRAKEND_ROOT / "config-production" / "settings.json").read_text(encoding="utf-8")

    assert "krakend:2.13.8@sha256:" in dockerfile
    assert 'test "${TARGETPLATFORM}" = "linux/amd64"' in dockerfile
    assert 'test "${#SOURCE_REVISION}" -eq 40' in dockerfile
    assert "FC_SETTINGS=/etc/krakend/config-production krakend check" in dockerfile
    assert 'com.recipe-manager.artifact="recipe-manager-krakend"' in dockerfile
    assert "USER krakend" in dockerfile
    assert '"upstream_host": "http://api:8000"' in production_settings


def test_local_gateway_check_supplies_non_release_metadata_through_compose():
    makefile = (REPOSITORY_ROOT / "Makefile").read_text(encoding="utf-8")
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "gateway-check:\n\tdocker compose build krakend" in makefile
    assert 'SOURCE_REVISION: "0000000000000000000000000000000000000000"' in compose
    assert "SOURCE_REPOSITORY: local-development" in compose


def test_host_unit_keeps_api_private_and_exposes_only_krakend():
    compose = (PRODUCTION_ROOT / "compose.yaml").read_text(encoding="utf-8")
    api = _service_block(compose, "api", "krakend")
    krakend = _service_block(compose, "krakend", "migration")
    migration = _service_block(compose, "migration", None)

    assert '    expose:\n      - "8000"' in api
    assert "    ports:" not in api
    assert "    ports:" in krakend
    assert "8080" in krakend
    assert "http://127.0.0.1:8080/__health" in krakend
    assert "FC_SETTINGS: /etc/krakend/config-production" in krakend
    assert 'profiles: ["release"]' in migration
    assert 'command: ["alembic", "upgrade", "head"]' in migration
    assert "volumes:" not in compose
    assert compose.count("    read_only: true") == 3
    assert compose.count("      - /tmp:rw,noexec,nosuid,size=64m") == 3


def test_host_unit_runbook_documents_release_identity_health_and_rollback():
    runbook = (PRODUCTION_ROOT / "host-unit.md").read_text(encoding="utf-8")

    for required_text in (
        "git-<full-sha>",
        "RepoDigests",
        "alembic upgrade head",
        "/__health",
        "/health",
        "release manifest",
        "previous digest",
        "does not downgrade the database",
        "No AWS, IAM, Terraform",
    ):
        assert required_text in runbook
