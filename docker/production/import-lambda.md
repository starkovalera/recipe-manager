# Import Lambda production artifact

The import artifact is the `import-lambda-runtime` target in
[`Dockerfile`](Dockerfile). It consumes the shared `lambda-runtime` target and
adds only the import handler plus the native media tools required by the P12
artifact contract.

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
$image = "recipe-manager-import:$imageVersion"

docker buildx build --platform linux/amd64 --provenance=false --load `
  --file docker/production/Dockerfile `
  --target import-lambda-runtime `
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
image's handler command is `app.lambdas.imports.handler` and is supplied to the
AWS Lambda runtime by the pinned Python 3.12 base image.

## Native media provenance and compatibility boundary

The image copies only `/ffmpeg`, `/ffprobe`, and `/versions.json` from
`mwader/static-ffmpeg:8.1.2-amd64@sha256:3bfa407c614a29a4535f1e3220fd9f6bc9cd7c25483036962e3c8ff711b56e01`.
The source image is pinned by digest, the version is recorded in the OCI
labels, and `/opt/recipe-manager/ffmpeg/versions.json` retains the upstream
build manifest. The Docker build executes both binaries with `-version` and
checks that they are executable.

`ffmpeg` and `ffprobe` are intentionally absent from the shared `lambda-runtime`
target and therefore are not inherited by the embedding, maintenance, or
account-deletion artifacts. The existing `ffmpeg_path` and `ffprobe_path`
settings remain an unused compatibility seam. This artifact does not add video
duration validation or invoke either binary from application code; that is a
separate approved behavior change.

Inspect the labels, architecture, entrypoint, and native-tool provenance:

```powershell
docker image inspect $image --format '{{json .Config.Labels}}'
docker image inspect $image --format 'architecture={{.Architecture}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}}'
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m --entrypoint /bin/sh $image -c 'ffmpeg -version && ffprobe -version && test -s /opt/recipe-manager/ffmpeg/versions.json'
```

The release manifest records the full-SHA tag, the pushed image digest, the
source revision, `linux/amd64`, and the verification result. After publication,
inspect the immutable registry digest with:

```powershell
docker buildx imagetools inspect <registry>/<repository>:git-<full-sha>
docker image inspect <registry>/<repository>@sha256:<image-digest> --format '{{json .RepoDigests}}'
```

## Deterministic Lambda runtime fixtures

The fixtures deliberately avoid database or provider state:

- `fixtures/import-lambda/success.json` is a valid empty SQS batch and must
  return `{"batchItemFailures": []}`;
- `fixtures/import-lambda/partial-failure.json` contains an addressable record
  with an invalid ID-only body and must return one failure for
  `import-fixture-invalid-body`.

Start the image in one terminal with the AWS Lambda Runtime Interface Emulator
provided by the AWS Python base image:

```powershell
docker run --rm --name recipe-manager-import-rie `
  -e APP_ENV=TEST `
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m `
  -p 9000:8080 $image
```

`APP_ENV=TEST` is deliberate: these fixtures exercise the runtime and SQS
partial-batch contract without production credentials or provider state. A
production invocation must supply the real locked settings through the
deployment environment instead.

Invoke each fixture from a second terminal:

```powershell
curl.exe -sS -X POST `
  http://127.0.0.1:9000/2015-03-31/functions/function/invocations `
  --data-binary '@docker/production/fixtures/import-lambda/success.json'

curl.exe -sS -X POST `
  http://127.0.0.1:9000/2015-03-31/functions/function/invocations `
  --data-binary '@docker/production/fixtures/import-lambda/partial-failure.json'
```

The RIE command verifies the Lambda runtime contract. The existing direct
handler tests remain the fast seam for all import dispositions and malformed
record behavior.

## Vulnerability and secret scan

Run the pinned scanner against the exact local image before publication:

```powershell
$scanDirectory = Join-Path $PWD.Path ".trivy-issue-43"
$scanArchive = Join-Path $scanDirectory "import.tar"
New-Item -ItemType Directory -Path $scanDirectory -Force | Out-Null

try {
  docker save --output $scanArchive $image
  docker run --rm `
    -v "${scanDirectory}:/workspace:ro" `
    aquasec/trivy:0.73.0@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c image `
    --input /workspace/import.tar `
    --scanners vuln,secret `
    --severity CRITICAL,HIGH `
    --exit-code 1 `
    --no-progress `
    --timeout 15m
} finally {
  Remove-Item -LiteralPath $scanDirectory -Recurse -Force
}
```

The archive is mounted read-only; the scanner does not receive the host
Docker socket. The initial release policy fails on unresolved Critical or
High findings and any detected secret.

The scanner version is fixed in this command; the completed cross-artifact CI
contract is documented in [`ci-verification.md`](ci-verification.md), including
the CI image digest, release manifest, and final scanner policy.
No application secret, `.env` file, provider credential, local database, or
generated media is part of the build context or image.
