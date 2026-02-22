# Contributing

## Workflow
1. Create a feature branch from main
2. Commit small, reviewable changes
3. Open a Pull Request into main
4. Ensure all CI checks pass

## Local checks
```bash
ruff check .
ruff format --check .
cd infra/terraform && terraform fmt -check -recursive && terraform init -backend=false && terraform validate
cd ../../dbt && dbt deps && dbt parse --profiles-dir ../.github/dbt_profiles --target ci