# Week 1 review and week 2 debt

## Definition of Done review

- Models have migrations and API endpoints are represented in OpenAPI.
- Authentication, membership permission, inactive membership, and maker-checker paths have tests.
- Shared API errors have a Persian envelope and requests carry a correlation ID.
- Docker services, health checks, CI quality gates, structured logs, and Sentry bootstrap are present.

## Week 2 backlog (onboarding/KYC and documents)

- Add short-lived presigned upload/download URLs, MIME sniffing, size limits, checksum, malware scanning, and immutable document metadata.
- Implement KYC state transitions exclusively through services with idempotency keys and audit events.
- Add provider adapter contract/timeout/retry tests for OCR and sanctions screening.
- Replace the simple sessions response with persisted refresh-session rotation and revocation.
- Add PostgreSQL integration tests for JSON/scopes and container-level health checks in CI.
- Add full OpenTelemetry exporter configuration and propagate correlation context into Celery headers.
