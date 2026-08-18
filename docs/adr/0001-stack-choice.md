# ADR-001: Modular Monolith with Django/DRF/PostgreSQL

## Context

Darafin has a small-to-medium team, a one-month frontend deadline, and a 16-week backend plan. The financial core needs reliable ACID transactions and auditability without the coordination cost of a distributed system.

## Options considered

- Java/Spring Boot: mature, but slower initial delivery and more operational ceremony for this team.
- FastAPI microservices: attractive API ergonomics, but premature network and data-consistency boundaries.
- Node/Nest: productive, but Django's transactional ORM and built-in admin better fit operations-heavy delivery.

## Decision

Use a modular monolith with Django 5.x, Django REST Framework, Python 3.13, and PostgreSQL 16. It provides rapid delivery, ACID transaction support, a ready administration surface, mature security primitives, and explicit module boundaries that allow gradual extraction when scale or team ownership justifies it.

## Deferred decisions

Kafka, blockchain, and microservices are rejected for the initial phase. Revisit them only with measured throughput, independent scaling, regulatory, or ownership requirements.
