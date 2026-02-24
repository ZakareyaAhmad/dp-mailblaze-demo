# Security

This document describes the security posture of **dp-mailblaze-demo** across:
- GitHub Actions CI
- Docker runtime (local)
- AWS (S3 + IAM)
- Snowflake (RBAC + staging from S3)
- Secrets handling and rotation

It is written to be production-realistic, with least-privilege design and explicit operational procedures.

---

## 1. Identity & Access Management (IAM) Overview

### 1.1 Actors
**Human operator (developer)**
- Runs Docker Compose locally
- Runs ingestion backfills
- Owns AWS and Snowflake credentials (stored as secrets; never committed)

**GitHub Actions (CI workflow: `CI`)**
- Performs offline validations:
  - Ruff lint/format
  - Terraform validate
  - dbt parse using DuckDB (no Snowflake access required)
  - Docker image builds for:
    - `ingest/Dockerfile` (context `ingest`)
    - `orchestration/prefect/Dockerfile` (context `orchestration/prefect`)
- CI should not require Snowflake or AWS production credentials.

**Snowflake service principal**
- Reads raw files from S3 using a **Snowflake Storage Integration**.
- Assumes an AWS IAM role with least-privilege read access to the RAW bucket.

---

## 2. AWS Security

### 2.1 S3 Buckets and Intended Use

The project uses multiple buckets; **only one is the RAW lake used for data ingestion and Snowflake staging**:

- **Terraform state bucket**
  - `dp-mailblaze-demo-dev-terraform`
  - Contains Terraform state; must be protected with encryption + blocked public access.

- **RAW data bucket (source-of-truth for ingestion + Snowflake load)**
  - `dp-mailblaze-demo-dev-raw-3dfbc1`
  - Contains raw landing data written by ingestion services.

> **Portfolio note:** For documentation and operations, treat `dp-mailblaze-demo-dev-raw-3dfbc1` as the only bucket that Snowflake reads from.

### 2.2 Bucket Security Controls (Expected/Recommended)
For all buckets, and especially for the Terraform state and RAW data buckets:
- Block all public access
- Enable server-side encryption (SSE-S3 or SSE-KMS)
- Prefer bucket policies restricting access to specific IAM roles
- Enable versioning on Terraform state bucket (recommended)

### 2.3 IAM Role Assumed by Snowflake

Snowflake reads from S3 by assuming an AWS IAM role:

- **Role name:** `dp-mailblaze-demo-dev-snowflake-storage`
- **Role ARN:** `arn:aws:iam::443414059898:role/dp-mailblaze-demo-dev-snowflake-storage`

This role is designed to be *read-only* and scoped only to the RAW bucket.

### 2.4 Confused Deputy Protection (External ID)

Snowflake assumes the role using a trust policy that includes:
- A trusted principal (Snowflake identity)
- An **External ID**

Values (final state):
- **Trusted principal:** `arn:aws:iam::727529935573:user/qs0e1000-s`
- **External ID:** `YU73962_SFCRole=2_TlySUcCyd5pFYEKpcnABcytAjMo=`

**Why this matters:**
- Prevents other Snowflake accounts or third parties from using the role even if they know the ARN.
- The External ID ties the trust to the intended Snowflake integration.

### 2.5 IAM Policy Scope (Least Privilege)

The Snowflake-assumed role policy allows only:
- `s3:ListBucket`
- `s3:GetObject`

Scoped to:
- `arn:aws:s3:::dp-mailblaze-demo-dev-raw-3dfbc1`
- `arn:aws:s3:::dp-mailblaze-demo-dev-raw-3dfbc1/*`

This ensures Snowflake can read raw files but cannot write, delete, or list unrelated buckets.

---

## 3. Snowflake Security (RBAC + Data Access)

> Note: Snowflake objects are created via SQL scripts (not Terraform). Terraform defines AWS-side infrastructure only.

### 3.1 Database & Schemas (Final State)

**Database:** `DP_MAILBLAZE_DEMO_DEV_DB`

**Schemas:**
- `RAW` (landing tables / external stage loads)
- `STAGING` (dbt staging models; typically views)
- `INTERMEDIATE` (dbt intermediate transformations; typically views)
- `MART` (analytics-ready facts/dimensions; typically tables)
- `SNAPSHOTS` (dbt snapshots)

### 3.2 Recommended Snowflake RBAC Model (Production-Realistic)

Even if account access is limited, the intended RBAC structure is:

**Role: SYSADMIN / SECURITYADMIN (admin roles)**
- Create database, warehouses, roles, integrations.
- Manage grants.

**Role: `DP_MAILBLAZE_DEMO_DEV_LOADER` (ingestion / loading)**
- USAGE on warehouse used for COPY/loads
- USAGE on database + RAW schema
- CREATE STAGE / FILE FORMAT (as required)
- INSERT/UPDATE on RAW landing tables

**Role: `DP_MAILBLAZE_DEMO_DEV_TRANSFORMER` (dbt role)**
- USAGE on transformation warehouse
- USAGE on database
- SELECT on RAW
- CREATE VIEW in STAGING/INTERMEDIATE
- CREATE TABLE in MART
- CREATE in SNAPSHOTS (if snapshots enabled)

**Role: `DP_MAILBLAZE_DEMO_DEV_READER` (BI/read-only)**
- USAGE on database
- SELECT on MART (and optionally STAGING/INTERMEDIATE)

