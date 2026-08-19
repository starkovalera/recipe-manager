# Cross-artifact CI verification

Issue #47 closes P12 with one CI acceptance harness for all six production
images. The `production artifacts` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
runs after the existing backend and gateway jobs on every pull request and
every push to `main`; it has no path filter, so shared model, migration,
runtime-dependency, and gateway changes cannot bypass artifact verification.

The harness is [`scripts/ci/verify-production-artifacts.sh`](../../scripts/ci/verify-production-artifacts.sh).
It builds the API, KrakenD, import, embedding, maintenance, and
account-deletion images for `linux/amd64` with the frozen application lock,
then verifies:

- full-SHA tags and OCI source/artifact labels;
- local content digests, architecture, API/KrakenD runtime users, read-only
  root filesystems, writable `/tmp`, native-tool boundaries, and absence of
  embedded `.env` files;
- API and proxied KrakenD health through an isolated local Docker network;
- deterministic Runtime Interface Emulator invocations for all four Lambda
  handlers;
- vulnerability and secret findings with the pinned scanner image and a
  failing `HIGH,CRITICAL` threshold.

CI uploads `production-artifact-manifest/manifest.json`. The manifest maps
every artifact name and build target to its `git-<full-sha>` tag, local image
content digest, source revision, architecture, runtime user, and verification
results. These local content IDs are pre-publication evidence, not registry
`RepoDigests`; the later publication workflow must replace them with immutable
registry digests before deployment or rollback selection.

## Scanner policy

The scanner is Trivy `0.73.0`, pinned to OCI index digest
`sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c`.
It scans every final image for vulnerabilities and secrets, ignores findings
without an available fix, and fails on every other `HIGH` or `CRITICAL`
finding.

[`trivyignore.yaml`](trivyignore.yaml) contains the only accepted exceptions.
They are scoped to the Go binaries in the latest official KrakenD 2.13.8 and
AWS Lambda Python 3.12 amd64 images, are printed with `--show-suppressed`, and
expire on 2026-09-19. Expiry deliberately makes CI fail until the affected
official base digest is refreshed or the exception is reviewed. Application
dependencies do not receive upstream exceptions: the first full run found
fixed Pillow findings, so the production lock was upgraded from 12.2.0 to
12.3.0 instead.

## Local verification

On a Linux Docker host, or Git Bash with Docker Desktop on Windows, run from
the repository root:

```bash
bash scripts/ci/verify-production-artifacts.sh
```

The command creates only local images, containers, a Docker network, a
temporary scanner cache volume, inspection JSON, and the local manifest. Its
trap removes runtime containers, network, and cache volume. It never pushes an
image and requires no registry, AWS credential, Terraform, IAM, ECR, or
deployment access.
