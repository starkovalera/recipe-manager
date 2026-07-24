# P10 Owner Verification Runbook

Use the branch SHA recorded in the draft PR. Automated tests cover authorization,
contracts, LOCAL bytes, S3 signing, frontend retrieval modes, and gateway parity.
The checks below require the repository owner because they use a browser session
or AWS credentials.

## LOCAL / PREVIEW

Prerequisites: PostgreSQL, Redis, KrakenD, backend, worker, and frontend started
with the normal PREVIEW configuration and a signed-in Clerk test user.

1. Import one image and one supported URL containing images.
2. Confirm the recipe grid, recipe hero, cover choices, preview modal, and import
   detail images render through KrakenD.
3. In browser Network, confirm domain responses contain image/source IDs and no
   `mediaUrl` or storage keys.
4. Confirm one or more `POST /media/access` requests return
   `accessMode=authenticated_fetch` and stable `/media/{type}/{id}` URLs.
5. Confirm each LOCAL GET includes `Authorization` and returns the expected MIME
   type and bytes.
6. Delete or hide the owning recipe and confirm a fresh access request returns
   `MEDIA_NOT_FOUND` for its image.
7. Confirm default recipe SVGs render without a media-access request.

## Live S3

Prerequisites: a private disposable user-media bucket, an AWS region, and
credentials with narrowly scoped `s3:GetObject` access. Do not commit values.

1. Configure PROD-compatible S3 settings and put one test image under a canonical
   `USER_MEDIA` key represented by a test database row.
2. Request `POST /media/access` for the owned stable ID.
3. Confirm `accessMode=direct`, `expiresAt` is approximately 60 seconds after the
   response, and the URL retrieves the object directly from S3.
4. Confirm backend logs contain no presigned URL or query signature.
5. Confirm a foreign user receives the same `MEDIA_NOT_FOUND` item as a missing ID.
6. Confirm the FastAPI GET media route does not proxy S3 content.

Live S3 verification remains a gap until the owner supplies the private bucket
and credentials and records the result in the PR.
