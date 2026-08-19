# Week 2 review (D7–D13)

Implemented organization onboarding state transitions, auditable KYC decisions, private presigned document upload/download, mock malware scanning, invoice lifecycle and bulk validation, optimistic locking, disputes, and transactional facility reservations with idempotency.

## Definition of Done

- Database migrations exist for audit, idempotency, onboarding, documents, invoices, and facilities.
- Organization-scoped reads, maker-checker decisions, immutable financial records, and IDOR-oriented document queries are enforced.
- Amounts use fixed-precision decimals and API serializers return strings.
- OpenAPI covers the new endpoints and automated tests cover state transitions, invoice uniqueness/conflicts, and facility limit/idempotency rules.

## Carried debt

- Replace mock document scanning with ClamAV and verify checksum by streaming the uploaded S3 object.
- Persist bulk-preview tokens with expiry instead of accepting validated rows again at commit.
- Add a dedicated dispute-resolution/credit-note workflow and notification templates.
- Run concurrency tests in CI against PostgreSQL with parallel connections; SQLite tests only verify service semantics.
