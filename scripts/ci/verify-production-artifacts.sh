#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPOSITORY="https://github.com/starkovalera/recipe-manager"
SOURCE_REVISION="$(git rev-parse HEAD)"
SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
SOURCE_CREATED="$(git show -s --format=%cI HEAD)"
IMAGE_VERSION="git-${SOURCE_REVISION}"
TRIVY_IMAGE="aquasec/trivy:0.73.0@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c"
EVIDENCE_DIR="${RUNNER_TEMP:-.tmp}/production-artifacts"
HOST_WORKSPACE="${GITHUB_WORKSPACE:-${PWD}}"
NETWORK_NAME="recipe-manager-artifacts-${GITHUB_RUN_ID:-local}"
TRIVY_CACHE_VOLUME="recipe-manager-trivy-${GITHUB_RUN_ID:-local}"
RUNNING_CONTAINERS=()

mkdir -p "${EVIDENCE_DIR}/inspections"

cleanup() {
  if ((${#RUNNING_CONTAINERS[@]})); then
    docker rm --force "${RUNNING_CONTAINERS[@]}" >/dev/null 2>&1 || true
  fi
  docker network rm "${NETWORK_NAME}" >/dev/null 2>&1 || true
  docker volume rm "${TRIVY_CACHE_VOLUME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

build_arguments=(
  --build-arg "SOURCE_REPOSITORY=${SOURCE_REPOSITORY}"
  --build-arg "SOURCE_REVISION=${SOURCE_REVISION}"
  --build-arg "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}"
  --build-arg "SOURCE_CREATED=${SOURCE_CREATED}"
  --build-arg "IMAGE_VERSION=${IMAGE_VERSION}"
)

build_target() {
  local target="$1"
  local tag="$2"
  docker buildx build --platform linux/amd64 --provenance=false --load \
    --file docker/production/Dockerfile --target "${target}" --tag "${tag}" \
    "${build_arguments[@]}" .
}

API_IMAGE="recipe-manager-api:${IMAGE_VERSION}"
KRAKEND_IMAGE="recipe-manager-krakend:${IMAGE_VERSION}"
IMPORT_IMAGE="recipe-manager-import:${IMAGE_VERSION}"
EMBEDDING_IMAGE="recipe-manager-embedding:${IMAGE_VERSION}"
MAINTENANCE_IMAGE="recipe-manager-maintenance:${IMAGE_VERSION}"
ACCOUNT_DELETION_IMAGE="recipe-manager-account-deletion:${IMAGE_VERSION}"
LAMBDA_BASE_IMAGE="recipe-manager-lambda-runtime:${IMAGE_VERSION}"

build_target api-runtime "${API_IMAGE}"
build_target import-lambda-runtime "${IMPORT_IMAGE}"
build_target maintenance-lambda-runtime "${MAINTENANCE_IMAGE}"
build_target account-deletion-lambda-runtime "${ACCOUNT_DELETION_IMAGE}"
build_target lambda-runtime "${LAMBDA_BASE_IMAGE}"

docker build --platform linux/amd64 --provenance=false \
  --file docker/production/embedding.Dockerfile --target embedding-runtime \
  --tag "${EMBEDDING_IMAGE}" --build-arg "PACKAGING_IMAGE=${LAMBDA_BASE_IMAGE}" \
  "${build_arguments[@]}" .

docker buildx build --platform linux/amd64 --provenance=false --load \
  --file infra/krakend/Dockerfile --target krakend-runtime --tag "${KRAKEND_IMAGE}" \
  "${build_arguments[@]}" infra/krakend

declare -A TARGETS=(
  [recipe-manager-api]="api-runtime"
  [recipe-manager-krakend]="krakend-runtime"
  [recipe-manager-import]="import-lambda-runtime"
  [recipe-manager-embedding]="embedding-runtime"
  [recipe-manager-maintenance]="maintenance-lambda-runtime"
  [recipe-manager-account-deletion]="account-deletion-lambda-runtime"
)
declare -A IMAGES=(
  [recipe-manager-api]="${API_IMAGE}"
  [recipe-manager-krakend]="${KRAKEND_IMAGE}"
  [recipe-manager-import]="${IMPORT_IMAGE}"
  [recipe-manager-embedding]="${EMBEDDING_IMAGE}"
  [recipe-manager-maintenance]="${MAINTENANCE_IMAGE}"
  [recipe-manager-account-deletion]="${ACCOUNT_DELETION_IMAGE}"
)
ARTIFACT_ORDER=(
  recipe-manager-api recipe-manager-krakend recipe-manager-import
  recipe-manager-embedding recipe-manager-maintenance recipe-manager-account-deletion
)

for artifact in "${ARTIFACT_ORDER[@]}"; do
  image="${IMAGES[${artifact}]}"
  test "$(docker image inspect "${image}" --format '{{.Architecture}}')" = "amd64"
  test "$(docker image inspect "${image}" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" = "${SOURCE_REVISION}"
  test "$(docker image inspect "${image}" --format '{{index .Config.Labels "com.recipe-manager.artifact"}}')" = "${artifact}"
  docker image inspect "${image}" >"${EVIDENCE_DIR}/inspections/${artifact}.json"
done

test "$(docker image inspect "${API_IMAGE}" --format '{{.Config.User}}')" = "recipe"
test "$(docker image inspect "${KRAKEND_IMAGE}" --format '{{.Config.User}}')" = "krakend"

docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --entrypoint python "${API_IMAGE}" -c \
  "import importlib.util; assert importlib.util.find_spec('pytest') is None; assert importlib.util.find_spec('ruff') is None"

for image in "${EMBEDDING_IMAGE}" "${MAINTENANCE_IMAGE}" "${ACCOUNT_DELETION_IMAGE}"; do
  docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --entrypoint /bin/sh "${image}" -c \
    'test -w /tmp; test ! -e /usr/local/bin/ffmpeg; test ! -e /usr/local/bin/ffprobe; test ! -e /var/task/.env'
done
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=512m \
  --entrypoint /bin/sh "${IMPORT_IMAGE}" -c \
  'test -w /tmp; ffmpeg -version >/dev/null; ffprobe -version >/dev/null; test -s /opt/recipe-manager/ffmpeg/versions.json; test ! -e /var/task/.env'

docker network create "${NETWORK_NAME}" >/dev/null
docker run --detach --name recipe-manager-api-smoke --network "${NETWORK_NAME}" \
  --network-alias api \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  -e APP_ENV=TEST -e DATABASE_URL=sqlite:////tmp/api.db \
  -e UPLOAD_DIR=/tmp/uploads -e SYSTEM_ARTIFACTS_DIR=/tmp/system-artifacts \
  "${API_IMAGE}" >/dev/null
RUNNING_CONTAINERS+=(recipe-manager-api-smoke)

docker run --detach --name recipe-manager-krakend-smoke --network "${NETWORK_NAME}" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -p 18080:8080 \
  -e FC_ENABLE=1 -e FC_SETTINGS=/etc/krakend/config-production \
  -e FC_OUT=/tmp/krakend.generated.json \
  -e CLERK_ISSUER=https://example.clerk.accounts.dev \
  -e CLERK_JWKS_URL=https://example.clerk.accounts.dev/.well-known/jwks.json \
  "${KRAKEND_IMAGE}" >/dev/null
RUNNING_CONTAINERS+=(recipe-manager-krakend-smoke)

for attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:18080/__health >/dev/null && \
     curl --fail --silent http://127.0.0.1:18080/health >/dev/null; then
    break
  fi
  if ((attempt == 30)); then
    docker logs recipe-manager-api-smoke
    docker logs recipe-manager-krakend-smoke
    exit 1
  fi
  sleep 2
done

docker rm --force recipe-manager-krakend-smoke recipe-manager-api-smoke >/dev/null
RUNNING_CONTAINERS=()

invoke_lambda() {
  local name="$1"
  local image="$2"
  local fixture="$3"
  local expected="$4"
  docker run --detach --name "${name}" --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=512m -e APP_ENV=TEST -p 19000:8080 "${image}" >/dev/null
  RUNNING_CONTAINERS+=("${name}")
  for attempt in {1..20}; do
    if response="$(curl --fail --silent --request POST \
      http://127.0.0.1:19000/2015-03-31/functions/function/invocations \
      --data-binary "@${fixture}")"; then
      break
    fi
    if ((attempt == 20)); then
      docker logs "${name}"
      exit 1
    fi
    sleep 1
  done
  python - "${response}" "${expected}" <<'PY'
import json
import sys

actual = json.loads(sys.argv[1])
expected = json.loads(sys.argv[2])
if actual != expected:
    raise SystemExit(f"unexpected Lambda response: {actual!r} != {expected!r}")
PY
  docker rm --force "${name}" >/dev/null
  RUNNING_CONTAINERS=()
}

invoke_lambda recipe-manager-import-rie "${IMPORT_IMAGE}" \
  docker/production/fixtures/import-lambda/success.json '{"batchItemFailures":[]}'
invoke_lambda recipe-manager-embedding-rie "${EMBEDDING_IMAGE}" \
  docker/production/fixtures/embedding-runtime-smoke.json '{"batchItemFailures":[]}'
invoke_lambda recipe-manager-maintenance-rie "${MAINTENANCE_IMAGE}" \
  docker/production/fixtures/maintenance-lambda/malformed-record.json \
  '{"batchItemFailures":[{"itemIdentifier":"maintenance-fixture-malformed"}]}'
invoke_lambda recipe-manager-account-deletion-rie "${ACCOUNT_DELETION_IMAGE}" \
  docker/production/fixtures/account-deletion-lambda/malformed-record.json \
  '{"batchItemFailures":[{"itemIdentifier":"account-deletion-fixture-malformed"}]}'

docker volume create "${TRIVY_CACHE_VOLUME}" >/dev/null
for artifact in "${ARTIFACT_ORDER[@]}"; do
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${TRIVY_CACHE_VOLUME}:/root/.cache/trivy" \
    -v "${HOST_WORKSPACE}:/workspace:ro" \
    "${TRIVY_IMAGE}" image --scanners vuln,secret --severity HIGH,CRITICAL \
    --ignore-unfixed --ignorefile /workspace/docker/production/trivyignore.yaml \
    --show-suppressed --exit-code 1 --no-progress --timeout 15m "${IMAGES[${artifact}]}"
done

manifest_arguments=()
for artifact in "${ARTIFACT_ORDER[@]}"; do
  manifest_arguments+=(
    --artifact "${artifact}=${TARGETS[${artifact}]}=${IMAGES[${artifact}]}=${EVIDENCE_DIR}/inspections/${artifact}.json"
  )
done
python scripts/ci/write-artifact-manifest.py \
  --source-revision "${SOURCE_REVISION}" --source-date-epoch "${SOURCE_DATE_EPOCH}" \
  --output "${EVIDENCE_DIR}/manifest.json" "${manifest_arguments[@]}"
