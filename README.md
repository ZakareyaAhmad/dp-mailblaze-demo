# dp-mailblaze-demo

![CI](https://github.com/ZakareyaAhmad/dp-mailblaze-demo/actions/workflows/ci.yml/badge.svg)

Production-oriented data engineering platform simulating ingestion from SaaS + Postgres sources into Snowflake using dbt, Prefect, Docker, AWS S3, and CI validation.

---

## 1. Project Overview

This project demonstrates a full modern data platform architecture including:

- Containerized ingestion services
- S3 raw data lake
- Snowflake warehouse with staged loading
- dbt transformation layers
- Prefect orchestration
- GitHub Actions CI
- Infrastructure-as-Code (Terraform)
- Security via IAM + Snowflake RBAC
- Offline CI validation using DuckDB

It is designed as a portfolio-grade system reflecting production engineering practices.

---

## 2. Business Problem

A SaaS company (“MailBlaze”) requires:

- Ingestion of operational Postgres data
- Ingestion of third-party SaaS event data
- Reliable, incremental loading
- Analytical star schema for reporting
- Secure cloud architecture
- CI enforcement for data model integrity
- Cost-controlled infrastructure

The system must scale from development to production while remaining secure and observable.

---

## 3. Architecture Summary

**Data Flow**

SaaS + Postgres  
→ Docker ingestion services  
→ S3 RAW bucket  
→ Snowflake External Stage  
→ RAW schema  
→ dbt STAGING → INTERMEDIATE → MART  
→ Analytics layer  

Orchestration: Prefect  
CI Validation: GitHub Actions  
IaC: Terraform  

Snowflake Database:
`DP_MAILBLAZE_DEMO_DEV_DB`

Schemas:
- RAW
- STAGING
- INTERMEDIATE
- MART
- SNAPSHOTS

S3 RAW Bucket:
`dp-mailblaze-demo-dev-raw-3dfbc1`

Storage Integration:
`DP_MAILBLAZE_DEMO_DEV_S3_INT`

---

## 4. Tech Stack

| Layer | Technology |
|-------|------------|
| Orchestration | Prefect 2.20.4 |
| Transformations | dbt |
| Warehouse | Snowflake |
| Object Storage | AWS S3 |
| IaC | Terraform |
| Containers | Docker |
| CI | GitHub Actions |
| CI Adapter | DuckDB (offline validation) |
| Mock Services | Postgres + mock_saas |