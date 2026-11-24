---
doc_id: doc_02_python_django_backend
title: High-Throughput FinTech API & Asynchronous Ledger Service
domain: Python Backend & Distributed Caching
tech_stack: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery
link: https://www.thoughtworks.com/clients
---

## Project Overview
We built a resilient backend transaction and reporting engine for a financial operations client needing strict auditability, scheduled reconciliation, and high-concurrency API access for enterprise partners.

## Technical Architecture
Core business services were implemented in Python and Django REST Framework, backed by PostgreSQL with normalized relational schemas, row-level locking, and read replicas for analytical queries. Redis served dual roles as an API response cache and broker for Celery background workers handling batch invoice generation and webhook retries.

## Engineering Execution
Database query bottlenecks were resolved through selective prefetching, partial indexes, and connection pooling. Automated Alembic/Django migrations and pytest integration suites guarded schema evolution and idempotent webhook processing under burst traffic.

## Outcomes Delivered
Clients gained deterministic financial reconciliation pipelines, clean OpenAPI documentation for third-party integrators, and reliable background job orchestration without blocking user-facing APIs.
