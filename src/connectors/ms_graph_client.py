"""
src.connectors.ms_graph_client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Universal Microsoft Graph API Connector.
Handles Entra ID OAuth2 authentication, token caching, OData email filtering, and attachment retrieval.
Zero knowledge of business logic, extraction rules, or database schemas.
"""

import logging
import time
from typing import Any
import requests

logger = logging.getLogger("connectors.ms_graph_client")


class MSGraphClient:
    """
    Universal Microsoft 365 Connector for email and attachment streaming.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        mailbox: str,
    ):
        """
        Initializes the MS Graph client credentials.

        Args:
            tenant_id: Azure Entra ID Tenant ID.
            client_id: Azure App Registration Client ID.
            client_secret: Azure App Client Secret.
            mailbox: Target mailbox email address.
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.mailbox = mailbox
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def get_token(self) -> str:
        """
        Retrieves or reuses cached OAuth2 access token.

        Returns:
            Bearer access token.
        """
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
            logger.error("Entra ID authentication failed: %s", resp.text)
            raise RuntimeError(f"MS Auth Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        self._token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in
        return self._token

    def fetch_messages(
        self,
        top: int = 50,
        filter_query: str | None = None,
        folder: str = "Inbox",
    ) -> list[dict[str, Any]]:
        """
        Fetches raw email messages from the specified folder.

        Args:
            top: Max emails to retrieve per request.
            filter_query: Optional OData filter string (e.g. 'receivedDateTime ge ...').
            folder: Target mail folder (default: 'Inbox').

        Returns:
            Standardized list of raw message dictionaries.
        """
        token = self.get_token()
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

        if filter_query:
            params["$filter"] = filter_query

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error("Failed to fetch messages: %s", resp.text)
            raise RuntimeError(f"Graph API Error ({resp.status_code}): {resp.text}")

        messages = resp.json().get("value", [])
        standardized_list = []

        for msg in messages:
            sender_obj = msg.get("from", {}).get("emailAddress", {})
            body_obj = msg.get("body", {})

            standardized_list.append({
                "id": msg.get("id"),
                "subject": msg.get("subject", ""),
                "email_sender": sender_obj.get("address", ""),
                "sender_name": sender_obj.get("name", ""),
                "received_at": msg.get("receivedDateTime"),
                "html_body": body_obj.get("content", ""),
                "has_attachments": msg.get("hasAttachments", False),
                "is_read": msg.get("isRead", False),
                "conversation_id": msg.get("conversationId"),
            })

        return standardized_list

    def fetch_attachments(self, message_id: str) -> list[dict[str, Any]]:
        """
        Fetches raw attachments for a specific message.

        Args:
            message_id: Microsoft Graph message ID.

        Returns:
            List of raw attachment dictionaries.
        """
        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"https://graph.microsoft.com/v1.0/users/{self.mailbox}/messages/{message_id}/attachments"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("Failed to fetch attachments for %s: %s", message_id, resp.text)
            raise RuntimeError(f"Graph API Error ({resp.status_code}): {resp.text}")

        return resp.json().get("value", [])
