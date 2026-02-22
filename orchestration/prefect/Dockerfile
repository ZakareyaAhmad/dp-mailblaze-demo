FROM python:3.11-slim

WORKDIR /app

# System deps for dbt + git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Prefect + connectors
COPY orchestration/prefect/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install dbt (use same adapter you already used successfully)
RUN pip install --no-cache-dir dbt-core==1.8.6 dbt-snowflake==1.8.4

# Copy repo into image (so dbt project is available)
COPY . /app

# Default: run flow module (docker-compose will override command as needed)
CMD ["python", "orchestration/prefect/flow.py"]