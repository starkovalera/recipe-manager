# Account-deletion Lambda production artifact

The account-deletion artifact is the `account-deletion-lambda-runtime` target in
[`Dockerfile`](Dockerfile). It consumes the shared `lambda-runtime` target and
adds only the ID-only account-deletion handler. It does not add `ffmpeg`,
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
$image = "recipe-manager-account-deletion:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target account-deletion-lambda-runtime `
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
image's handler command is `app.lambdas.account_deletion.handler` and is
supplied to the AWS Lambda runtime by the pinned Python 3.12 base image.

## Runtime and filesystem contract

The target inherits the digest-pinned `public.ecr.aws/lambda/python:3.12` base,
the frozen production dependency environment, the Lambda runtime entrypoint,
and the least-privilege base-image user. The shared Dockerfile rejects a
non-`linux/amd64` target and publishes the source revision, source timestamp,
image version, base image, and packaging-contract OCI labels. The child adds
`com.recipe-manager.artifact=recipe-manager-account-deletion`.

The image contains no native media tools. Verify metadata, the handler command,
architecture, and the read-only-root/`/tmp` boundary locally:

```powershell
docker image inspect $image --format '{{json .Config.Labels}}'
docker image inspect $image --format 'architecture={{.Architecture}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}}'
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m --entrypoint /bin/sh $image -c 'test -w /tmp && test ! -e /usr/local/bin/ffmpeg && test ! -e /usr/local/bin/ffprobe && python -c "from app.queueing.messages import AccountDeletionQueueMessage; print(AccountDeletionQueueMessage(userId=\"fixture-user\").model_dump_json())"'
```

The read-only check verifies the container filesystem assumption; it does not
replace a deployed Lambda test with real database, storage, Clerk, queue, and
IAM configuration.

## Deterministic Lambda fixtures

The fixtures are intentionally free of database, storage, provider, and secret
state. The focused infra test overrides the idempotent service boundary with
controlled results and verifies the handler's partial-batch contract:

- `fixtures/account-deletion-lambda/success.json` is acknowledged for a
  completed deletion;
- `waiting-for-imports.json` and `retryable-failure.json` return their
  addressable `messageId` values for retry;
- `duplicate-delivery.json` sends the same user ID twice; the first controlled
  result is `COMPLETED` and the idempotent duplicate is `NOOP`, so neither
  delivery is returned as a failure;
- `malformed-record.json` is rejected and its addressable `messageId` is
  returned without invoking the service.

Run the deterministic fixture seam with:

```powershell
Push-Location backend
uv run pytest tests/infra/test_account_deletion_lambda_artifact.py
Pop-Location
```

For a runtime-contract smoke, start the image with the AWS Lambda Runtime
Interface Emulator supplied by the base image and invoke the malformed fixture.
Set `APP_ENV=TEST` for this local no-service smoke: the handler's imported
database boundary eagerly validates settings, while the TEST profile uses the
repository's local SQLite/default-provider configuration and requires no
production secrets. The invocation must return one addressable
`batchItemFailures` entry:

```powershell
docker run --rm --name recipe-manager-account-deletion-rie `
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m `
  -e APP_ENV=TEST `
  -p 9000:8080 $image

curl.exe -sS -X POST `
  http://127.0.0.1:9000/2015-03-31/functions/function/invocations `
  --data-binary '@docker/production/fixtures/account-deletion-lambda/malformed-record.json'
```

The RIE invocation verifies the image's Lambda entrypoint and response
serialization. The direct fixture test remains the deterministic seam for
service outcomes because actual account deletion intentionally depends on
configured database, storage, Clerk, queue, and IAM boundaries.

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
  aquasec/trivy:0.73.0@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c image `
  --scanners vuln,secret `
  --severity CRITICAL,HIGH `
  --exit-code 1 `
  $image
```

No `.env` file, provider credential, local database, test storage, generated
media, ECR repository, IAM resource, Terraform file, or deployment mutation is
part of this build. Cross-artifact CI, release manifests, and the final scanner
policy are documented in [`ci-verification.md`](ci-verification.md).
