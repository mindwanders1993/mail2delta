"""
tests.test_ar_pipeline
~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the universal, multi-region YAML configurable engine.
"""

from core.email_ingestion_utils import CurrencyUtility, YamlConfigUtility


def test_global_currency_cleaner():
    # US / UK Dollars & Pounds
    assert CurrencyUtility.clean("$1,500.50") == 1500.50
    assert CurrencyUtility.clean("($250.00)") == -250.00
    assert CurrencyUtility.clean("£10,000.00") == 10000.00
    assert CurrencyUtility.clean("-£500.00") == -500.00
    
    # European Euros
    assert CurrencyUtility.clean("€2,345.67") == 2345.67
    
    # Japanese Yen & Asian Accounting
    assert CurrencyUtility.clean("¥180,123,447") == 180123447.0
    assert CurrencyUtility.clean("￥1,500,000") == 1500000.0
    assert CurrencyUtility.clean("¥-25,226,790") == -25226790.0
    assert CurrencyUtility.clean("△500,000") == -500000.0
    assert CurrencyUtility.clean("▲1,234,567") == -1234567.0
    
    # Null & Empty values
    assert CurrencyUtility.clean("¥0") == 0.0
    assert CurrencyUtility.clean("-") is None
    assert CurrencyUtility.clean("#DIV/0!") is None
    assert CurrencyUtility.clean("N/A") is None


def test_actual_kamoshoji_corporate_email():
    yaml_str = """
    customers:
      KamoShoji:
        subject_regex: "KamoShoji|加茂商事"
        code_regex: "請求先コード"
        amount_regex: "支払額"
        currency: "JPY"
        default_label: "3/31 支払額"
    """
    config = YamlConfigUtility.load_config(yaml_str)

    actual_email = {
        "subject": "<月次報告> 加茂商事様 2026/2/28締",
        "email_sender": "svc_global_bi@adidas.com",
        "received_at": "2026-08-26T00:00:00Z",
        "html_body": """
        <p>浦尻さん　稲葉さん<br>
        お疲れ様です。<br>
        加茂商事様 2026/2/28締め->2026/3/31 でんさいで支払予定の売掛金残高をご報告いたします。</p>
        <p>取引先名: 加茂商事 (株)<br>
        請求先コード: 7910890000<br>
        締め日: 末日<br>
        支払方法: 翌月末日 90日でんさい (納品額を3分割し3ヶ月の分割)</p>
        <table>
            <tr><td></td><td>7910890000</td></tr>
            <tr><td>2/28締 総請求金額</td><td>¥632,491,856</td></tr>
            <tr><td>3/2入金分</td><td>¥222,521,781</td></tr>
            <tr><td>3/31 支払額</td><td>¥180,123,447</td><td>(2026/6/30現金化)</td></tr>
        </table>
        """
    }

    record = YamlConfigUtility.parse_email(actual_email, config)
    assert record is not None
    assert record["customer_name"] == "KamoShoji"
    assert record["customer_code"] == "7910890000"
    assert record["payment_amount"] == 180123447.0
    assert record["currency"] == "JPY"
