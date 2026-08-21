"""
msgraph_email_core.client
~~~~~~~~~~~~~~~~~~~~~~~~~
Synchronous, requests-based Microsoft Graph API email client.
Supports incremental delta querying, attachment loading, and mailbox actions.
"""

import base64
import logging
import time
from datetime import datetime, timezone
from typing import Any, Self
from urllib.parse import parse_qs, urlparse

import requests

from .models import AttachmentItem, EmailMessage

logger = logging.getLogger("msgraph_email_core.client")


class MSGraphEmailClient:
    """
    Synchronous client for reading and managing emails via Microsoft Graph API.

    Features:
    - Pure synchronous HTTP calls via `requests` (no asyncio or nest_asyncio needed)
    - Full support for incremental change tracking via MS Graph delta query
    - Attachment downloading and decoding
    - Context manager support (`with MSGraphEmailClient(...) as client:`)
    - Retry logic with exponential backoff for resilience

    Usage:
        with MSGraphEmailClient(tenant_id, client_id, secret, mailbox) as client:
            emails, new_token = client.get_emails_incremental(delta_token=saved_token)
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        mailbox: str,
        max_retries: int = 3,
        retry_backoff: int = 2,
        timeout: int = 30,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.mailbox = mailbox
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.timeout = timeout
        self._access_token: str | None = None
        self._session = requests.Session()

    # ── Connection Lifecycle ────────────────────────────────────────────────

    def connect(self) -> None:
        """Authenticates with Azure AD and caches the OAuth2 token."""
        self._access_token = self._fetch_access_token()
        logger.info(f"Successfully authenticated for mailbox: {self.mailbox}")

    def close(self) -> None:
        """Clears cached token and closes active session."""
        self._access_token = None
        self._session.close()
        logger.info("MSGraphEmailClient session closed.")

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def is_connected(self) -> bool:
        """Returns True if client currently holds a valid access token."""
        return self._access_token is not None

    # ── Authentication & HTTP Helpers ───────────────────────────────────────

    def _fetch_access_token(self) -> str:
        """Obtains an access token using OAuth2 Client Credentials flow."""
        token_url = self.TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id)
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.post(token_url, data=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                if not token:
                    raise ValueError("No access_token found in token endpoint response.")
                return token
            except (requests.RequestException, ValueError) as e:
                logger.warning(f"Token acquisition attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries:
                    raise ConnectionError(f"Failed to acquire Microsoft Graph token after {self.max_retries} attempts: {e}") from e
                time.sleep(self.retry_backoff * attempt)
        raise ConnectionError("Authentication failed.")

    def _get_headers(self) -> dict[str, str]:
        if not self._access_token:
            self._access_token = self._fetch_access_token()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Prefer": 'outlook.body-content-type="html"',
        }

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Executes an HTTP request with automatic token refresh and retry backoff."""
        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
                if resp.status_code == 401:  # Token expired
                    logger.info("Access token expired, refreshing...")
                    self._access_token = self._fetch_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    resp = self._session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as e:
                logger.warning(f"HTTP {method} {url} attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_backoff * attempt)
        raise RuntimeError("Request failed.")

    # ── Email Fetching ──────────────────────────────────────────────────────

    def get_emails(
        self,
        folder: str = "Inbox",
        top: int = 50,
        order_by: str = "receivedDateTime DESC",
    ) -> list[EmailMessage]:
        """
        Fetches the latest N emails from a specified mailbox folder.

        Args:
            folder: Mailbox folder name or ID (e.g. 'Inbox', 'Archive').
            top: Number of messages to retrieve.
            order_by: OData ordering clause.

        Returns:
            List of EmailMessage dataclasses.
        """
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/mailFolders/{folder}/messages"
        params = {
            "$top": top,
            "$orderby": order_by,
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,hasAttachments,isRead,conversationId",
        }

        resp = self._request_with_retry("GET", url, params=params)
        data = resp.json()
        raw_messages = data.get("value", [])
        return [self._build_email_message(m) for m in raw_messages]

    def get_email_by_id(self, message_id: str) -> EmailMessage | None:
        """Fetches a single email by its unique MS Graph message ID."""
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}"
        params = {
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,hasAttachments,isRead,conversationId",
        }
        try:
            resp = self._request_with_retry("GET", url, params=params)
            return self._build_email_message(resp.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_emails_incremental(
        self,
        folder: str = "Inbox",
        delta_token: str | None = None,
    ) -> tuple[list[EmailMessage], str]:
        """
        Fetches only emails received or modified since the last delta token was generated.

        Args:
            folder: Mailbox folder name (default: "Inbox").
            delta_token: The token or deltaLink returned by the previous call. Pass None on first run.

        Returns:
            Tuple of:
              - list of newly received/updated EmailMessage objects
              - next delta_token string to persist for future incremental runs
        """
        if delta_token and delta_token.startswith("http"):
            next_url: str | None = delta_token
        elif delta_token:
            next_url = f"{self.GRAPH_BASE}/users/{self.mailbox}/mailFolders/{folder}/messages/delta?$deltatoken={delta_token}"
        else:
            next_url = f"{self.GRAPH_BASE}/users/{self.mailbox}/mailFolders/{folder}/messages/delta"

        messages: list[EmailMessage] = []
        new_delta_token = ""

        while next_url:
            resp = self._request_with_retry("GET", next_url)
            data = resp.json()

            for item in data.get("value", []):
                # Skip deletion tombstones
                if "@removed" in item:
                    continue
                messages.append(self._build_email_message(item))

            if "@odata.nextLink" in data:
                next_url = data["@odata.nextLink"]
            elif "@odata.deltaLink" in data:
                delta_link = data["@odata.deltaLink"]
                parsed = urlparse(delta_link)
                qs = parse_qs(parsed.query)
                token_val = qs.get("$deltatoken", [delta_link])[0]
                new_delta_token = token_val
                next_url = None
            else:
                next_url = None

        return messages, new_delta_token

    # ── Attachments ─────────────────────────────────────────────────────────

    def get_attachments(self, message_id: str) -> list[AttachmentItem]:
        """
        Retrieves all attachments for a specific message, with contents decoded.
        """
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}/attachments"
        resp = self._request_with_retry("GET", url)
        data = resp.json()
        attachments: list[AttachmentItem] = []

        for item in data.get("value", []):
            raw_bytes = b""
            if item.get("@odata.type") == "#microsoft.graph.fileAttachment" and "contentBytes" in item:
                raw_bytes = base64.b64decode(item["contentBytes"])

            attachments.append(
                AttachmentItem(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    content_type=item.get("contentType", "application/octet-stream"),
                    size_bytes=item.get("size", len(raw_bytes)),
                    content_bytes=raw_bytes,
                )
            )

        return attachments

    def get_attachment_by_name(self, message_id: str, filename: str) -> AttachmentItem | None:
        """Finds and returns an attachment by exact name matching."""
        all_att = self.get_attachments(message_id)
        for att in all_att:
            if att.name.lower() == filename.lower():
                return att
        return None

    # ── Mailbox Actions ─────────────────────────────────────────────────────

    def mark_as_read(self, message_id: str) -> None:
        """Sets isRead=True on the message."""
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}"
        self._request_with_retry("PATCH", url, json={"isRead": True})

    def mark_as_unread(self, message_id: str) -> None:
        """Sets isRead=False on the message."""
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}"
        self._request_with_retry("PATCH", url, json={"isRead": False})

    def move_message(self, message_id: str, target_folder_id: str) -> None:
        """Moves a message to another folder."""
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}/move"
        self._request_with_retry("POST", url, json={"destinationId": target_folder_id})

    def delete_message(self, message_id: str) -> None:
        """Deletes a message."""
        url = f"{self.GRAPH_BASE}/users/{self.mailbox}/messages/{message_id}"
        self._request_with_retry("DELETE", url)

    # ── Parsing Helpers ─────────────────────────────────────────────────────

    def _build_email_message(self, raw: dict[str, Any]) -> EmailMessage:
        """Converts raw MS Graph JSON payload into a structured EmailMessage."""
        from_data = raw.get("from") or {}
        email_addr_obj = from_data.get("emailAddress") or {}
        sender = email_addr_obj.get("address", "UNKNOWN")
        sender_name = email_addr_obj.get("name", sender)

        recipients = [
            r.get("emailAddress", {}).get("address", "")
            for r in raw.get("toRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]
        cc = [
            r.get("emailAddress", {}).get("address", "")
            for r in raw.get("ccRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]

        received_str = raw.get("receivedDateTime")
        received_at = datetime.now(timezone.utc)
        if received_str:
            try:
                received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        body_obj = raw.get("body") or {}
        body_html = body_obj.get("content", "")
        body_text = ""
        if body_html:
            from .html_tools import HTMLTableExtractor
            body_text = HTMLTableExtractor.get_plain_text(body_html)

        return EmailMessage(
            id=raw.get("id", ""),
            subject=raw.get("subject") or "",
            sender=sender,
            sender_name=sender_name,
            recipients=recipients,
            cc=cc,
            received_at=received_at,
            body_html=body_html,
            body_text=body_text,
            has_attachments=bool(raw.get("hasAttachments", False)),
            is_read=bool(raw.get("isRead", False)),
            conversation_id=raw.get("conversationId", ""),
        )
