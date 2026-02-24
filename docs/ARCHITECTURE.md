# Architecture

## System Overview

`dp-mailblaze-demo` is a portfolio-grade, production-oriented data platform that simulates ingestion from:
- a mock SaaS source (`mock_saas`)
- a Postgres source (`postgres`)

It lands raw files into an S3 data lake and models analytics-ready tables in Snowflake using dbt, orchestrated with Prefect. CI validates code quality, Terraform formatting/validation, offline dbt project parsing, and Docker build correctness.

At a high level:

1. **Extract** from Postgres + mock SaaS
2. **Land** raw data into **S3** (`dp-mailblaze-demo-dev-raw-3dfbc1`)
3. **Load** to Snowflake RAW using an external stage (`STG_S3_RAW`) backed by storage integration (`DP_MAILBLAZE_DEMO_DEV_S3_INT`)
4. **Transform** with dbt into STAGING → INTERMEDIATE → MART (and SNAPSHOTS)
5. **Orchestrate** end-to-end with Prefect

This repo supports both:
- **Local demo execution** via Docker Compose
- **CI validation** via GitHub Actions workflow `CI`


## Components and Responsibilities

### 1) Source Systems (simulated)
**Postgres (`postgres`)**
- Represents an operational data store
- Used to simulate OLTP-style tables

**Mock SaaS API (`mock_saas`)**
- Represents a third-party event source (Mailblaze-style provider)
- Used to simulate webhook/event-like data (e.g., email events)


### 2) Ingestion Layer (containerized)
**Ingest service (`ingest`)**
- Extracts from Postgres and mock SaaS
- Writes raw files into S3 under stable prefixes:
  - `s3://dp-mailblaze-demo-dev-raw-3dfbc1/events/`
  - `s3://dp-mailblaze-demo-dev-raw-3dfbc1/inventory/`
- Maintains basic state/watermarks in S3 to support incremental ingestion and replay

This is intentionally designed as a containerized ingestion worker so it can scale out independently of transformation.


### 3) Storage Layer (S3 raw lake)
**Raw bucket**
- `dp-mailblaze-demo-dev-raw-3dfbc1`
- Used as the durable raw landing zone
- Prefix structure is treated as part of the data contract:
  - `/events/`
  - `/inventory/`

This bucket is accessed by:
- ingestion containers (write)
- Snowflake (read) via storage integration + external stage


### 4) Warehouse Layer (Snowflake)
**Database**
- `DP_MAILBLAZE_DEMO_DEV_DB`

**Schemas**
- `RAW` — direct loads from S3 stage
- `STAGING` — clean + typed + lightly modeled views/tables
- `INTERMEDIATE` — business logic normalization
- `MART` — dimensional/fact tables for analytics
- `SNAPSHOTS` — slowly changing dimension tracking via dbt snapshots

**Storage integration**
- `DP_MAILBLAZE_DEMO_DEV_S3_INT`

**External stage**
- `STG_S3_RAW` (reads from the raw S3 bucket)

Snowflake reads raw files from S3 using:
- IAM role: `dp-mailblaze-demo-dev-snowflake-storage`
  - ARN: `arn:aws:iam::443414059898:role/dp-mailblaze-demo-dev-snowflake-storage`


### 5) Transformation Layer (dbt)
**dbt project**
- Located at: `dbt/`
- dbt profile name: `dp_mailblaze_demo`

**Model layers**
- `dbt/models/staging/` → schema `STAGING`
- `dbt/models/intermediate/` → schema `INTERMEDIATE`
- `dbt/models/marts/` → schema `MART`
  - `marts/dimensions/`
  - `marts/facts/`
- Tests: `dbt/tests/`
- Snapshots: `dbt/snapshots/` → schema `SNAPSHOTS`

dbt is responsible for:
- applying consistent naming and typing conventions
- creating reusable staging models
- building final marts optimized for BI/query patterns
- enforcing quality via tests
- tracking history via snapshots


### 6) Orchestration Layer (Prefect)
Prefect is deployed in a local Docker-based topology:

- `prefect_server` — Prefect API/UI backend
- `prefect_agent` — executes scheduled/queued work
- `prefect_flow` — flow runner container that runs `orchestration/prefect/flow.py`

**Flow name**
- `dp-maiblaze-demo-dev-flow`

The flow coordinates:
- ingestion execution
- load to Snowflake RAW (when Snowflake is available)
- dbt runs for transformations and tests


### 7) CI / Quality Gates (GitHub Actions)
Workflow name: `CI` (`.github/workflows/ci.yml`)

Jobs:
- `python_lint (ruff)` — linting
- `python_format_check (ruff format --check)` — formatting
- `terraform_validate` — terraform fmt + validate (no backend)
- `dbt_compile (offline)` — dbt deps + parse using DuckDB profile in CI
- `docker_build` — build Docker images with correct build contexts

