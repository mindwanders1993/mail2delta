"""
notebooks.finance_ops_collections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Production Databricks Job Orchestrator for Accounts Receivable (AR) Ingestion.
Runs on Databricks Serverless Compute.
"""

import os
import pandas as pd
from core.delta_sink import DeltaSink
from core.ms_graph_client import MSGraphClient
from router.strategy_router import StrategyRouter


def run_pipeline(spark_session) -> None:
    """
    Executes the end-to-end email ingestion pipeline:
    1. Computes High-Watermark date with a 7-day safety buffer.
    2. Fetches recent messages from MS Graph API.
    3. Filters out already processed email IDs (Gate 1).
    4. Routes new emails through the declarative YAML Strategy Router.
    5. Merges records into the production Delta table with business keys (Gate 2).
    """
    # 1. Configuration & Credentials (use Databricks Secrets or Env variables)
    tenant_id = os.getenv("AZURE_TENANT_ID", "YOUR_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID", "YOUR_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
    mailbox = os.getenv("MAILBOX_ADDRESS", "svc_global_bi@adidas.com")
    table_name = "lakehouse_dev.sadp_jpdna_pool_lhdev.finops_ar_collections"

    config_path = "configs/customers.yaml"
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

    # 3. Fetch from MS Graph
    emails = client.fetch_messages(top=50, filter_query=filter_query)
    print(f"📥 Fetched {len(emails)} candidate messages from inbox.")

    # 4. Process & Route Emails
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

    # 5. Gate 2: Idempotent MERGE into Delta Lake
    total_saved = 0
    for keys_tuple, records in grouped_records.items():
        keys_list = list(keys_tuple)
        count = sink.save_merge(
            records=records,
            table_name=table_name,
            merge_keys=keys_list,
            timezone="Asia/Tokyo",
        )
        total_saved += count

    print(f"🚀 Pipeline Complete: {total_saved} new/updated records merged into {table_name}.")


# Databricks Entrypoint
if "spark" in globals():
    run_pipeline(spark)
