# syntax=docker/dockerfile:1.10

# The target platform is deliberately constrained to the first-release artifact
# contract. Every caller must still pass --platform linux/amd64 explicitly.
ARG TARGETPLATFORM=linux/amd64

# Resolve these references with `docker buildx imagetools inspect` before
# changing them. The digest pins are part of the production packaging contract.
ARG PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.8.14-python3.12-bookworm-slim@sha256:b748a09ec61c993083278020a84e16f0c81485c5349b30c64dd29d6a22da7462
ARG LAMBDA_BASE_IMAGE=public.ecr.aws/lambda/python:3.12@sha256:9109e6ad351e8ff59a9a22d11f0d2ba4de60593e70a2370c7683f32edc4b0fa4

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_BASE_IMAGE} AS python-base

ARG TARGETPLATFORM
ARG TARGETARCH
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

RUN set -eux; \
    test "${TARGETPLATFORM}" = "linux/amd64"; \
    test "${TARGETARCH}" = "amd64"; \
    test -n "${SOURCE_REPOSITORY}"; \
    test "${#SOURCE_REVISION}" -eq 40; \
    test -n "${SOURCE_CREATED}"; \
    test -n "${IMAGE_VERSION}"; \
    test "${SOURCE_DATE_EPOCH}" -ge 0; \
    addgroup --gid 10001 recipe; \
    adduser --uid 10001 --gid 10001 --home /nonexistent --no-create-home \
      --shell /usr/sbin/nologin --disabled-password --gecos "" recipe; \
    chmod 1777 /tmp

ENV APP_ENV=PROD \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/recipe-manager/backend

FROM python-base AS python-dependencies

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
COPY backend/pyproject.toml backend/uv.lock ./

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python-base AS python-runtime

ARG PYTHON_BASE_IMAGE
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

COPY --from=python-dependencies /opt/recipe-manager/backend/.venv /opt/recipe-manager/backend/.venv
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini

ENV PATH="/opt/recipe-manager/backend/.venv/bin:${PATH}" \
    PYTHONPATH=/opt/recipe-manager/backend

LABEL org.opencontainers.image.source="${SOURCE_REPOSITORY}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.created="${SOURCE_CREATED}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.base.name="${PYTHON_BASE_IMAGE}" \
      com.recipe-manager.target-architecture="linux/amd64" \
      com.recipe-manager.source-date-epoch="${SOURCE_DATE_EPOCH}" \
      com.recipe-manager.packaging-contract="docker/production/v1"

USER recipe
CMD ["python", "--version"]

FROM ${LAMBDA_BASE_IMAGE} AS lambda-base

ARG TARGETPLATFORM
ARG TARGETARCH
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

RUN set -eux; \
    test "${TARGETPLATFORM}" = "linux/amd64"; \
    test "${TARGETARCH}" = "amd64"; \
    test -n "${SOURCE_REPOSITORY}"; \
    test "${#SOURCE_REVISION}" -eq 40; \
    test -n "${SOURCE_CREATED}"; \
    test -n "${IMAGE_VERSION}"; \
    test "${SOURCE_DATE_EPOCH}" -ge 0

FROM lambda-base AS lambda-dependencies

USER root
WORKDIR /opt/recipe-manager/lambda

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
COPY backend/pyproject.toml backend/uv.lock ./

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/recipe-manager/lambda/.venv

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM lambda-base AS lambda-runtime

ARG LAMBDA_BASE_IMAGE
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

COPY --from=lambda-dependencies /opt/recipe-manager/lambda/.venv /opt/recipe-manager/lambda/.venv
COPY backend/app /var/task/app

WORKDIR /var/task

ENV APP_ENV=PROD \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/var/task:/opt/recipe-manager/lambda/.venv/lib/python3.12/site-packages"

LABEL org.opencontainers.image.source="${SOURCE_REPOSITORY}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.created="${SOURCE_CREATED}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.base.name="${LAMBDA_BASE_IMAGE}" \
      com.recipe-manager.target-architecture="linux/amd64" \
      com.recipe-manager.source-date-epoch="${SOURCE_DATE_EPOCH}" \
      com.recipe-manager.packaging-contract="docker/production/v1"
