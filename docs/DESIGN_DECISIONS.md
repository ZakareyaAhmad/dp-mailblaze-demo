# Design Decisions — dp-mailblaze-demo

This document outlines key architectural and engineering decisions made during the development of the dp-mailblaze-demo data platform.

Repository: dp-mailblaze-demo  
Database: DP_MAILBLAZE_DEMO_DEV_DB  
RAW Bucket: dp-mailblaze-demo-dev-raw-3dfbc1  
CI Workflow: CI  

---

# 1. Use Snowflake as the Data Warehouse

## Decision
Use Snowflake as the primary analytical warehouse.

## Alternatives Considered
- Amazon Redshift
- Google BigQuery
- PostgreSQL (single-node analytical)
- DuckDB only

## Why Snowflake
- Separation of compute and storage
- Auto-suspend for cost control
- Native S3 integration
- Strong RBAC model
- Industry adoption

## Tradeoffs
- Credit-based cost model
- Requires external account setup
- Vendor lock-in

## Risks
- Free trial expiration
- Cost escalation if warehouse not suspended

## Mitigation
- Auto-suspend enabled
- CI designed to run without Snowflake
- Offline dbt compile via DuckDB

---

# 2. Use S3 as RAW Storage Layer

## Decision
Use S3 as the immutable RAW data zone.

## Alternatives Considered
- Direct load to Snowflake
- Local file system storage
- PostgreSQL staging tables

## Why S3
- Durable object storage
- Decouples ingestion from transformation
- Supports replay and backfill
- Enables external stage loading

## Tradeoffs
- Additional infrastructure complexity
- Requires IAM role management

## Risks
- Incorrect IAM permissions
- Data duplication

## Mitigation
- Least privilege IAM policy
- Structured folder layout
- Idempotent ingestion logic

---

# 3. Orchestrate with Prefect

## Decision
Use Prefect for workflow orchestration.

## Alternatives Considered
- Apache Airflow
- Cron jobs
- AWS Step Functions

## Why Prefect
- Lightweight local deployment
- Modern Python-native API
- Retries and logging built-in
- Simple Docker integration

## Tradeoffs
- Not as enterprise-scale as Airflow
- Requires running Prefect server container

## Risks
- Port conflicts
- Agent misconfiguration

## Mitigation
- Explicit port mapping (4201)
- Docker Compose service isolation

---

# 4. Use dbt for Transformations

## Decision
Use dbt to manage transformations and modeling.

## Alternatives Considered
- Raw SQL scripts
- Stored procedures
- Custom Python transformations

## Why dbt
- DAG-based dependency management
- Test framework built-in
- Incremental models
- Snapshot SCD2 support
- Widely adopted in analytics engineering

## Tradeoffs
- Requires learning Jinja templating
- Additional configuration overhead

## Risks
- Schema drift
- Model build failures

## Mitigation
- Tests on unique and not_null constraints
- CI dbt parse step
- Snapshot versioning for SCD2

---

# 5. Separate Environments (Local vs CI)

## Decision
Run CI without live Snowflake dependency.

## Alternatives Considered
- Full Snowflake CI integration
- Skip dbt validation in CI

## Why This Approach
- Eliminates external dependency in CI
- Allows portfolio reviewers to run pipeline
- Prevents CI failure after Snowflake trial expiry

## Tradeoffs
- CI validates structure, not warehouse connectivity

## Risks
- Runtime-only issues in Snowflake not caught in CI

## Mitigation
- Local dbt debug before push
- Clear documentation of production configuration

---

# 6. Least Privilege IAM Model

## Decision
Use a dedicated IAM role for Snowflake S3 access.

Role:
dp-mailblaze-demo-dev-snowflake-storage

## Alternatives Considered
- Full S3 admin access
- Shared application IAM role

## Why Least Privilege
- Security best practice
- Prevents lateral access
- Limits blast radius

## Tradeoffs
- More configuration effort

## Risks
- Permission misconfiguration

## Mitigation
- Explicit ListBucket + GetObject policy
- External ID condition for trust relationship

---

# 7. Dockerized Architecture

## Decision
Containerize all services.

## Alternatives Considered
- Native Python virtual environments
- Managed cloud services only

## Why Docker
- Environment reproducibility
- Isolated services
- Portfolio portability

## Tradeoffs
- Slight startup overhead
- Requires Docker knowledge

## Risks
- Port conflicts
- Volume misconfiguration

## Mitigation
- Explicit port definitions
- Documented compose structure

---

# 8. CI as Portfolio Validation

## Decision
Create GitHub Actions CI workflow (CI).

## Validations Included
- Ruff lint
- Ruff format check
- Terraform validate
- dbt parse (offline)
- Docker build

## Why
- Demonstrates DevOps maturity
- Enforces code quality
- Ensures infrastructure correctness

## Tradeoffs
- Increased repository complexity

## Risks
- CI drift from runtime config

## Mitigation
- Absolute path to CI profiles
- Offline DuckDB profile
- Matrix Docker build

---

# Summary

The architecture prioritizes:

- Separation of concerns
- Cost control
- Security best practices
- Idempotency
- Portability
- CI independence from cloud services

The platform balances production realism with portfolio accessibility.