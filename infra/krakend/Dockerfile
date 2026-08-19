ARG KRAKEND_BASE_IMAGE=krakend:2.13.8@sha256:e8a4470820405ea728ffd1fd79ce4e6320966fa8c0b7a6e23e3ec822e8b4f62f

FROM ${KRAKEND_BASE_IMAGE} AS validator

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

ENV FC_ENABLE=1 \
    FC_SETTINGS=/etc/krakend/config \
    FC_OUT=/tmp/krakend.generated.json \
    CLERK_ISSUER=https://example.clerk.accounts.dev \
    CLERK_JWKS_URL=https://example.clerk.accounts.dev/.well-known/jwks.json
COPY krakend.tmpl /etc/krakend/krakend.tmpl
COPY config /etc/krakend/config
COPY config/auth.json config/endpoints.json config-production/settings.json /etc/krakend/config-production/
RUN krakend check -tnd -c /etc/krakend/krakend.tmpl; \
    FC_SETTINGS=/etc/krakend/config-production krakend check -tnd -c /etc/krakend/krakend.tmpl

FROM ${KRAKEND_BASE_IMAGE}

ARG KRAKEND_BASE_IMAGE
ARG SOURCE_REPOSITORY
ARG SOURCE_REVISION
ARG SOURCE_DATE_EPOCH
ARG SOURCE_CREATED
ARG IMAGE_VERSION

ENV FC_ENABLE=1 \
    FC_SETTINGS=/etc/krakend/config \
    FC_OUT=/tmp/krakend.generated.json
COPY --from=validator --chown=krakend:nogroup /etc/krakend /etc/krakend
COPY --chmod=755 --chown=krakend:nogroup entrypoint.sh /usr/local/bin/recipe-manager-krakend-entrypoint

LABEL org.opencontainers.image.source="${SOURCE_REPOSITORY}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.created="${SOURCE_CREATED}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.base.name="${KRAKEND_BASE_IMAGE}" \
      com.recipe-manager.target-architecture="linux/amd64" \
      com.recipe-manager.source-date-epoch="${SOURCE_DATE_EPOCH}" \
      com.recipe-manager.packaging-contract="docker/production/v1" \
      com.recipe-manager.artifact="recipe-manager-krakend"

USER krakend
ENTRYPOINT ["/usr/local/bin/recipe-manager-krakend-entrypoint"]
CMD ["run", "-c", "/etc/krakend/krakend.tmpl"]
