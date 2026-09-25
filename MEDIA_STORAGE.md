# Private media storage

Media uploads are disabled unless an adapter is explicitly configured. The current API accepts JPEG, PNG, and WebP images up to 10 MiB, re-encodes them as JPEG, removes source metadata, and stores a separate preview. Both variants are private; they are served through authenticated owner-scoped endpoints, never direct public object URLs.

## S3-compatible object storage

Set these through the deployment's secret/configuration manager (do not commit credentials):

```text
MEDIA_STORAGE_BACKEND=s3
MEDIA_S3_ENDPOINT_URL=https://<provider-endpoint>
MEDIA_S3_BUCKET=<private-bucket>
MEDIA_S3_REGION=<provider-region>
MEDIA_S3_ACCESS_KEY_ID=<secret-reference>
MEDIA_S3_SECRET_ACCESS_KEY=<secret-reference>
MEDIA_S3_PREFIX=crista-media
```

The API uses path-style S3 requests and does not set a public ACL. Configure the bucket/provider to deny anonymous access and use TLS. Keep credentials scoped to the one bucket/prefix with only object get/put/delete permissions. Configure provider-side versioning/backup and test restoration before treating uploads as durable. Runtime configuration is validated but bucket reachability and permissions are not probed at startup.

## Local filesystem

For development or a single durable host, configure `MEDIA_STORAGE_BACKEND=local` and `MEDIA_STORAGE_DIR=/absolute/path/to/durable/media`. The directory must be a persistent volume and included in backup/restore. Container-local ephemeral storage is not suitable for production.

With no adapter or incomplete configuration the rest of the API remains available, while media endpoints return `503` and `/health` reports `media_storage.available=false`.
