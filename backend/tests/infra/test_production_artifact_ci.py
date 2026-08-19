import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
HARNESS = REPOSITORY_ROOT / "scripts" / "ci" / "verify-production-artifacts.sh"
MANIFEST_WRITER = REPOSITORY_ROOT / "scripts" / "ci" / "write-artifact-manifest.py"
TRIVY_IGNORE = REPOSITORY_ROOT / "docker" / "production" / "trivyignore.yaml"

ARTIFACTS = {
    "recipe-manager-api": "api-runtime",
    "recipe-manager-krakend": "krakend-runtime",
    "recipe-manager-import": "import-lambda-runtime",
    "recipe-manager-embedding": "embedding-runtime",
    "recipe-manager-maintenance": "maintenance-lambda-runtime",
    "recipe-manager-account-deletion": "account-deletion-lambda-runtime",
}


def test_ci_runs_the_cross_artifact_harness_after_backend_and_gateway_checks() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "production-artifacts:" in workflow
    assert "needs: [backend, gateway]" in workflow
    assert "docker/setup-buildx-action@" in workflow
    assert "scripts/ci/verify-production-artifacts.sh" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "production-artifact-manifest" in workflow
    assert "if-no-files-found: error" in workflow


def test_harness_builds_and_verifies_every_p12_artifact_with_one_pinned_policy() -> None:
    harness = HARNESS.read_text(encoding="utf-8")

    for artifact, target in ARTIFACTS.items():
        assert artifact in harness
        assert target in harness

    for required_text in (
        "--platform linux/amd64",
        "--provenance=false",
        "--read-only",
        "--tmpfs /tmp:rw,noexec,nosuid",
        "org.opencontainers.image.revision",
        "com.recipe-manager.artifact",
        "aquasec/trivy:0.73.0@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c",
        "--scanners vuln,secret",
        "--severity HIGH,CRITICAL",
        "--exit-code 1",
        "write-artifact-manifest.py",
    ):
        assert required_text in harness

    assert "docker build --platform linux/amd64 --provenance=false" in harness
    assert '--build-arg "PACKAGING_IMAGE=${LAMBDA_BASE_IMAGE}"' in harness


def test_upstream_scanner_exceptions_are_scoped_expiring_and_visible() -> None:
    policy = TRIVY_IGNORE.read_text(encoding="utf-8")
    harness = HARNESS.read_text(encoding="utf-8")

    for vulnerability in (
        "CVE-2026-56864",
        "CVE-2026-56865",
        "CVE-2026-46600",
        "CVE-2026-56852",
        "GHSA-hrxh-6v49-42gf",
        "CVE-2026-33818",
        "CVE-2026-39821",
        "CVE-2026-56853",
        "CVE-2026-56858",
        "CVE-2026-56859",
        "CVE-2026-56860",
        "CVE-2026-56862",
    ):
        assert vulnerability in policy

    assert policy.count('paths:\n      - "usr/bin/krakend"') == 12
    assert policy.count('paths:\n      - "usr/local/bin/aws-lambda-rie"') == 8
    assert policy.count("expired_at: 2026-09-19") == 20
    assert "latest official KrakenD 2.13.8 image" in policy
    assert "latest official AWS Lambda Python 3.12 amd64 image" in policy
    assert "--ignorefile /workspace/docker/production/trivyignore.yaml" in harness
    assert "--show-suppressed" in harness


def test_manifest_writer_rejects_mismatched_identity_and_records_verification(tmp_path: Path) -> None:
    revision = "a" * 40
    inspection = tmp_path / "api.json"
    inspection.write_text(
        json.dumps(
            [
                {
                    "Id": f"sha256:{'b' * 64}",
                    "Architecture": "amd64",
                    "Config": {
                        "User": "recipe",
                        "Labels": {
                            "org.opencontainers.image.revision": revision,
                            "org.opencontainers.image.version": f"git-{revision}",
                            "com.recipe-manager.target-architecture": "linux/amd64",
                            "com.recipe-manager.artifact": "recipe-manager-api",
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(MANIFEST_WRITER),
            "--source-revision",
            revision,
            "--source-date-epoch",
            "1724000000",
            "--output",
            str(output),
            "--artifact",
            f"recipe-manager-api=api-runtime=recipe-manager-api:git-{revision}={inspection}",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["sourceRevision"] == revision
    assert manifest["architecture"] == "linux/amd64"
    assert manifest["scanner"] == {
        "exceptionsFile": "docker/production/trivyignore.yaml",
        "image": "aquasec/trivy:0.73.0@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c",
        "scanners": ["vuln", "secret"],
        "severities": ["HIGH", "CRITICAL"],
    }
    assert manifest["artifacts"] == [
        {
            "architecture": "linux/amd64",
            "digest": f"sha256:{'b' * 64}",
            "digestType": "local-image-id",
            "name": "recipe-manager-api",
            "revision": revision,
            "tag": f"recipe-manager-api:git-{revision}",
            "target": "api-runtime",
            "user": "recipe",
            "verification": {
                "build": "passed",
                "filesystem": "passed",
                "identity": "passed",
                "invocation": "passed",
                "scan": "passed",
            },
        }
    ]

    bad = json.loads(inspection.read_text(encoding="utf-8"))
    bad[0]["Config"]["Labels"]["org.opencontainers.image.revision"] = "c" * 40
    inspection.write_text(json.dumps(bad), encoding="utf-8")
    rejected = subprocess.run(completed.args, capture_output=True, check=False, text=True)
    assert rejected.returncode != 0
    assert "revision label" in rejected.stderr
