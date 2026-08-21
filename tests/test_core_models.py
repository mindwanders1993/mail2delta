"""Unit tests for msgraph_email_core.models."""

from datetime import datetime, timezone

from msgraph_email_core.models import AttachmentItem, EmailMessage


def test_email_message_serialization():
    dt = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)
    msg = EmailMessage(
        id="msg-123",
        subject="Test Subject",
        sender="sender@example.com",
        sender_name="Test Sender",
        recipients=["recp@example.com"],
        cc=[],
        received_at=dt,
        body_html="<p>Hello World</p>",
        body_text="Hello World",
        has_attachments=False,
        is_read=True,
        conversation_id="conv-123",
    )

    d = msg.to_dict()
    assert d["id"] == "msg-123"
    assert d["subject"] == "Test Subject"
    assert d["sender"] == "sender@example.com"
    assert d["received_at"] == "2026-03-31T12:00:00+00:00"
    assert d["has_attachments"] is False


def test_attachment_item_stream(tmp_path):
    content = b"Mock PDF attachment binary content"
    att = AttachmentItem(
        id="att-1",
        name="invoice.pdf",
        content_type="application/pdf",
        size_bytes=len(content),
        content_bytes=content,
    )

    stream = att.to_bytes_io()
    assert stream.read() == content

    target_file = tmp_path / "invoice.pdf"
    att.save_to_path(str(target_file))
    assert target_file.read_bytes() == content
