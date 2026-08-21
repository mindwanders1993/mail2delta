"""Unit tests for msgraph_email_core.client."""

from unittest.mock import MagicMock, patch

from msgraph_email_core.client import MSGraphEmailClient
from msgraph_email_core.models import EmailMessage


@patch("msgraph_email_core.client.requests.Session")
def test_client_connect_and_auth(mock_session_cls):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "mock_test_token_123"}
    mock_session.post.return_value = mock_resp

    with MSGraphEmailClient(
        tenant_id="mock-tenant",
        client_id="mock-client",
        client_secret="mock-secret",
        mailbox="ar@example.com",
    ) as client:
        assert client.is_connected
        assert client._access_token == "mock_test_token_123"


@patch("msgraph_email_core.client.requests.Session")
def test_get_emails_incremental_delta(mock_session_cls):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # 1. Auth response
    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.json.return_value = {"access_token": "mock_token"}
    mock_session.post.return_value = auth_resp

    # 2. Delta query response
    delta_resp = MagicMock()
    delta_resp.status_code = 200
    delta_resp.json.return_value = {
        "value": [
            {
                "id": "msg-001",
                "subject": "Test Delta Subject",
                "from": {"emailAddress": {"address": "test@example.com", "name": "Tester"}},
                "toRecipients": [{"emailAddress": {"address": "ar@example.com"}}],
                "ccRecipients": [],
                "receivedDateTime": "2026-03-31T10:00:00Z",
                "body": {"content": "<p>Delta content</p>"},
                "hasAttachments": False,
                "isRead": True,
                "conversationId": "conv-001",
            }
        ],
        "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?$deltatoken=new_token_xyz_456",
    }
    mock_session.request.return_value = delta_resp

    client = MSGraphEmailClient("t", "c", "s", "mailbox@example.com")
    emails, new_token = client.get_emails_incremental()

    assert len(emails) == 1
    assert isinstance(emails[0], EmailMessage)
    assert emails[0].id == "msg-001"
    assert new_token == "new_token_xyz_456"
