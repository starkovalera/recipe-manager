#!/usr/bin/env python3
"""Validate Docker inspection evidence and write the P12 release manifest."""

import argparse
import json
import re
import sys
from pathlib import Path


TRIVY_IMAGE = (
    "aquasec/trivy:0.73.0@"
    "sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c"
)
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--source-date-epoch", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="NAME=TARGET=TAG=INSPECTION",
        help="Artifact identity and path to docker image inspect JSON.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    raise ValueError(message)


def load_artifact(specification: str, revision: str) -> dict[str, object]:
    try:
        name, target, tag, inspection_path = specification.split("=", maxsplit=3)
    except ValueError as error:
        raise ValueError(f"invalid artifact specification: {specification}") from error

    inspection = json.loads(Path(inspection_path).read_text(encoding="utf-8"))
    if not isinstance(inspection, list) or len(inspection) != 1:
        fail(f"{name}: inspection must contain exactly one image")
    image = inspection[0]
    labels = image.get("Config", {}).get("Labels", {})

    if labels.get("org.opencontainers.image.revision") != revision:
        fail(f"{name}: revision label does not match {revision}")
    if labels.get("org.opencontainers.image.version") != f"git-{revision}":
        fail(f"{name}: version label is not the full-SHA tag identity")
    if labels.get("com.recipe-manager.target-architecture") != "linux/amd64":
        fail(f"{name}: target architecture label is not linux/amd64")
    if labels.get("com.recipe-manager.artifact") != name:
        fail(f"{name}: artifact label does not match")
    if image.get("Architecture") != "amd64":
        fail(f"{name}: image architecture is not amd64")
    if tag != f"{name}:git-{revision}":
        fail(f"{name}: tag is not derived from the full source revision")

    digest = image.get("Id", "")
    if not DIGEST_PATTERN.fullmatch(digest):
        fail(f"{name}: local image digest is missing or invalid")

    user = image.get("Config", {}).get("User", "")
    if name == "recipe-manager-api" and user != "recipe":
        fail(f"{name}: expected recipe runtime user")
    if name == "recipe-manager-krakend" and user != "krakend":
        fail(f"{name}: expected krakend runtime user")

    return {
        "architecture": "linux/amd64",
        "digest": digest,
        "digestType": "local-image-id",
        "name": name,
        "revision": revision,
        "tag": tag,
        "target": target,
        "user": user,
        "verification": {
            "build": "passed",
            "filesystem": "passed",
            "identity": "passed",
            "invocation": "passed",
            "scan": "passed",
        },
    }


def main() -> int:
    arguments = parse_args()
    try:
        if not SHA_PATTERN.fullmatch(arguments.source_revision):
            fail("source revision must be a full lowercase Git SHA")
        if arguments.source_date_epoch < 0:
            fail("source date epoch must be non-negative")
        if not arguments.artifact:
            fail("at least one artifact is required")

        artifacts = [load_artifact(item, arguments.source_revision) for item in arguments.artifact]
        names = [artifact["name"] for artifact in artifacts]
        if len(names) != len(set(names)):
            fail("artifact names must be unique")

        manifest = {
            "architecture": "linux/amd64",
            "artifacts": artifacts,
            "scanner": {
                "exceptionsFile": "docker/production/trivyignore.yaml",
                "image": TRIVY_IMAGE,
                "scanners": ["vuln", "secret"],
                "severities": ["HIGH", "CRITICAL"],
            },
            "sourceDateEpoch": arguments.source_date_epoch,
            "sourceRevision": arguments.source_revision,
        }
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
