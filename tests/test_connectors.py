"""
tests.test_connectors
~~~~~~~~~~~~~~~~~~~~~
Unit tests for the Connectors layer (MSGraphClient & HTMLParser).
"""

from unittest.mock import patch
from connectors.html_parser import HTMLParser
from connectors.ms_graph_client import MSGraphClient


@patch("requests.post")
def test_msgraph_auth_token_caching(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "access_token": "token-xyz-123",
        "expires_in": 3600,
    }

    client = MSGraphClient("tenant", "client", "secret", "inbox@example.com")
    token1 = client.get_token()
    token2 = client.get_token()

    assert token1 == "token-xyz-123"
    assert token2 == "token-xyz-123"
    # Verify cached token was reused without making a second HTTP request
    assert mock_post.call_count == 1


@patch("requests.get")
@patch("requests.post")
def test_msgraph_fetch_messages(mock_post, mock_get):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "token", "expires_in": 3600}

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "value": [
            {
                "id": "email-001",
                "subject": "Monthly Remittance",
                "from": {"emailAddress": {"address": "ar@client.com", "name": "AR Dept"}},
                "receivedDateTime": "2026-08-27T10:00:00Z",
                "body": {"content": "<p>Payment Notice</p>"},
                "hasAttachments": False,
                "isRead": True,
                "conversationId": "conv-001",
            }
        ]
    }

    client = MSGraphClient("tenant", "client", "secret", "inbox@example.com")
    emails = client.fetch_messages(top=5)

    assert len(emails) == 1
    assert emails[0]["id"] == "email-001"
    assert emails[0]["email_sender"] == "ar@client.com"
    assert emails[0]["html_body"] == "<p>Payment Notice</p>"


def test_html_parser_to_text():
    html = "<p>Header Line</p><table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
    text = HTMLParser.html_to_text(html)
    assert "Header Line" in text
    assert "Cell 1" in text
    assert "Cell 2" in text


def test_html_parser_extract_tables():
    html = """
    <table>
        <tr><th>Customer</th><th>Amount</th></tr>
        <tr><td>KamoShoji</td><td>¥180,000,000</td></tr>
    </table>
    """
    tables = HTMLParser.extract_tables(html)
    assert len(tables) == 1
    df = tables[0]
    assert df.shape == (2, 2)
    assert df.iloc[0, 0] == "Customer"
    assert df.iloc[1, 1] == "¥180,000,000"
