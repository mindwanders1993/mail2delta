"""
src.core.delta_sink
~~~~~~~~~~~~~~~~~~~
Universal Databricks Delta Lake Writer.
Supports append and idempotent MERGE INTO upserts using arbitrary composite keys.
"""

import logging
from typing import Any
import pandas as pd

logger = logging.getLogger("core.delta_sink")


class DeltaSink:
    """
    Universal Delta Lake writer for Databricks environments.
    Agnostic of business logic, handles dynamic composite-key MERGE operations.
    """

    def __init__(self, spark_session: Any):
        """
        Initializes with an active PySpark session.

        Args:
            spark_session: Active Databricks SparkSession instance.
        """
        self.spark = spark_session

    def _prepare_spark_df(self, df: pd.DataFrame, timezone: str) -> Any:
        """Adds audit timestamp column using native PySpark or local fallback."""
        try:
            import pyspark.sql.functions as F
            spark_df = self.spark.createDataFrame(df)
            return spark_df.withColumn(
                "last_update_s",
                F.from_utc_timestamp(F.current_timestamp(), timezone),
            )
        except ImportError:
            df_with_ts = df.copy()
            df_with_ts["last_update_s"] = pd.Timestamp.now(tz=timezone)
            return self.spark.createDataFrame(df_with_ts)

    def save_append(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        table_name: str,
        timezone: str = "Asia/Tokyo",
    ) -> int:
        """
        Appends records to a Delta table with an ingestion timestamp.

        Args:
            records: List of dictionary records or a Pandas DataFrame.
            table_name: Target Delta Lake table name.
            timezone: Timezone for the audit timestamp column.

        Returns:
            Number of records appended.
        """
        if isinstance(records, list):
            if not records:
                return 0
            df = pd.DataFrame(records)
        else:
            df = records

        if df.empty:
            return 0

        spark_df = self._prepare_spark_df(df, timezone)
        spark_df.write.format("delta").mode("append").saveAsTable(table_name)
        logger.info("Successfully appended %d records to %s", len(df), table_name)
        return len(df)

    def save_merge(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        table_name: str,
        merge_keys: list[str] | str,
        timezone: str = "Asia/Tokyo",
    ) -> int:
        """
        Performs an idempotent MERGE INTO (Upsert) on a Delta table.
        Supports single primary keys or multi-column composite keys.

        Args:
            records: List of dictionary records or a Pandas DataFrame.
            table_name: Target Delta Lake table name.
            merge_keys: Single column name or list of column names defining uniqueness.
            timezone: Timezone for the audit timestamp column.

        Returns:
            Number of records merged.
        """
        if isinstance(records, list):
            if not records:
                return 0
            df = pd.DataFrame(records)
        else:
            df = records

        if df.empty:
            return 0

        if isinstance(merge_keys, str):
            merge_keys = [merge_keys]

        spark_df = self._prepare_spark_df(df, timezone)

        # Check if table exists
        table_exists = False
        try:
            table_exists = self.spark.catalog.tableExists(table_name)
        except Exception:
            pass

        if not table_exists:
            spark_df.write.format("delta").mode("append").saveAsTable(table_name)
            logger.info("Table %s did not exist. Created and inserted %d records.", table_name, len(df))
            return len(df)

        temp_view = f"temp_{table_name.replace('.', '_')}"
        spark_df.createOrReplaceTempView(temp_view)

        join_conditions = " AND ".join([f"target.{col} = source.{col}" for col in merge_keys])

        merge_sql = f"""
            MERGE INTO {table_name} AS target
            USING {temp_view} AS source
            ON {join_conditions}
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """

        self.spark.sql(merge_sql)
        logger.info("Successfully merged %d records into %s on keys: %s", len(df), table_name, merge_keys)
        return len(df)
