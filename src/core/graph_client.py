"""
src.core.graph_client
~~~~~~~~~~~~~~~~~~~~~
Universal Microsoft 365 OAuth2 Client and Email Fetcher using MS Graph API.
Handles Client Credentials flow, token caching/auto-refresh, and robust email retrieval.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any
import requests

logger = logging.getLogger("core.graph_client")


class MSGraphEmailClient:
    """
    Client for interacting with Microsoft Graph API using Client Credentials grant.
    Reusable across ANY email ingestion project.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        mailbox: str,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.mailbox = mailbox
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_access_token(self) -> str:
        """Retrieves and auto-refreshes OAuth2 access token."""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code != 200:
            logger.error("Authentication failed: %s", resp.text)
            raise RuntimeError(f"MS Entra ID Authentication Error: {resp.status_code} - {resp.text}")

        data = resp.json()
        self._token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in
        return self._token

    def fetch_emails(
        self,
        top: int = 50,
        subject_contains: str | None = None,
        received_after: datetime | None = None,
        folder: str = "Inbox",
    ) -> list[dict[str, Any]]:
        """
        Fetches emails from the target mailbox with optional filtering.

        Args:
            top: Maximum number of emails to retrieve.
            subject_contains: Substring filter for email subject.
            received_after: Datetime threshold for email received time.
            folder: Mail folder name (default: "Inbox").

        Returns:
            List of standardized email dictionaries.
        """
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"https://graph.microsoft.com/v1.0/users/{self.mailbox}/mailFolders/{folder}/messages"
        
        params: dict[str, Any] = {
            "$top": top,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,body,hasAttachments,isRead,conversationId",
        }

        filter_clauses = []
        if received_after:
            filter_clauses.append(f"receivedDateTime ge {received_after.isoformat()}")
        if subject_contains:
            filter_clauses.append(f"contains(subject, '{subject_contains}')")

        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error("Failed to fetch messages: %s", resp.text)
            raise RuntimeError(f"Graph API Error: {resp.status_code} - {resp.text}")

        raw_messages = resp.json().get("value", [])
        standardized_emails = []

        for msg in raw_messages:
            sender_info = msg.get("from", {}).get("emailAddress", {})
            body_info = msg.get("body", {})
            standardized_emails.append({
                "id": msg.get("id"),
                "subject": msg.get("subject", ""),
                "sender_email": sender_info.get("address", ""),
                "sender_name": sender_info.get("name", ""),
                "received_at": msg.get("receivedDateTime"),
                "html_body": body_info.get("content", ""),
                "is_read": msg.get("isRead", False),
                "conversation_id": msg.get("conversationId"),
            })

        return standardized_emails
