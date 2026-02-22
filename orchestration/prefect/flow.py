import os
import subprocess
from datetime import timedelta

from dotenv import load_dotenv
from prefect import flow, get_run_logger, task
from prefect.tasks import task_input_hash

import snowflake.connector

load_dotenv()


def _sf_connect():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
    )


@task(
    retries=2,
    retry_delay_seconds=15,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=5),
)
def snowflake_preflight():
    """
    Verify we can connect, and that role/warehouse are correct.
    Also validates RAW tables exist (EMAIL_EVENTS_RAW, INVENTORY_RAW).
    """
    logger = get_run_logger()
    con = _sf_connect()
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE();"
        )
        row = cur.fetchone()
        logger.info(f"Snowflake context: user={row[0]} role={row[1]} wh={row[2]} db={row[3]}")

        # Ensure schemas exist
        cur.execute("SHOW SCHEMAS LIKE 'RAW' IN DATABASE DP_MAILBLAZE_DEMO_DEV_DB;")
        logger.info(f"RAW schema rows: {cur.rowcount}")

        # Ensure the RAW tables exist
        cur.execute("SHOW TABLES LIKE 'EMAIL_EVENTS_RAW' IN SCHEMA DP_MAILBLAZE_DEMO_DEV_DB.RAW;")
        if cur.rowcount == 0:
            raise RuntimeError("Missing RAW table: DP_MAILBLAZE_DEMO_DEV_DB.RAW.EMAIL_EVENTS_RAW")

        cur.execute("SHOW TABLES LIKE 'INVENTORY_RAW' IN SCHEMA DP_MAILBLAZE_DEMO_DEV_DB.RAW;")
        if cur.rowcount == 0:
            raise RuntimeError("Missing RAW table: DP_MAILBLAZE_DEMO_DEV_DB.RAW.INVENTORY_RAW")

        logger.info("Snowflake preflight OK.")
    finally:
        con.close()


@task(retries=2, retry_delay_seconds=15)
def run_dbt(cmd: str):
    """
    Runs dbt inside the repo. Assumes dbt project lives in ./dbt
    and profiles.yml exists in ~/.dbt/profiles.yml (mounted in container implicitly).
    """
    logger = get_run_logger()
    full_cmd = ["bash", "-lc", cmd]
    logger.info(f"Running: {cmd}")
    proc = subprocess.run(full_cmd, capture_output=True, text=True)
    logger.info(proc.stdout)
    if proc.returncode != 0:
        logger.error(proc.stderr)
        raise RuntimeError(f"dbt command failed: {cmd}")
    return proc.stdout


@task
def notify_failure(message: str):
    """
    Mock Slack notification: prints message.
    If SLACK_WEBHOOK_URL is set, you can later implement real post.
    """
    logger = get_run_logger()
    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if webhook:
        logger.warning("SLACK_WEBHOOK_URL set, but this demo uses mock notify only.")
    logger.error(f"[MOCK NOTIFY] {message}")


@flow(name="dp-mailblaze-demo-dev-flow")
def mailblaze_flow():
    logger = get_run_logger()

    try:
        snowflake_preflight()

        # dbt deps (safe to run repeatedly)
        run_dbt("cd /app/dbt && dbt deps")

        # dbt snapshot (if you have snapshots configured)
        # If you removed snapshots, comment this line out.
        run_dbt("cd /app/dbt && dbt snapshot")

        # dbt run (build models)
        run_dbt("cd /app/dbt && dbt run")

        # dbt test
        run_dbt("cd /app/dbt && dbt test")

        logger.info("Flow completed successfully.")

    except Exception as e:
        notify_failure(f"Flow failed: {e}")
        raise


if __name__ == "__main__":
    mailblaze_flow()
