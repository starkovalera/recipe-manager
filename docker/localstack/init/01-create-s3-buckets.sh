#!/usr/bin/env bash

set -euo pipefail

create_private_bucket() {
  local bucket_name="$1"

  if ! awslocal s3api head-bucket --bucket "${bucket_name}" >/dev/null 2>&1; then
    awslocal s3api create-bucket --bucket "${bucket_name}" >/dev/null
  fi

  awslocal s3api put-public-access-block \
    --bucket "${bucket_name}" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
}

create_private_bucket "${S3_USER_MEDIA_BUCKET_NAME}"
create_private_bucket "${S3_SYSTEM_ARTIFACTS_BUCKET_NAME}"

cat >/tmp/user-media-cors.json <<'JSON'
{
  "CORSRules": [
    {
      "AllowedOrigins": [
        "http://127.0.0.1:5173",
        "http://localhost:5173"
      ],
      "AllowedMethods": ["GET"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "Content-Type"],
      "MaxAgeSeconds": 300
    }
  ]
}
JSON

awslocal s3api put-bucket-cors \
  --bucket "${S3_USER_MEDIA_BUCKET_NAME}" \
  --cors-configuration file:///tmp/user-media-cors.json
