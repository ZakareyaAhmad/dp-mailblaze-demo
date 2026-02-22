# dp-mailblaze-demo Terraform (AWS)

This folder provisions AWS infrastructure used by the dp-mailblaze-demo pipeline.

## What it creates
- S3 buckets:
  - raw (existing bucket adopted via import if already created)
  - processed
  - archive
- IAM policy for ingestion user (least-privilege access to the three buckets)
- Optional Snowflake storage integration IAM Role (created only when Snowflake identifiers are provided)

## Environments
Use separate tfvars per environment (dev/prod) and a unique backend key or workspace.

For this walkthrough, we use:
- env: dev
- region: eu-west-2

## Quick start
From repo root:
```bash
cd infra/terraform
./write_dev_tfvars.sh
terraform init
terraform plan -var-file=env/dev.tfvars
terraform apply -var-file=env/dev.tfvars