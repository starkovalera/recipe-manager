# syntax=docker/dockerfile:1.10

# Build docker/production/Dockerfile --target lambda-runtime first and pass its
# source-specific local tag as PACKAGING_IMAGE. The shared target owns the
# digest-pinned AWS Lambda base and frozen production dependency installation.
ARG PACKAGING_IMAGE

FROM ${PACKAGING_IMAGE} AS embedding-runtime

ARG PACKAGING_IMAGE
ARG TARGETPLATFORM
ARG TARGETARCH
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

RUN set -eux; \
    test -n "${PACKAGING_IMAGE}"; \
    test "${TARGETPLATFORM}" = "linux/amd64"; \
    test "${TARGETARCH}" = "amd64"; \
    test -n "${SOURCE_REPOSITORY}"; \
    test "${#SOURCE_REVISION}" -eq 40; \
    test -n "${SOURCE_CREATED}"; \
    test -n "${IMAGE_VERSION}"; \
    test "${SOURCE_DATE_EPOCH}" -ge 0

LABEL org.opencontainers.image.source="${SOURCE_REPOSITORY}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.created="${SOURCE_CREATED}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      com.recipe-manager.target-architecture="linux/amd64" \
      com.recipe-manager.source-date-epoch="${SOURCE_DATE_EPOCH}" \
      com.recipe-manager.packaging-contract="docker/production/v1" \
      com.recipe-manager.artifact="recipe-manager-embedding"

# The AWS Lambda base image supplies the runtime interface entrypoint. Only the
# handler command is owned by this artifact child.
CMD ["app.lambdas.embeddings.handler"]
