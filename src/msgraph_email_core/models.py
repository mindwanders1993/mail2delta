"""
msgraph_email_core.models
~~~~~~~~~~~~~~~~~~~~~~~~~
Generic, platform-agnostic data models for Microsoft Graph email processing.
Zero external dependencies beyond Python standard library.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Any


@dataclass
class AttachmentItem:
    """Represents a single email attachment."""
    id: str
    name: str
    content_type: str
    size_bytes: int
    content_bytes: bytes = field(default=b"", repr=False)

    def to_bytes_io(self) -> BytesIO:
        """Returns the attachment content as a BytesIO stream."""
        return BytesIO(self.content_bytes)

    def save_to_path(self, path: str) -> None:
        """Writes attachment bytes directly to a local filesystem path."""
        with open(path, "wb") as f:
            f.write(self.content_bytes)


@dataclass
class EmailMessage:
    """
    Represents a single email fetched from Microsoft Graph API.
    Platform-agnostic — works on Databricks, Airflow, local scripts, or any Python runtime.
    """
    id: str
    subject: str
    sender: str
    sender_name: str
    recipients: list[str]
    cc: list[str]
    received_at: datetime
    body_html: str
    body_text: str
    has_attachments: bool
    is_read: bool
    conversation_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dictionary for storage (Delta, Parquet, JSON, DB)."""
        d = asdict(self)
        if isinstance(self.received_at, datetime):
            d["received_at"] = self.received_at.isoformat()
        return d