**Important CI substitution**
CI uses DuckDB for dbt validation:
- `.github/ci_profiles/profiles.yml`
- `dp_mailblaze_demo` profile
- adapter: DuckDB
This allows parsing/validation without requiring Snowflake credentials.


## How Components Interact (End-to-End)

### Control plane vs Data plane

**Control plane**
- GitHub Actions for CI (quality gates)
- Prefect server/agent for orchestration & scheduling

**Data plane**
- Ingestion containers extract from sources and write to S3
- Snowflake reads from S3 and materializes RAW
- dbt builds STAGING → INTERMEDIATE → MART
- Snapshots capture historical changes into SNAPSHOTS


## Data Lifecycle (From Source to Mart)

1. **Extract**
   - `ingest` pulls from:
     - Postgres tables (operational)
     - mock SaaS events (API-like)

2. **Land raw to S3**
   - Files written to:
     - `s3://dp-mailblaze-demo-dev-raw-3dfbc1/events/`
     - `s3://dp-mailblaze-demo-dev-raw-3dfbc1/inventory/`
   - Naming and partitioning strategy can evolve (see `docs/DATA_CONTRACTS.md`)

3. **Load to Snowflake RAW**
   - Snowflake uses:
     - storage integration: `DP_MAILBLAZE_DEMO_DEV_S3_INT`
     - external stage: `STG_S3_RAW`
   - RAW schema receives minimally transformed data

4. **Transform in dbt**
   - STAGING: typed + cleaned + standardized
   - INTERMEDIATE: business rules and joins centralized
   - MART: dimensional + fact tables for analytics
   - SNAPSHOTS: historical tracking

5. **Consume**
   - BI / analysts query MART
   - Data quality results and execution metadata are available from dbt + Prefect


## Why These Technologies Were Chosen

### Docker + Docker Compose
- Reproducible local environment
- Clear separation of services (sources, orchestration, ingestion, transformations)

### Prefect
- Modern orchestration with strong local developer ergonomics
- Explicit retries, logging, parameterization, and UI visibility
- Easy to upgrade to managed deployments later

### S3 Raw Data Lake
- Low-cost durable storage for raw data
- Enables replay/backfill without re-querying sources
- Natural boundary between ingestion and warehousing

### Snowflake
- Scales warehouse compute independently of storage
- Supports secure cross-account access from S3 via storage integration
- Strong support for analytics workloads and governance

### dbt
- Industry standard for analytics engineering
- Modular modeling with tests and snapshots
- Clear lineage between raw → staging → marts

### GitHub Actions CI + Ruff + Terraform validation
- Enforces code standards and infra hygiene
- Validates dbt project correctness without secrets
- Ensures Docker images remain buildable


## Scaling Strategy (10x and 100x)

### 10x scale (more sources, more data)
**Ingestion**
- Run ingestion per source as separate tasks/containers
- Partition raw files by date and source keys
- Use S3 prefix strategy to support parallel loads

**Snowflake**
- Introduce dedicated warehouses per workload class:
  - ingest/load warehouse
  - transformation warehouse
  - BI/query warehouse
- Use auto-suspend aggressively to control cost

**dbt**
- Incremental models for large facts
- Use ephemeral models only where appropriate; prefer tables for heavy reuse


### 100x scale (large event streams, strict SLAs)
**Ingestion**
- Shift from batch file landing to streaming (Kinesis/Kafka) where needed
- Still preserve raw “bronze” in S3 for replay and auditing

**Snowflake**
- Consider Snowpipe / auto-ingest patterns
- Separate compute by team/domain (domain-driven marts)

**Orchestration**
- Move Prefect server to managed Prefect Cloud or hosted control plane
- Use work pools/queues and stronger concurrency controls


## Key Tradeoffs

### Raw files in S3 vs direct load to Snowflake
**Chosen:** S3 first  
**Pros:** replayability, auditability, decoupling ingestion from warehouse  
**Cons:** additional moving parts, requires stage/integration setup

### dbt in CI uses DuckDB (offline) vs Snowflake
**Chosen:** DuckDB for CI validation  
**Pros:** no secrets required, fast parse/compile feedback, consistent linting  
**Cons:** does not validate Snowflake-specific SQL/runtime behavior

### Containerized orchestration vs managed orchestration
**Chosen:** containerized Prefect for local demo  
**Pros:** reproducible, cheap, portfolio-friendly  
**Cons:** not HA by default, requires docker runtime


## Alternatives Considered

- **Airflow** instead of Prefect  
  - More common in legacy stacks but heavier for local-first developer workflows.

- **BigQuery/Redshift** instead of Snowflake  
  - Both viable; Snowflake selected for strong S3 integration patterns and RBAC clarity.

- **Dagster** instead of Prefect  
  - Strong asset-based orchestration; Prefect selected for straightforward flow-first design and local UI simplicity.

- **CI running dbt against Snowflake**
  - Rejected because CI should not depend on privileged credentials for basic validation.
  - DuckDB-based parsing provides a stable secretless baseline.