> In a portfolio context, document these roles even if the account is inaccessible, because it shows correct production design.

### 3.3 Row-Level Security (RLS) Approach

This project’s default assumes schema-level separation and least privilege by role.
If row-level security is needed (e.g., tenant isolation), implement:

- Secure views in `MART` that enforce tenant filters using:
  - session context (e.g., `CURRENT_ROLE()` or `CURRENT_USER()`)
  - mapping tables (role-to-tenant)
- Or Snowflake Row Access Policies (preferred in production)

**Example design:**
- `MART.SECURE_FACT_EVENTS` applies `WHERE tenant_id IN (...)` based on role mapping.

RLS is not required for the demo, but the architecture supports it via MART-layer secure views.

---

## 4. Snowflake ↔ S3 Security (Storage Integration + External Stage)

### 4.1 Storage Integration (Final State)
- **Storage Integration:** `DP_MAILBLAZE_DEMO_DEV_S3_INT`
  - `STORAGE_PROVIDER = S3`

### 4.2 External Stage (Final State)
- **External stage:** `STG_S3_RAW`
- Reads from paths such as:
  - `@STG_S3_RAW/events/`
  - `@STG_S3_RAW/inventory/`

**Security benefits:**
- Access is controlled by Snowflake integration + AWS IAM policy.
- No static AWS keys stored in Snowflake.

---

## 5. Secrets Handling (Local + CI)

### 5.1 What is a Secret in This Project
- AWS credentials (if used locally)
- Snowflake credentials (account/user/password or keypair)
- Prefect API keys (if Prefect Cloud is used; this demo typically uses Prefect Server locally)
- Any third-party SaaS tokens

### 5.2 Rules (Non-Negotiable)
- **Never commit secrets** to Git
- `.env` files are ignored by `.gitignore`
- CI should not print secrets to logs

### 5.3 Where Secrets Live

**Local development**
- `.env` or Docker Compose environment variables (not committed)
- OS keychain / secret manager (preferred)

**GitHub**
- Repository secrets under:
  - GitHub → Repo → **Settings** → **Secrets and variables** → **Actions**
- Use secrets only when strictly needed (ideally not for CI validation)

### 5.4 CI “Offline” Posture
The `CI` workflow runs:
- `dbt parse` with DuckDB using `.github/ci_profiles/profiles.yml`
- No Snowflake login needed
- No AWS access needed

This reduces blast radius:
- PRs can be validated without touching production data systems.

---

## 6. Key Rotation Policy (Recommended)

### 6.1 AWS
- If using access keys locally:
  - Rotate at least every 90 days
  - Prefer short-lived credentials (AWS SSO / assumed roles) where possible
- After rotation:
  - Update local `.env`
  - Update GitHub secrets (if used)
  - Validate by listing S3 bucket contents (read-only check)

### 6.2 Snowflake
- Prefer key-pair auth or SSO in production.
- If password-based:
  - Rotate regularly
  - Restrict network policies and MFA where possible
- Verify no plaintext secrets are present in repository history.

---

## 7. Least Privilege Summary

This project follows least privilege by design:

- Snowflake can only **read** from a single RAW bucket:
  - `dp-mailblaze-demo-dev-raw-3dfbc1`
- Snowflake access is mediated by:
  - Storage integration `DP_MAILBLAZE_DEMO_DEV_S3_INT`
  - External stage `STG_S3_RAW`
  - AWS IAM role `dp-mailblaze-demo-dev-snowflake-storage`
  - External ID protection against confused deputy attacks
- CI validates code without requiring Snowflake or AWS production access.

---

## 8. How to Verify Security Configuration (Where to Click / What to Run)

### 8.1 Verify GitHub Secrets Are Not Exposed
**Where:** GitHub Repo → Settings → Secrets and variables → Actions  
**What to confirm:**
- Only required secrets exist
- No plaintext secrets are printed in workflow logs

### 8.2 Verify `.gitignore` Protects Secret Files
**Where:** Repo root `.gitignore`  
**What to confirm:**
- `.env`, `.env.*`, keys, and profiles are ignored
- `dbt/profiles.yml` is ignored (local)

### 8.3 Verify Snowflake Read Access Is Limited to RAW Bucket (AWS-side)
**Where:** AWS IAM → Roles → `dp-mailblaze-demo-dev-snowflake-storage` → Permissions  
**What to confirm:**
- Only `s3:ListBucket` and `s3:GetObject`
- Resource scope is only `dp-mailblaze-demo-dev-raw-3dfbc1`

### 8.4 Verify External ID Is Enforced (AWS-side)
**Where:** AWS IAM → Roles → `dp-mailblaze-demo-dev-snowflake-storage` → Trust relationships  
**What to confirm:**
- Trusted principal is Snowflake identity
- External ID condition is present and matches the documented value

---

## 9. Security Incident Response (Portfolio-Grade)

If a secret is accidentally committed:
1. Immediately rotate the secret (AWS key / Snowflake password)
2. Remove from repo history (use `git filter-repo` or BFG)
3. Invalidate any exposed tokens
4. Add additional `.gitignore` rules if needed
5. Add a CI secret scanner (optional enhancement)

---

## 10. Non-Goals / Assumptions

- This repo demonstrates production-like security patterns.
- It is not a fully hardened enterprise deployment (e.g., no mandatory KMS CMKs, no VPC endpoints documented).
- The design intentionally keeps CI offline to reduce risk and cost.