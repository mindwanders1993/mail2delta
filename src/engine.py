import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yaml
from azure.identity.aio import ClientSecretCredential
from bs4 import BeautifulSoup
from msgraph import GraphServiceClient
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)

from .extractors import HTMLTableExtractor, MetadataExtractor


class EmailPipelineEngine:
    """
    Generic, template-driven runner for ingesting, parsing, and storing email data.
    """

    def __init__(self, config_path_or_dict: Any):
        if isinstance(config_path_or_dict, str):
            with open(config_path_or_dict, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        elif isinstance(config_path_or_dict, dict):
            self.config = config_path_or_dict
        else:
            raise ValueError("Config must be a file path string or a Python dict.")

        self.metadata_extractor = MetadataExtractor(self.config.get("metadata_extractors", []))
        self.table_extractor = HTMLTableExtractor(self.config.get("table_extraction", {}))

    def _resolve_client_secret(self) -> str:
        """Resolves secret from Databricks dbutils or environment variables."""
        conn = self.config["connection"]
        secret_scope = conn.get("secret_scope")
        secret_key = conn.get("secret_key")

        # 1. Try Databricks dbutils
        try:
            from pyspark.dbutils import DBUtils
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            dbutils = DBUtils(spark)
            return dbutils.secrets.get(scope=secret_scope, key=secret_key)
        except Exception:
            pass

        # 2. Fallback to direct string or env var
        return conn.get("client_secret") or os.getenv(secret_key, "")

    async def execute(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Runs the extraction pipeline asynchronously.
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (extracted_data_df, audit_log_df)
        """
        conn = self.config["connection"]
        filt = self.config.get("filter", {})
        
        client_secret = self._resolve_client_secret()
        credential = ClientSecretCredential(conn["tenant_id"], conn["client_id"], client_secret)
        client = GraphServiceClient(credential)

        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=filt.get("top_n", 20),
            select=["id", "conversationId", "subject", "from", "receivedDateTime", "body", "hasAttachments", "isRead"],
            orderby=["receivedDateTime DESC"]
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        messages = await client.users.by_user_id(conn["mailbox"]).messages.get(request_configuration=request_config)

        extracted_rows = []
        audit_logs = []
        process_time = datetime.now(timezone.utc)
        allowed_senders = filt.get("sender_contains", [])
        subject_filter = filt.get("subject_must_contain", "").lower()

        if messages and messages.value:
            for msg in messages.value:
                msg_id = msg.id
                subject = msg.subject or ""
                sender = msg.from_.email_address.address if msg.from_ and msg.from_.email_address else "UNKNOWN"
                received_at = str(msg.received_date_time)
                body_html = msg.body.content if msg.body else ""
                plain_text = BeautifulSoup(body_html, "html.parser").get_text() if body_html else ""

                # Subject and Sender filter check
                if subject_filter and subject_filter not in subject.lower():
                    continue
                if allowed_senders and not any(s.lower() in sender.lower() for s in allowed_senders):
                    continue

                # 1. Regex Metadata Extraction
                meta = self.metadata_extractor.extract(subject, plain_text)

                # 2. HTML Table Extraction
                tables = self.table_extractor.extract_tables(body_html)
                rows_count = 0
                status = "SUCCESS" if tables else ("METADATA_ONLY" if meta else "NO_MATCH")

                if tables:
                    for idx, table_df in enumerate(tables):
                        table_df["pipeline_name"] = self.config.get("pipeline_name")
                        table_df["email_message_id"] = msg_id
                        table_df["email_subject"] = subject
                        table_df["email_sender"] = sender
                        table_df["email_received_at"] = received_at
                        for k, v in meta.items():
                            table_df[f"extracted_{k}"] = v
                        table_df["table_index"] = idx

                        rows_count += len(table_df)
                        extracted_rows.append(table_df)

                # 3. Build Audit Record
                audit_logs.append({
                    "pipeline_name": self.config.get("pipeline_name"),
                    "message_id": msg_id,
                    "conversation_id": msg.conversation_id,
                    "sender": sender,
                    "subject": subject,
                    "received_at": received_at,
                    "processed_at": process_time,
                    "status": status,
                    "tables_found": len(tables),
                    "rows_extracted": rows_count,
                    "extracted_metadata": str(meta),
                    "has_attachments": msg.has_attachments
                })

        await credential.close()

        data_df = pd.concat(extracted_rows, ignore_index=True) if extracted_rows else pd.DataFrame()
        audit_df = pd.DataFrame(audit_logs)
        return data_df, audit_df

    def run_and_save_to_delta(self, spark_session) -> tuple[Any, Any]:
        """Runs the pipeline and writes both extracted data and audit logs to Delta Lake."""
        loop = asyncio.get_event_loop()
        data_df, audit_df = loop.run_until_complete(self.execute())

        sink = self.config.get("sink", {})
        save_mode = sink.get("save_mode", "append")

        # 1. Save Audit Log Table
        spark_audit_df = None
        if not audit_df.empty:
            spark_audit_df = spark_session.createDataFrame(audit_df)
            spark_audit_df.write.format("delta").mode(save_mode).option("mergeSchema", "true").saveAsTable(sink["audit_table"])

        # 2. Save Extracted Data Table
        spark_data_df = None
        if not data_df.empty:
            spark_data_df = spark_session.createDataFrame(data_df)
            spark_data_df.write.format("delta").mode(save_mode).option("mergeSchema", "true").saveAsTable(sink["data_table"])

        return spark_data_df, spark_audit_df
