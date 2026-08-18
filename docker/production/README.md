# Shared production packaging contract

This directory owns the packaging seam for P12 artifact children. It builds
production-only Python dependencies once per runtime family and exposes two
named runtime targets:

| Target | Consumer | Contents |
| --- | --- | --- |
| `python-runtime` | #42 FastAPI image | Python 3.12, application source, Alembic source, and the frozen production dependency set; runs as the named non-root `recipe` user |
| `lambda-runtime` | #43–#46 Lambda images | AWS Lambda Python 3.12 base, application source, and the frozen production dependency set; retains the base image's least-privilege runtime user and entrypoint |

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

FastAPI (#42) follows this shape after it owns the controlled migration command:

```dockerfile
ARG PACKAGING_IMAGE
FROM ${PACKAGING_IMAGE}

USER recipe
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Each Lambda child (#43–#46) follows the Lambda shape and sets its own handler:

```dockerfile
ARG PACKAGING_IMAGE
FROM ${PACKAGING_IMAGE}

CMD ["app.lambdas.imports.handler"]
```

The import child may add `ffmpeg`/`ffprobe`; those binaries are deliberately not
part of `lambda-runtime`. The gateway half of #42 starts from its own
digest-pinned KrakenD base, reapplies the same five metadata arguments/labels,
and does not inherit a Python runtime image. This keeps API, gateway, and every
Lambda independently addressable while preserving one source/build identity.

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
