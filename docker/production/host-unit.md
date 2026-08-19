# FastAPI and KrakenD production host unit

Issue #42 produces two independently buildable `linux/amd64` OCI images that
are released together:

- `recipe-manager-api` is the private FastAPI service on container port 8000;
- `recipe-manager-krakend` is the only public ingress and routes to
  `http://api:8000` over the Compose bridge network.

The host unit is [`compose.yaml`](compose.yaml). It publishes no FastAPI host
port, mounts no persistent application volume, runs both services with a
read-only root filesystem, and limits process writes to a tmpfs at `/tmp`.
The API image runs as `recipe`; the gateway retains the pinned base image's
`krakend` user. Runtime configuration and secrets stay in a host-owned API env
file or the process environment and never enter an image layer.

No AWS, IAM, Terraform, registry, DNS, certificate, or host-provisioning
resource is created by this unit. The final public 80/443 and TLS mechanism is
owned by #31/Phase 2; this host-neutral unit maps the configurable public HTTP
binding to KrakenD only.

## Build both images from a clean checkout

Run from the repository root. Use the exact commit timestamp so rebuilds carry
deterministic source metadata. The full-SHA discovery tag is
`git-<full-sha>`; never publish or deploy `latest`.

```powershell
$sourceRepository = "https://github.com/starkovalera/recipe-manager"
$sourceRevision = (git rev-parse HEAD).Trim()
$sourceDateEpoch = (git show -s --format=%ct HEAD).Trim()
$sourceCreated = (git show -s --format=%cI HEAD).Trim()
$imageVersion = "git-$sourceRevision"
$apiImage = "recipe-manager-api:$imageVersion"
$gatewayImage = "recipe-manager-krakend:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile --target api-runtime --tag $apiImage `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion .

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file infra/krakend/Dockerfile --tag $gatewayImage `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion infra/krakend
```

Both Dockerfiles reject a non-amd64 target, missing source identity, or a
non-full revision. The API consumes the shared frozen `uv.lock` packaging stage;
the KrakenD base is pinned to its `linux/amd64` manifest digest.

## Inspect and record immutable identity

```powershell
docker image inspect $apiImage --format '{{json .Config.Labels}}'
docker image inspect $gatewayImage --format '{{json .Config.Labels}}'
docker image inspect $apiImage --format '{{index .RepoDigests 0}}'
docker image inspect $gatewayImage --format '{{index .RepoDigests 0}}'
```

After registry publication in a separately approved workflow, record each
`RepoDigests` value in the release manifest with artifact name, source revision,
architecture, and verification result. Production uses the immutable digest;
the `git-<full-sha>` tag is only a discovery and audit reference.

## Controlled migration and startup

Set `API_IMAGE` and `KRAKEND_IMAGE` to the two matching tags or digests and set
`API_ENV_FILE` to the host-owned production settings file. The same API image
contains Alembic and is the only migration artifact. FastAPI production startup
does not run migrations.

Run exactly one controlled release migration before starting or replacing the
service unit:

```powershell
docker compose --file docker/production/compose.yaml --profile release run --rm migration alembic upgrade head
docker compose --file docker/production/compose.yaml up -d api krakend
```

For a risky migration or backfill, verify the required Neon snapshot first.
Application startup is never the migration owner.

## Health and private-network checks

```powershell
curl.exe http://127.0.0.1:80/__health
curl.exe http://127.0.0.1:80/health
docker compose --file docker/production/compose.yaml ps
```

`/__health` verifies KrakenD itself. `/health` passes through KrakenD to the
private FastAPI service. `docker compose ps` must show both health checks as
healthy. Confirm that the rendered host port list contains KrakenD only; the API
must remain reachable only as `api:8000` on the service network.

## Rollback reference

Retain the previous API and KrakenD digests in the release manifest. Rollback
sets `API_IMAGE` and `KRAKEND_IMAGE` to the compatible previous digest pair and
recreates the host unit. Image rollback does not downgrade the database. A
schema-incompatible release requires its separately reviewed restore or
forward-fix procedure; never run an automatic Alembic downgrade.
