# Shared production packaging contract

This directory owns the packaging seam for P12 artifact children. It builds
production-only Python dependencies once per runtime family and exposes two
named runtime targets:

| Target | Consumer | Contents |
| --- | --- | --- |
| `python-runtime` | Shared Python base | Python 3.12, application source, Alembic source, and the frozen production dependency set; runs as the named non-root `recipe` user |
| `api-runtime` | #42 FastAPI image | The shared Python runtime plus the production Uvicorn command, private port, health check, and API artifact identity |
| `lambda-runtime` | #43–#46 Lambda images | AWS Lambda Python 3.12 base, application source, and the frozen production dependency set; retains the base image's least-privilege runtime user and entrypoint |
| `maintenance-lambda-runtime` | #45 maintenance Lambda image | The shared Lambda runtime plus the operation-only maintenance handler; no native media tools |

The intermediate `python-dependencies` and `lambda-dependencies` targets are
build stages, not deployable artifacts. They install from exactly
`backend/pyproject.toml` and `backend/uv.lock` with `uv sync --frozen
--no-dev --no-install-project`. Development packages such as `pytest`, Ruff,
and `sqlite-web` are never installed into either runtime target.

## Build interface

Every artifact child must pass the same five source/build arguments:

| Argument | Required value |
| --- | --- |
| `SOURCE_REPOSITORY` | Canonical source repository URL, normally `https://github.com/starkovalera/recipe-manager` |
| `SOURCE_REVISION` | Full 40-character Git revision being built |
| `SOURCE_DATE_EPOCH` | Commit timestamp as a non-negative Unix epoch |
| `SOURCE_CREATED` | Commit timestamp in RFC 3339 form for `org.opencontainers.image.created` |
| `IMAGE_VERSION` | Immutable human-readable identity, normally `git-$SOURCE_REVISION` |

The runtime targets publish these OCI labels:

```text
org.opencontainers.image.source
org.opencontainers.image.revision
org.opencontainers.image.created
org.opencontainers.image.version
org.opencontainers.image.base.name
com.recipe-manager.target-architecture=linux/amd64
com.recipe-manager.source-date-epoch
com.recipe-manager.packaging-contract=docker/production/v1
```

The Dockerfile rejects a non-`linux/amd64` target at build time. Build commands
must still include `--platform linux/amd64`; never pass a platform list to a
P12 Lambda build, and do not publish a multi-architecture manifest for the
initial release.

The base references are pinned by digest in `Dockerfile`:

```text
python:3.12-slim-bookworm
ghcr.io/astral-sh/uv:0.8.14-python3.12-bookworm-slim
public.ecr.aws/lambda/python:3.12
```

Changing a digest is a packaging-contract change. Inspect the replacement
manifest, verify its `linux/amd64` variant, and rerun both runtime builds.

## Build from a clean checkout

Run from the repository root. The commands below build local base images; the
artifact children add their own final command/handler and metadata while
consuming the corresponding local tag.

PowerShell:

```powershell
$sourceRepository = "https://github.com/starkovalera/recipe-manager"
$sourceRevision = (git rev-parse HEAD).Trim()
$sourceDateEpoch = (git show -s --format=%ct HEAD).Trim()
$sourceCreated = (git show -s --format=%cI HEAD).Trim()
$imageVersion = "git-$sourceRevision"
$tag = "recipe-manager-python-runtime:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target python-runtime `
  --tag $tag `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion `
  .

$lambdaTag = "recipe-manager-lambda-runtime:$imageVersion"
docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target lambda-runtime `
  --tag $lambdaTag `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion `
  .
```

POSIX shell / CI:

```bash
SOURCE_REPOSITORY="https://github.com/starkovalera/recipe-manager"
SOURCE_REVISION="$(git rev-parse HEAD)"
SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
SOURCE_CREATED="$(git show -s --format=%cI HEAD)"
IMAGE_VERSION="git-${SOURCE_REVISION}"

docker buildx build --platform linux/amd64 --provenance=false --load \
  --file docker/production/Dockerfile \
  --target python-runtime \
  --tag "recipe-manager-python-runtime:${IMAGE_VERSION}" \
  --build-arg "SOURCE_REPOSITORY=${SOURCE_REPOSITORY}" \
  --build-arg "SOURCE_REVISION=${SOURCE_REVISION}" \
  --build-arg "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}" \
  --build-arg "SOURCE_CREATED=${SOURCE_CREATED}" \
  --build-arg "IMAGE_VERSION=${IMAGE_VERSION}" \
  .

docker buildx build --platform linux/amd64 --provenance=false --load \
  --file docker/production/Dockerfile \
  --target lambda-runtime \
  --tag "recipe-manager-lambda-runtime:${IMAGE_VERSION}" \
  --build-arg "SOURCE_REPOSITORY=${SOURCE_REPOSITORY}" \
  --build-arg "SOURCE_REVISION=${SOURCE_REVISION}" \
  --build-arg "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}" \
  --build-arg "SOURCE_CREATED=${SOURCE_CREATED}" \
  --build-arg "IMAGE_VERSION=${IMAGE_VERSION}" \
  .
```

`--load` is for local inspection. CI may use `--push` only in a separately
approved artifact-publication workflow; this issue does not add registry,
credentials, AWS, or deployment mutations.

## How artifact children consume the seam

The Python artifact children first build the relevant shared target with a
source-specific local tag, then use that tag as their `PACKAGING_IMAGE` base.
The shared labels and runtime filesystem defaults are inherited; the child adds
only its artifact-specific command and any artifact-specific labels.

