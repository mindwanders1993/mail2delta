"""
tests.test_delta_sink
~~~~~~~~~~~~~~~~~~~~~
Unit tests for DeltaSink dynamic SQL generation and key handling.
"""

from unittest.mock import MagicMock
import pandas as pd
from core.delta_sink import DeltaSink


def test_delta_sink_merge_composite_keys():
    mock_spark = MagicMock()
    mock_spark.catalog.tableExists.return_value = True

    sink = DeltaSink(mock_spark)

    records = [
        {"customer_code": "7910890000", "payment_due_label": "3/31 支払額", "payment_amount": 180123447.0}
    ]

    sink.save_merge(
        records=records,
        table_name="lakehouse_dev.schema.finops_ar_collections",
        merge_keys=["customer_code", "payment_due_label"],
    )

    # Verify spark.sql was called with the composite key conditions
    assert mock_spark.sql.called
    sql_query = mock_spark.sql.call_args[0][0]
    assert "target.customer_code = source.customer_code" in sql_query
    assert "target.payment_due_label = source.payment_due_label" in sql_query
    assert "MERGE INTO lakehouse_dev.schema.finops_ar_collections AS target" in sql_query
