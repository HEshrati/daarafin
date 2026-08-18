#!/bin/sh
set -eu
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/${S3_BUCKET:-darafin-documents}"
mc version enable "local/${S3_BUCKET:-darafin-documents}"
bucket="${S3_BUCKET:-darafin-documents}"
cat >/tmp/backend-policy.json <<JSON
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["arn:aws:s3:::$bucket/*"]},{"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["arn:aws:s3:::$bucket"]}]}
JSON
mc admin policy create local darafin-backend /tmp/backend-policy.json
mc admin user add local "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY" || true
mc admin policy attach local darafin-backend --user "$S3_ACCESS_KEY_ID"
