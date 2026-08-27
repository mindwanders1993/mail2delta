"""
tests.test_ms_graph_client
~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for MSGraphClient with mocked HTTP requests.
"""

from unittest.mock import MagicMock, patch
from core.ms_graph_client import MSGraphClient


@patch("requests.post")
def test_get_token_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "access_token": "fake-token-12345",
        "expires_in": 3600,
    }

    client = MSGraphClient("tenant-id", "client-id", "secret", "inbox@example.com")
    token = client.get_token()

    assert token == "fake-token-12345"
    assert client._token == "fake-token-12345"


@patch("requests.get")
@patch("requests.post")
def test_fetch_messages_success(mock_post, mock_get):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "fake-token", "expires_in": 3600}

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "value": [
            {
                "id": "msg-001",
                "subject": "<月次報告> 加茂商事様",
                "from": {"emailAddress": {"address": "svc@adidas.com", "name": "Service Account"}},
                "receivedDateTime": "2026-08-26T10:00:00Z",
                "body": {"content": "<p>Hello</p>"},
                "hasAttachments": False,
                "isRead": True,
                "conversationId": "conv-1",
            }
        ]
    }

    client = MSGraphClient("tenant-id", "client-id", "secret", "inbox@example.com")
    messages = client.fetch_messages(top=10, filter_query="receivedDateTime ge 2026-08-01")

    assert len(messages) == 1
    msg = messages[0]
    assert msg["id"] == "msg-001"
    assert msg["subject"] == "<月次報告> 加茂商事様"
    assert msg["email_sender"] == "svc@adidas.com"
    assert msg["received_at"] == "2026-08-26T10:00:00Z"
