"""
tests.test_transformers
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the Transformers layer (KeyValueParser, CurrencyCleaner, StrategyRouter).
"""

from transformers.currency_cleaner import CurrencyCleaner
from transformers.strategy_router import StrategyRouter


def test_currency_cleaner_global_rules():
    # US & UK
    assert CurrencyCleaner.clean("$1,500.50") == 1500.50
    assert CurrencyCleaner.clean("($250.00)") == -250.00
    assert CurrencyCleaner.clean("£10,000.00") == 10000.00

    # Euro & Japanese Yen & Accounting Negatives
    assert CurrencyCleaner.clean("€2,345.67") == 2345.67
    assert CurrencyCleaner.clean("¥180,123,447") == 180123447.0
    assert CurrencyCleaner.clean("￥1,500,000") == 1500000.0
    assert CurrencyCleaner.clean("¥-25,226,790") == -25226790.0
    assert CurrencyCleaner.clean("△500,000") == -500000.0
    assert CurrencyCleaner.clean("▲1,234,567") == -1234567.0
    assert CurrencyCleaner.clean("150,000円") == 150000.0

    # Null / Empty values
    assert CurrencyCleaner.clean("¥0") == 0.0
    assert CurrencyCleaner.clean("-") is None
    assert CurrencyCleaner.clean("#DIV/0!") is None
    assert CurrencyCleaner.clean(None) is None


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


def test_router_gfoot_with_greeting():
    yaml_config = """
    customers:
      GFoot:
        subject_regex: "G-FOOT|ジーフット|Aeon Sports.*G-foot"
        strategy: "key_value_table"
        merge_keys:
          - "customer_code"
          - "payment_due_label"
        params:
          customer_name: "GFoot"
          code_regex: "請求先コード"
          amount_regex: "当月入金額|入金額|支払額|振込額|振込金額"
          currency: "JPY"
          default_label: "入金額"
    """

    router = StrategyRouter(yaml_config)

    gfoot_email = {
        "id": "msg-gfoot-001",
        "subject": "【ご通知】株式会社ジーフット（G-FOOT）8月度お振込のお知らせ",
        "email_sender": "ar@gfoot.jp",
        "received_at": "2026-08-28T13:40:25Z",
        "html_body": """
        <p>お取引先様 各位</p>
        <p>株式会社ジーフット 経理担当よりご連絡申し上げます。<br>下記の内容にてお振込手続きを完了いたしました。</p>
        <p>請求先コード: 7930450000</p>
        <p>・請求締日: 2026/08/20<br>・総請求額: ¥84,200,000<br>・相殺控除額: △¥4,200,000<br>・当月入金額: ¥80,000,000</p>
        """,
    }

    record, merge_keys = router.process_email(gfoot_email)

    assert record is not None
    assert record["customer_name"] == "GFoot"
    assert record["customer_code"] == "7930450000"
    assert record["payment_amount"] == 80000000.0
    assert "当月入金額" in record["payment_due_label"]
    assert record["currency"] == "JPY"

