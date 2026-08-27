"""
tests.test_router_and_strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for KeyValueStrategy and StrategyRouter matching.
"""

from router.strategy_router import StrategyRouter


def test_router_kamoshoji_corporate_email():
    yaml_config = """
    customers:
      KamoShoji:
        subject_regex: "KamoShoji|加茂商事"
        strategy: "key_value_table"
        merge_keys:
          - "customer_code"
          - "payment_due_label"
        params:
          code_regex: "請求先コード"
          amount_regex: "支払額"
          currency: "JPY"
          default_label: "3/31 支払額"
    """

    router = StrategyRouter(yaml_config)

    actual_email = {
        "id": "AAMkAD-kamo-msg-123",
        "subject": "<月次報告> 加茂商事様 2026/2/28締",
        "email_sender": "svc_global_bi@adidas.com",
        "received_at": "2026-08-26T00:00:00Z",
        "html_body": """
        <p>加茂商事様 2026/2/28締め</p>
        <p>請求先コード: 7910890000</p>
        <table>
            <tr><td>2/28締 総請求金額</td><td>¥632,491,856</td></tr>
            <tr><td>3/2入金分</td><td>¥222,521,781</td></tr>
            <tr><td>3/31 支払額</td><td>¥180,123,447</td><td>(2026/6/30現金化)</td></tr>
        </table>
        """,
    }

    record, merge_keys = router.process_email(actual_email)

    assert record is not None
    assert record["customer_name"] == "KamoShoji"
    assert record["customer_code"] == "7910890000"
    assert record["payment_amount"] == 180123447.0
    assert record["currency"] == "JPY"
    assert record["email_unique_id"] == "AAMkAD-kamo-msg-123"
    assert merge_keys == ["customer_code", "payment_due_label"]


def test_router_imoto_prefix_code():
    yaml_config = """
    customers:
      Imoto:
        subject_regex: "イモト|Imoto"
        strategy: "key_value_table"
        merge_keys:
          - "customer_code"
          - "payment_due_label"
        params:
          code_regex: "コード"
          amount_regex: "支払額"
          prefix_code: "79"
          currency: "JPY"
    """

    router = StrategyRouter(yaml_config)

    imoto_email = {
        "id": "msg-imoto-999",
        "subject": "イモト 3月度ご案内",
        "email_sender": "ar@imoto.jp",
        "received_at": "2026-08-26T05:00:00Z",
        "html_body": "<p>コード: 1089555</p><p>3/31 支払額: ¥50,000,000</p>",
    }

    record, merge_keys = router.process_email(imoto_email)

    assert record is not None
    assert record["customer_name"] == "Imoto"
    assert record["customer_code"] == "791089555"
    assert record["payment_amount"] == 50000000.0
