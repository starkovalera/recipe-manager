# Maintenance Lambda production artifact

The maintenance artifact is the `maintenance-lambda-runtime` target in
[`Dockerfile`](Dockerfile). It consumes the shared `lambda-runtime` target and
adds only the operation-only maintenance handler. It does not add `ffmpeg`,
`ffprobe`, application secrets, or AWS provisioning resources.

## Build

Build one immutable `linux/amd64` image for the full source revision. The
shared packaging arguments are required; the Dockerfile rejects missing or
short metadata values.

```powershell
$sourceRepository = "https://github.com/starkovalera/recipe-manager"
$sourceRevision = (git rev-parse HEAD).Trim()
$sourceDateEpoch = (git show -s --format=%ct HEAD).Trim()
$sourceCreated = (git show -s --format=%cI HEAD).Trim()
$imageVersion = "git-$sourceRevision"
$image = "recipe-manager-maintenance:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target maintenance-lambda-runtime `
  --tag $image `
  --build-arg SOURCE_REPOSITORY=$sourceRepository `
  --build-arg SOURCE_REVISION=$sourceRevision `
  --build-arg SOURCE_DATE_EPOCH=$sourceDateEpoch `
  --build-arg SOURCE_CREATED=$sourceCreated `
  --build-arg IMAGE_VERSION=$imageVersion `
  .
```

`--platform linux/amd64` and `--provenance=false` are required for the initial
Lambda artifact. Do not publish a multi-architecture manifest. The final
image's handler command is `app.lambdas.maintenance.handler` and is supplied
to the AWS Lambda runtime by the pinned Python 3.12 base image.

## Runtime and filesystem contract

The target inherits the digest-pinned `public.ecr.aws/lambda/python:3.12` base,
the frozen production dependency environment, the Lambda runtime entrypoint,
and the least-privilege base-image user. The shared Dockerfile rejects a
non-`linux/amd64` target and publishes the source revision, source timestamp,
image version, base image, and packaging-contract OCI labels. The child adds
`com.recipe-manager.artifact=recipe-manager-maintenance`.

The image contains no native media tools. Verify the metadata, handler command,
architecture, and read-only-root/`/tmp` boundary locally:

```powershell
docker image inspect $image --format '{{json .Config.Labels}}'
docker image inspect $image --format 'architecture={{.Architecture}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}}'
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m --entrypoint /bin/sh $image -c 'test -w /tmp && test ! -e /usr/local/bin/ffmpeg && test ! -e /usr/local/bin/ffprobe && python -c "from app.queueing.messages import MaintenanceQueueMessage; print(MaintenanceQueueMessage(operation=\"integrity_check\").model_dump_json())"'
```

The read-only check verifies the container filesystem assumption; it does not
replace a deployed Lambda test with real database, storage, queue, and IAM
configuration.

## Deterministic Lambda fixtures

The fixtures are intentionally free of database, storage, provider, and secret
state. The focused infra test overrides the dispatcher boundary with the
corresponding controlled result and verifies the handler's partial-batch
contract:

- `fixtures/maintenance-lambda/valid-operation.json` returns no failures for a
  completed operation;
- `fixtures/maintenance-lambda/retryable-failure.json` returns the retryable
  record's `messageId`;
- `fixtures/maintenance-lambda/anomaly-result.json` returns no failures for an
  anomaly disposition, because anomalies are reportable success;
- `fixtures/maintenance-lambda/malformed-record.json` returns the malformed
  record's `messageId`.

Run the deterministic fixture seam with:

```powershell
Push-Location backend
uv run pytest tests/infra/test_maintenance_lambda_artifact.py
Pop-Location
```

For a runtime-contract smoke, start the image with the AWS Lambda Runtime
Interface Emulator supplied by the base image and invoke the malformed fixture.
The existing maintenance module initializes its DB engine during import, so the
local smoke supplies only non-secret TEST settings and a SQLite path on the
`/tmp` tmpfs; it must return one addressable `batchItemFailures` entry:

```powershell
docker run --rm --name recipe-manager-maintenance-rie `
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m `
  -e APP_ENV=TEST -e DATABASE_URL=sqlite:////tmp/maintenance.db `
  -p 9000:8080 $image

curl.exe -sS -X POST `
  http://127.0.0.1:9000/2015-03-31/functions/function/invocations `
  --data-binary '@docker/production/fixtures/maintenance-lambda/malformed-record.json'
```

The RIE invocation verifies the image's Lambda entrypoint and response
serialization. The direct fixture test remains the deterministic seam for
completed, retryable, anomaly, and malformed outcomes because actual
maintenance operations intentionally depend on configured production services.

## Tag, digest, and vulnerability scan

The release manifest records the full-SHA tag, immutable image digest, source
revision, `linux/amd64`, and verification result. After publication, inspect
the registry digest with:

```powershell
docker buildx imagetools inspect <registry>/<repository>:git-<full-sha>
docker image inspect <registry>/<repository>@sha256:<image-digest> --format '{{json .RepoDigests}}'
```

Run the pinned scanner against the exact local image before publication. The
initial release policy fails on unresolved Critical or High findings and any
detected secret:

```powershell
docker run --rm `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -v ${PWD}:/workspace:ro `
  aquasec/trivy:0.73.0 image `
  --scanners vuln,secret `
  --severity CRITICAL,HIGH `
  --exit-code 1 `
  $image
```

No `.env` file, provider credential, local database, test storage, generated
media, ECR repository, IAM resource, Terraform file, or deployment mutation is
part of this build. Cross-artifact CI, release manifests, and the final scanner
policy remain owned by [#47](https://github.com/starkovalera/recipe-manager/issues/47).
