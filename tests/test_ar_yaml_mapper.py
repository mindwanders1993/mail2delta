"""Unit tests for ar_collections_pipeline.yaml_mapper."""

from datetime import datetime, timezone

import yaml

from ar_collections_pipeline.yaml_mapper import YamlMappingParser
from msgraph_email_core.models import EmailMessage


def _get_test_config():
    yaml_str = """
    customers:
      KamoShoji:
        match:
          subject_regex: '.*加茂商事.*'
        strategy: vertical_key_value
        code_source:
          table_index: 0
          target_regex: '請求先コード'
        amount_source:
          table_index: 0
          target_regex: '.*(支払額|入金額).*'

      Mega:
        match:
          subject_regex: '.*(Mega|メガ).*'
        strategy: zip_columns_across_tables
        code_source:
          table_index: 0
          target_regex: '請求先コード'
        amount_source:
          table_index: 1
          target_regex: '.*(振込金額|支払額).*'

      Himaraya:
        match:
          subject_regex: '.*ヒマラヤ.*'
        strategy: zip_headers_to_row
        code_source:
          table_index: 1
        amount_source:
          table_index: 1
          target_regex: '.*(支払額|入金額).*'

      Imoto:
        match:
          subject_regex: '.*イモト.*'
        strategy: zip_rows_in_same_table
        code_source:
          table_index: 1
          target_regex: '^コード$'
        amount_source:
          table_index: 1
          target_regex: '.*(支払額|入金額).*'
    """
    return yaml.safe_load(yaml_str)["customers"]


def test_strategy_vertical_key_value():
    config = _get_test_config()
    parser = YamlMappingParser(config)

    html = """
    <table>
        <tr><td>項目</td><td>内容</td></tr>
        <tr><td>請求先コード</td><td>7910890000</td></tr>
        <tr><td>3/31 支払額</td><td>¥144,590,047</td></tr>
    </table>
    """
    email = EmailMessage(
        id="kamo-1",
        subject="【加茂商事】2026年3月度 お支払明細",
        sender="kamo@example.com",
        sender_name="Kamo",
        recipients=["ar@example.com"],
        cc=[],
        received_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        body_html=html,
        body_text="",
        has_attachments=False,
        is_read=True,
        conversation_id="conv-kamo",
    )

    records = parser.parse(email)
    assert len(records) == 1
    rec = records[0]
    assert rec.customer_name == "KamoShoji"
    assert rec.billing_code == "7910890000"
    assert rec.payment_amount == 144590047.0
    assert rec.report_year == 2026
    assert rec.report_month == 3
    assert rec.parse_status == "SUCCESS"


def test_strategy_zip_columns_across_tables():
    config = _get_test_config()
    parser = YamlMappingParser(config)

    html = """
    <div>
        <table id="t0">
            <tr><td>区分</td><td>コード1</td><td>コード2</td></tr>
            <tr><td>請求先コード</td><td>10260000</td><td>10260001</td></tr>
        </table>
        <table id="t1">
            <tr><td>区分</td><td>金額1</td><td>金額2</td></tr>
            <tr><td>3/31 振込金額</td><td>¥1,500,000</td><td>¥900,000</td></tr>
        </table>
    </div>
    """
    email = EmailMessage(
        id="mega-1",
        subject="AEON Sports Mega 3月分ご案内",
        sender="mega@example.com",
        sender_name="Mega",
        recipients=["ar@example.com"],
        cc=[],
        received_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        body_html=html,
        body_text="",
        has_attachments=False,
        is_read=True,
        conversation_id="conv-mega",
    )

    records = parser.parse(email)
    assert len(records) == 2
    assert records[0].billing_code == "10260000"
    assert records[0].payment_amount == 1500000.0
    assert records[1].billing_code == "10260001"
    assert records[1].payment_amount == 900000.0


def test_strategy_zip_headers_to_row():
    config = _get_test_config()
    parser = YamlMappingParser(config)

    html = """
    <div>
        <table><tr><td>Overview</td></tr></table>
        <table>
            <tr><td>項目</td><td>79108601</td><td>79108602</td></tr>
            <tr><td>3/31 支払額</td><td>¥2,000,000</td><td>△500,000</td></tr>
        </table>
    </div>
    """
    email = EmailMessage(
        id="himaraya-1",
        subject="【ヒマラヤ】3月度 お支払額",
        sender="hima@example.com",
        sender_name="Himaraya",
        recipients=["ar@example.com"],
        cc=[],
        received_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        body_html=html,
        body_text="",
        has_attachments=False,
        is_read=True,
        conversation_id="conv-hima",
    )

    records = parser.parse(email)
    assert len(records) == 2
    assert records[0].billing_code == "79108601"
    assert records[0].payment_amount == 2000000.0
    assert records[1].billing_code == "79108602"
    assert records[1].payment_amount == -500000.0


def test_strategy_zip_rows_in_same_table():
    config = _get_test_config()
    parser = YamlMappingParser(config)

    html = """
    <div>
        <table><tr><td>Meta</td></tr></table>
        <table>
            <tr><td>項目</td><td>店舗A</td><td>店舗B</td></tr>
            <tr><td>コード</td><td>3344001</td><td>3344002</td></tr>
            <tr><td>3/31 支払額</td><td>¥500,000</td><td>¥750,000</td></tr>
        </table>
    </div>
    """
    email = EmailMessage(
        id="imoto-1",
        subject="【イモト】3月度 ご連絡",
        sender="imoto@example.com",
        sender_name="Imoto",
        recipients=["ar@example.com"],
        cc=[],
        received_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        body_html=html,
        body_text="",
        has_attachments=False,
        is_read=True,
        conversation_id="conv-imoto",
    )

    records = parser.parse(email)
    assert len(records) == 2
    assert records[0].billing_code == "3344001"
    assert records[0].payment_amount == 500000.0
    assert records[1].billing_code == "3344002"
    assert records[1].payment_amount == 750000.0
