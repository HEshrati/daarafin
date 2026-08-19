# Sharing the Darafin Docker stack

Docker volumes are local runtime storage and cannot be meaningfully pushed to Git. Share the
versioned Compose file and container image, then transfer logical backups only when shared data
actually exists.

## Repository layout

Clone the repositories as siblings:

```text
Daarafin/
  backend/
  frontend/
```

From `backend/`, start the complete stack:

```powershell
docker compose -f compose.fullstack.yaml pull frontend
docker compose -f compose.fullstack.yaml up -d --build
```

The frontend is available at `http://localhost:3000` and the API at
`http://localhost:8000`. The frontend image is published as
`ghcr.io/setyhoseini81/darafin-frontend:latest`. If the package is private, authenticate with
GitHub Container Registry before pulling it.

Set `FRONTEND_AUTH_SECRET` to a strong environment-specific value outside local development.
Never commit `.env`.

## Back up PostgreSQL and MinIO

Run from PowerShell 7 or newer:

```powershell
pwsh -File scripts/backup-docker-data.ps1
```

The script creates a timestamped directory under `backups/` containing:

- `postgres.dump`: a portable PostgreSQL custom-format dump;
- `minio-data.tar.gz`: a consistent MinIO volume archive;
- `manifest.json`: file sizes and SHA-256 checksums.

Redis is intentionally excluded because it contains cache, Celery broker, and result state rather
than durable application data. The `backups/` directory is ignored by Git. A backup can contain
identity, document, and financial records; encrypt it and send it only through a private channel.

## Restore a backup

Restore replaces the target PostgreSQL and MinIO data and briefly stops application services:

```powershell
pwsh -File scripts/restore-docker-data.ps1 `
  -BackupDirectory C:\secure-transfer\darafin-backup `
  -Force
```

The restore script validates every checksum before changing data. Keep independent backups before
restoring over an environment that already contains records.

## Current local data state

At the time this sharing setup was added, application models contained zero rows and the MinIO
bucket contained zero objects. Running migrations therefore gives a collaborator the same durable
application state without transferring a snapshot. No raw volume or database dump is committed to
Git.
