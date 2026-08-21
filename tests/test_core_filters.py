"""Unit tests for msgraph_email_core.filters."""

from datetime import datetime, timezone

from msgraph_email_core.filters import EmailFilter
from msgraph_email_core.models import EmailMessage


def _create_mock_emails():
    return [
        EmailMessage(
            id="1",
            subject="【月次報告】加茂商事 3月分",
            sender="partner1@kamoshoji.co.jp",
            sender_name="Kamo Shoji Staff",
            recipients=["ar@example.com"],
            cc=[],
            received_at=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            body_html="<p>Table</p>",
            body_text="Table",
            has_attachments=False,
            is_read=False,
            conversation_id="c1",
        ),
        EmailMessage(
            id="2",
            subject="AEON Sports Mega 振込予定のご案内",
            sender="billing@mega.co.jp",
            sender_name="Mega Accounting",
            recipients=["ar@example.com"],
            cc=[],
            received_at=datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc),
            body_html="<p>Table</p>",
            body_text="Table",
            has_attachments=True,
            is_read=True,
            conversation_id="c2",
        ),
        EmailMessage(
            id="3",
            subject="Weekly Newsletter",
            sender="news@random.com",
            sender_name="Newsletter",
            recipients=["all@example.com"],
            cc=[],
            received_at=datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc),
            body_html="<p>News</p>",
            body_text="News",
            has_attachments=False,
            is_read=False,
            conversation_id="c3",
        ),
    ]


def test_filter_by_sender():
    emails = _create_mock_emails()
    res = EmailFilter(emails).by_sender("mega.co.jp").results()
    assert len(res) == 1
    assert res[0].id == "2"


def test_filter_by_subject_contains():
    emails = _create_mock_emails()
    res = EmailFilter(emails).by_subject_contains("月次報告").results()
    assert len(res) == 1
    assert res[0].id == "1"


def test_filter_by_subject_regex():
    emails = _create_mock_emails()
    res = EmailFilter(emails).by_subject_regex(r"(加茂商事|Mega)").results()
    assert len(res) == 2


def test_filter_by_date_range():
    emails = _create_mock_emails()
    start = datetime(2026, 3, 16, tzinfo=timezone.utc)
    end = datetime(2026, 3, 21, tzinfo=timezone.utc)
    res = EmailFilter(emails).by_date_range(start, end).results()
    assert len(res) == 1
    assert res[0].id == "2"


def test_filter_chaining():
    emails = _create_mock_emails()
    filtered = (
        EmailFilter(emails)
        .by_unread_only()
        .by_has_attachments(False)
        .results()
    )
    assert len(filtered) == 2
    assert {e.id for e in filtered} == {"1", "3"}
