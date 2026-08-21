"""
ar_collections_pipeline.models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Data models representing extracted Accounts Receivable (AR) collection records.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class CollectionRecord:
    """
    Standardized schema for extracted payment and billing information from partner emails.
    One EmailMessage can yield one or many CollectionRecords.
    """
    # Lineage / Audit fields
    message_id: str
    email_received_at: datetime
    email_subject: str
    email_sender: str

    # Extracted Business Fields
    customer_name: str | None = None
    billing_code: str | None = None
    payment_amount: float | None = None
    payment_date: date | None = None
    report_year: int | None = None
    report_month: int | None = None

    # Status Tracking
    parse_status: str = "SUCCESS"  # SUCCESS | PARTIAL | FAILED
    parse_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Converts dataclass to a serializable dictionary."""
        d = asdict(self)
        if isinstance(self.email_received_at, datetime):
            d["email_received_at"] = self.email_received_at.isoformat()
        if isinstance(self.payment_date, date):
            d["payment_date"] = self.payment_date.isoformat()
        return d
