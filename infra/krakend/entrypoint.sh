#!/bin/sh
set -eu

: "${CLERK_ISSUER:?CLERK_ISSUER is required to start KrakenD}"
: "${CLERK_JWKS_URL:?CLERK_JWKS_URL is required to start KrakenD}"

exec krakend "$@"
