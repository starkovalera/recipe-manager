FROM krakend:2.13.8 AS validator

ENV FC_ENABLE=1 \
    FC_SETTINGS=/etc/krakend/config \
    FC_OUT=/tmp/krakend.generated.json \
    CLERK_ISSUER=https://example.clerk.accounts.dev \
    CLERK_JWKS_URL=https://example.clerk.accounts.dev/.well-known/jwks.json
COPY krakend.tmpl /etc/krakend/krakend.tmpl
COPY config /etc/krakend/config
RUN krakend check -tnd -c /etc/krakend/krakend.tmpl

FROM krakend:2.13.8

ENV FC_ENABLE=1 \
    FC_SETTINGS=/etc/krakend/config \
    FC_OUT=/tmp/krakend.generated.json
COPY --from=validator --chown=krakend:nogroup /etc/krakend /etc/krakend
COPY --chmod=755 --chown=krakend:nogroup entrypoint.sh /usr/local/bin/recipe-manager-krakend-entrypoint

ENTRYPOINT ["/usr/local/bin/recipe-manager-krakend-entrypoint"]
CMD ["run", "-c", "/etc/krakend/krakend.tmpl"]
