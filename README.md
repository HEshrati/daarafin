# Darafin backend

This directory is the backend workspace for the Darafin pharmaceutical supply-chain finance platform. It starts as a **modular monolith**: domain modules are deployed together, but their ownership and dependency boundaries remain explicit so selected modules can be extracted later if scale or team ownership requires it.

## Repository layout

```text
backend/
  config/
    settings/          # Environment-specific Django settings
    urls/              # Root and versioned URL configuration
    celery/            # Celery app, routing, queues, and beat schedule
    observability/     # Logging, tracing, metrics, and error reporting
  apps/
    identity/
    organizations/
    onboarding/
    invoices/
    facilities/
    financing/
    ledger/
    payments/
    documents/
    risk/
    notifications/
    reporting/
    audit/
  common/              # Domain-neutral primitives only
  integrations/        # Adapters for external systems
    bank/
    insurance/
    sms/
    ocr/
    sanctions/
  tests/               # Cross-module integration and contract tests
```

## Module rules

Every domain app follows the same internal structure:

- `models.py`: persistence models and invariants close to stored data.
- `services.py`: commands, state transitions, transaction boundaries, and business side effects.
- `selectors.py`: read-only application queries. Selectors must not change state.
- `api/serializers.py`: transport validation and response serialization.
- `api/views.py`: thin HTTP handlers that delegate to services or selectors.
- `permissions.py`: domain-specific authorization rules.
- `tasks.py`: thin Celery entry points that delegate behavior to services.
- `tests/`: tests owned by the domain app.

The following constraints are mandatory:

1. **All state transitions happen in `services.py`.** A view, serializer, selector, task, signal, or model admin must not implement a business state transition directly.
2. **All application reads happen in `selectors.py`.** Views and services may call selectors; selectors remain read-only.
3. **Views stay thin.** They validate transport input, authorize the request, and call a service or selector.
4. **Celery tasks stay thin.** A task handles delivery/retry concerns and calls an idempotent service.
5. **Cross-module writes use the owning module's service.** One app must not update another app's models directly.
6. **Financial operations require a transaction boundary, fixed-precision decimal values, idempotency, and auditability.** These primitives will be implemented in later tasks under `common/` and `apps/audit/`.
7. **External providers are accessed through `integrations/` adapters.** Domain code must not import a provider SDK directly.

## Dependency direction

```text
API / Celery entry points
          |
          v
      services  -----> integrations adapters
          |
          +-----> selectors
          |
          v
        models

common primitives may be imported by all layers.
Domain modules collaborate through public services and events, not direct model writes.
```

## Local development

Prerequisites are Docker Desktop with Compose v2 and Git. Clone the repository, enter `backend/`, copy `.env.example` to `.env`, generate non-production values for every blank secret, and run:

```bash
docker compose up --build
```

The stack starts PostgreSQL 16, Redis 7, versioned MinIO document storage, Django web, the four-queue Celery worker, and Celery beat. In local settings only the web service applies migrations before it starts; worker and beat never race it. Production never auto-migrates.

Useful commands:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web pytest
docker compose exec web celery -A config worker -Q integrations -l INFO
docker compose exec web celery -A config beat -l INFO
docker compose exec web celery -A config call darafin.ping
```

To run the frontend and backend together or securely transfer PostgreSQL/MinIO state to another
developer, see [`docs/docker-sharing.md`](docs/docker-sharing.md).

`GET /health/` checks PostgreSQL, Redis, and MinIO and returns HTTP 200 only when all three are reachable. OpenAPI is available at `/api/schema/` and Swagger UI at `/api/docs/`.

Week-two APIs add onboarding cases and decisions, private KYC document presigning, invoice lifecycle/bulk operations, and facility reservation/history under `/api/v1/`. Financial mutations use decimal strings, audit hashes, maker-checker rules, optimistic versions, and idempotency keys.

Never put real credentials in source control. Base settings require secrets from the environment; local/test fallbacks are explicitly insecure and production forces `DEBUG=False`.
