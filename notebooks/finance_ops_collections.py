"""
notebooks.finance_ops_collections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Production Databricks Job Orchestrator for Accounts Receivable (AR) Ingestion.
Decoupled Architecture: Connectors -> Transformers -> Sinks.
"""

import os
import sys
import pandas as pd
from connectors.ms_graph_client import MSGraphClient
from sinks.delta_sink import DeltaSink
from transformers.strategy_router import StrategyRouter


def get_credential(key: str, default: str | None = None) -> str:
    """
    Retrieves credentials from environment variables first,
    with fallback to Databricks Secret Scope if available.
    """
    val = os.getenv(key)
    if val:
        return val

    # Databricks dbutils secrets fallback
    try:
        import IPython
        dbutils = IPython.get_ipython().user_ns.get("dbutils")
        if dbutils:
            secret_scope = os.getenv("DATABRICKS_SECRET_SCOPE", "finops_m365")
            return dbutils.secrets.get(scope=secret_scope, key=key.lower())
    except Exception:
        pass

    if default is not None:
        return default

    raise ValueError(
        f"Missing required configuration '{key}'. "
        f"Please set environment variable '{key}' or configure Databricks secret scope."
    )


def run_pipeline(spark_session) -> None:
    """
    Executes the end-to-end email ingestion pipeline:
    1. Reads environment variables for Azure & Databricks configuration.
    2. Computes High-Watermark date with a 7-day safety buffer.
    3. Fetches candidate messages from MS Graph API via Connectors.
    4. Filters out already processed email IDs (Gate 1).
    5. Routes new emails through Transformers Strategy Router.
    6. Merges records into the production Delta table via Sinks (Gate 2).
    """
    # 1. Environment-Driven Configuration
    tenant_id = get_credential("AZURE_TENANT_ID")
    client_id = get_credential("AZURE_CLIENT_ID")
    client_secret = get_credential("AZURE_CLIENT_SECRET")

    mailbox = os.getenv("MAILBOX_ADDRESS", "svc_global_bi@adidas.com")
    table_name = os.getenv(
        "DELTA_TABLE_NAME",
        "lakehouse_dev.sadp_jpdna_pool_lhdev.finops_ar_collections",
    )
    config_path = os.getenv("YAML_CONFIG_PATH", "configs/customers.yaml")
    pipeline_timezone = os.getenv("PIPELINE_TIMEZONE", "Asia/Tokyo")

    # Decoupled components initialization
    router = StrategyRouter(config_path)
    client = MSGraphClient(tenant_id, client_id, client_secret, mailbox)
    sink = DeltaSink(spark_session)

    # 2. Gate 1: Determine High-Watermark & Load Recent Processed IDs
    filter_query = None
    processed_ids_query = f"SELECT email_unique_id FROM {table_name}"

    try:
        max_row = spark_session.sql(
            f"SELECT MAX(email_received_at) FROM {table_name}"
        ).collect()
        if max_row and max_row[0][0]:
            max_dt = pd.to_datetime(max_row[0][0])
            watermark_dt = max_dt - pd.Timedelta(days=7)
            watermark_iso = watermark_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            filter_query = f"receivedDateTime ge {watermark_iso}"
            processed_ids_query = (
                f"SELECT email_unique_id FROM {table_name} "
                f"WHERE email_received_at >= '{watermark_iso}'"
            )
            print(f"⏰ High Watermark Active: Fetching emails since {watermark_iso}")
    except Exception as err:
        print(f"ℹ️ Table check notice (first run or table empty): {err}")

    # Load known IDs into a set
    try:
        id_rows = spark_session.sql(processed_ids_query).collect()
        processed_ids = {r[0] for r in id_rows if r[0]}
    except Exception:
        processed_ids = set()

    # 3. Fetch candidate messages from MS Graph (Connectors Layer)
    emails = client.fetch_messages(top=50, filter_query=filter_query)
    print(f"📥 Fetched {len(emails)} candidate messages from inbox.")

    # 4. Process & Route Emails (Transformers Layer)
    grouped_records: dict[tuple, list[dict]] = {}

    for email in emails:
        email_id = email.get("id")
        if email_id in processed_ids:
            continue

        record, merge_keys = router.process_email(email)
        if record:
            keys_tuple = tuple(merge_keys)
            if keys_tuple not in grouped_records:
                grouped_records[keys_tuple] = []
            grouped_records[keys_tuple].append(record)

    # 5. Gate 2: Idempotent MERGE into Delta Lake (Sinks Layer)
    total_saved = 0
    for keys_tuple, records in grouped_records.items():
        keys_list = list(keys_tuple)
        count = sink.save_merge(
            records=records,
            table_name=table_name,
            merge_keys=keys_list,
            timezone=pipeline_timezone,
        )
        total_saved += count

    print(f"🚀 Pipeline Complete: {total_saved} new/updated records merged into {table_name}.")


# Databricks Entrypoint
if "spark" in globals():
    run_pipeline(spark)
