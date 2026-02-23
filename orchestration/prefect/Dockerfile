FROM python:3.11-slim

WORKDIR /app

# System deps for dbt + git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install Prefect + connectors
# (context is orchestration/prefect, so requirements.txt is at ./requirements.txt)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install dbt (use same adapter you already used successfully)
RUN pip install --no-cache-dir dbt-core==1.8.6 dbt-snowflake==1.8.4

# Copy Prefect project files into image (everything inside orchestration/prefect/)
COPY . /app

# Default: run flow module (docker-compose can override command as needed)
CMD ["python", "flow.py"]