FastAPI (#42) is the named `api-runtime` target in this Dockerfile. It owns the
production command while the release process owns the controlled migration:

```dockerfile
FROM python-runtime AS api-runtime
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

See [`host-unit.md`](host-unit.md) for the clean API and KrakenD builds, private
network deployment unit, health smoke, release manifest, and rollback contract.

Each Lambda child (#43–#46) follows the Lambda shape and sets its own handler:

```dockerfile
ARG PACKAGING_IMAGE
FROM ${PACKAGING_IMAGE}

CMD ["app.lambdas.imports.handler"]
```

The #45 maintenance artifact target is `maintenance-lambda-runtime`. It
inherits the shared read-only-root and `/tmp` assumptions, keeps the operation-
only `MaintenanceQueueMessage` boundary, and invokes
`app.lambdas.maintenance.handler`. Its deterministic fixture, runtime-contract
smoke, image inspection, digest, and scanner commands are documented in
[`maintenance-lambda.md`](maintenance-lambda.md).

The import child may add `ffmpeg`/`ffprobe`; those binaries are deliberately not
part of `lambda-runtime`. The gateway half of #42 starts from its own
digest-pinned KrakenD base, reapplies the same five metadata arguments/labels,
and does not inherit a Python runtime image. This keeps API, gateway, and every
Lambda independently addressable while preserving one source/build identity.

## Embedding Lambda artifact (#44)

The embedding child is a thin final image over the shared `lambda-runtime`
target. Build the shared target and the child from the same source revision;
`PACKAGING_IMAGE` must be the local full-SHA tag of that shared target. The
child sets `CMD ["app.lambdas.embeddings.handler"]`, does not install
dependencies, add AWS resources, or copy any fixture into the image.

PowerShell:

```powershell
$sourceRepository = "https://github.com/starkovalera/recipe-manager"
$sourceRevision = (git rev-parse HEAD).Trim()
$sourceDateEpoch = (git show -s --format=%ct HEAD).Trim()
$sourceCreated = (git show -s --format=%cI HEAD).Trim()
$imageVersion = "git-$sourceRevision"
$lambdaTag = "recipe-manager-lambda-runtime:$imageVersion"
$embeddingTag = "recipe-manager-embedding:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target lambda-runtime `
  --tag $lambdaTag `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion `
  .

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/embedding.Dockerfile `
  --tag $embeddingTag `
  --build-arg PACKAGING_IMAGE=$lambdaTag `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion `
  .
```

Inspect the final image identity and boundaries:

```powershell
docker image inspect $embeddingTag --format '{{json .Config.Labels}}'
docker image inspect $embeddingTag --format 'architecture={{.Architecture}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}}'
docker image inspect $embeddingTag --format 'content={{.Id}} RepoDigests={{join .RepoDigests "\n"}}'
docker run --rm --entrypoint /bin/sh $embeddingTag -c 'set -eu; ! command -v ffmpeg; ! command -v ffprobe; test ! -e /var/task/.env; test ! -e /var/task/backend/.env'
```

The expected tag is `recipe-manager-embedding:git-<full-sha>`. The content
digest from `docker image inspect` is the local identity; after publication,
record the registry `RepoDigests` value in the release manifest and deploy by
digest rather than by a mutable tag.

The AWS Lambda base image supplies the runtime interface entrypoint. Start the
image with a read-only root and writable `/tmp`, then invoke the runtime from a
second terminal with the deterministic SQS event fixture:

```powershell
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m `
  --publish 9000:8080 $embeddingTag

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:9000/2015-03-31/functions/function/invocations `
  -ContentType application/json `
  -InFile docker/production/fixtures/embedding-sqs-event.json
```

`embedding-sqs-event.json` contains only ID-only `recipeId` messages plus one
addressable malformed body. Its direct-handler verification maps the records to
the expected outcomes: `SUCCEEDED` and `NOOP` are acknowledged, `BUSY` and
`RETRYABLE_FAILURE` are returned as partial-batch failures, and the malformed
record is returned as a partial-batch failure without calling the processor.
Run that deterministic behavior check with:

```powershell
uv --directory backend run pytest tests/infra/test_embedding_lambda_artifact.py -q
```

The runtime request proves the container-to-Lambda handler wiring; the direct
fixture test avoids requiring a database, provider credentials, or AWS
resources. Use the exact scanner version selected by the artifact pipeline
(the initial local contract uses Trivy `0.63.0`) and fail on unresolved High or
Critical vulnerabilities or detected secrets:

```powershell
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock `
  aquasec/trivy:0.63.0 image --scanners vuln,secret `
  --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 $embeddingTag
```

Cross-artifact scanner pinning, manifest generation, and CI failure policy are
owned by #47. This child documents the image-specific command and boundaries;
it does not push to ECR or provision Lambda, SQS, IAM, or event-source mappings.

## Inspect the shared targets

```powershell
docker image inspect $tag --format '{{json .Config.Labels}}'
docker image inspect $tag --format 'architecture={{.Architecture}} user={{.Config.User}}'
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m $tag `
  python -c "import importlib.util; assert importlib.util.find_spec('pytest') is None; assert importlib.util.find_spec('ruff') is None; print('production dependency contract ok')"
```

For a Lambda child, the child Dockerfile must set the handler command, for
example `CMD ["app.lambdas.imports.handler"]`, and keep the inherited
`lambda-runtime` user, `/tmp` write boundary, and `PYTHONPATH`. The child must
also reapply the same metadata arguments/labels to its final image when its
base image is not one of these shared targets. #42 owns the pinned KrakenD
reference and gateway-specific final image; it consumes this metadata contract
but does not use the Python runtime target for KrakenD.

No `.env` file, provider credential, local database, test fixture, generated
media, ECR repository, IAM resource, Terraform file, or deployment mutation is
part of this seam.
