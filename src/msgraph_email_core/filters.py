"""
msgraph_email_core.filters
~~~~~~~~~~~~~~~~~~~~~~~~~~
Chainable, side-effect-free in-memory filtering for EmailMessage collections.
"""

import re
from datetime import datetime

from .models import EmailMessage


class EmailFilter:
    """
    Chainable filter for a collection of EmailMessage objects.

    Usage:
        filtered = (
            EmailFilter(emails)
            .by_subject_contains("Report")
            .by_sender("@example.com")
            .by_has_attachments(False)
            .results()
        )
    """

    def __init__(self, emails: list[EmailMessage]):
        self._emails: list[EmailMessage] = list(emails)

    def by_sender(self, pattern: str) -> "EmailFilter":
        """Case-insensitive substring match on sender email address or display name."""
        p = pattern.lower()
        self._emails = [
            e for e in self._emails
            if p in e.sender.lower() or p in e.sender_name.lower()
        ]
        return self

    def by_subject_contains(self, keyword: str) -> "EmailFilter":
        """Case-insensitive substring match on subject."""
        kw = keyword.lower()
        self._emails = [e for e in self._emails if kw in e.subject.lower()]
        return self

    def by_subject_regex(self, pattern: str, flags: int = 0) -> "EmailFilter":
        """Regex match on subject."""
        compiled = re.compile(pattern, flags)
        self._emails = [e for e in self._emails if compiled.search(e.subject)]
        return self

    def by_date_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None
    ) -> "EmailFilter":
        """
        Filters emails received within a datetime range (inclusive).
        Both start and end are optional for open-ended ranges.
        """
        if start is not None:
            self._emails = [e for e in self._emails if e.received_at >= start]
        if end is not None:
            self._emails = [e for e in self._emails if e.received_at <= end]
        return self

    def by_has_attachments(self, has: bool = True) -> "EmailFilter":
        """Filter by whether the email has attachments."""
        self._emails = [e for e in self._emails if e.has_attachments == has]
        return self

    def by_unread_only(self) -> "EmailFilter":
        """Filter to only unread emails."""
        self._emails = [e for e in self._emails if not e.is_read]
        return self

    def results(self) -> list[EmailMessage]:
        """Returns the filtered list of EmailMessage objects."""
        return list(self._emails)

    def count(self) -> int:
        """Returns the count of matching emails."""
        return len(self._emails)

    def first(self) -> EmailMessage | None:
        """Returns the first matching email, or None if empty."""
        return self._emails[0] if self._emails else None
