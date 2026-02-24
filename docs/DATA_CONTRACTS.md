# Data Contracts — dp-mailblaze-demo

This document defines data contracts, schema expectations, and incremental logic for the dp-mailblaze-demo platform.

Repository: dp-mailblaze-demo  
Database: DP_MAILBLAZE_DEMO_DEV_DB  
Schemas: RAW, STAGING, INTERMEDIATE, MART, SNAPSHOTS  
RAW Bucket: dp-mailblaze-demo-dev-raw-3dfbc1  

---

# 1. Source Data Contracts

## 1.1 Inventory Source

Origin:
- CSV ingestion
- Stored in S3 RAW zone
- Loaded into RAW schema

Expected Columns (RAW):

- inventory_id (string)
- product_name (string)
- quantity (integer)
- price (numeric)
- ingested_at (timestamp)
- source_file (string)
- payload (variant or string)

Contract Requirements:
- inventory_id must be unique per ingestion batch
- quantity must be >= 0
- price must be >= 0
- ingested_at must be populated
- source_file must be recorded for traceability

---

## 1.2 Events Source

Origin:
- Application event stream
- Stored in S3 RAW zone
- Loaded into RAW schema

Expected Columns (RAW):

- event_id (string)
- user_id (string)
- event_type (string)
- event_timestamp (timestamp)
- ingested_at (timestamp)
- source_file (string)
- payload (variant or string)

Contract Requirements:
- event_id must be unique
- event_timestamp must not be null
- user_id must not be null
- ingested_at required for incremental logic

---

# 2. RAW Layer Principles

The RAW schema:

- Is append-only
- Preserves source fidelity
- Does not apply business logic
- Includes ingestion metadata

RAW is the system of record for replay and backfill.

---

# 3. Staging Layer Contract

Location: STAGING schema  
Materialization: View  

Responsibilities:
- Type casting
- Column renaming
- Null handling
- Basic data quality filters

No business aggregations occur in staging.

---

# 4. Intermediate Layer Contract

Location: INTERMEDIATE schema  
Materialization: View  

Responsibilities:
- Join staging models
- Enrich dimensions
- Prepare fact-ready datasets
- Apply transformation logic

Intermediate models must:

- Avoid destructive operations
- Remain idempotent
- Not duplicate records

---

# 5. MART Layer Contract

Location: MART schema  
Materialization: Table  

Contains:

- Dimension tables
- Fact tables

Example Structures:

Dimension:
- surrogate_key
- business_key
- attributes
- valid_from (for SCD)
- valid_to (nullable)
- is_current

Fact:
- fact_id
- foreign_keys
- measures
- event_timestamp

---

# 6. Idempotency Strategy

The system ensures idempotency through:

- Unique event_id / inventory_id
- S3 object naming control
- Ingestion watermark tracking
- dbt incremental logic (when enabled)

Re-running ingestion does not create duplicate records if business keys are enforced.

---

# 7. Incremental Model Logic

Incremental models:

- Filter by max(ingested_at)
- Only load new records
- Merge into target table

Example logic pattern:
WHERE ingested_at > (SELECT MAX(ingested_at)) FROM {{this}}

Incremental assumptions:

- ingested_at is monotonic
- source systems provide stable IDs

---

# 8. Snapshot (SCD Type 2) Logic

Snapshots track historical changes to dimensions.

Mechanism:

- Compare business keys
- Detect attribute change
- Expire old row (valid_to set)
- Insert new row (valid_from updated)

Columns Required:

- business_key
- updated_at
- tracked attributes

Guarantees:

- Full history retention
- Point-in-time analysis support

---

# 9. Freshness SLA

Expected Freshness:

- Ingestion: Near real-time or scheduled
- dbt models: Updated per Prefect flow execution

SLA Guidelines:

- RAW ingestion within defined schedule
- MART tables reflect latest ingestion cycle

---

# 10. Schema Evolution Policy

If source schema changes:

1. Update RAW loader
2. Adjust staging model
3. Add backward-compatible transformation
4. Add dbt test for new field
5. Document change in Git commit

Backward compatibility preferred over destructive change.

---

# 11. Data Quality Controls

Implemented Controls:

- dbt unique tests
- dbt not_null tests
- Relationship tests between fact and dimension
- CI dbt parse validation

Optional Future Enhancements:

- dbt exposures
- Great Expectations integration
- Row-level anomaly detection

---

# 12. Governance Principles

The platform follows:

- Separation of ingestion and transformation
- Immutable RAW zone
- Version-controlled transformation logic
- Test-driven analytics modeling