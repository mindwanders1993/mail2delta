"""
src.transformers.key_value_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Concrete strategy for extracting financial records from Key-Value and Table-Row formatted emails.
Handles Japanese and Global AR reconciliation formats deterministically without LLMs.
"""

import re
from typing import Any
from connectors.html_parser import HTMLParser
from transformers.base import BaseEmailStrategy
from transformers.currency_cleaner import CurrencyCleaner


class KeyValueParser(BaseEmailStrategy):
    """
    Extracts customer code and payment amount from email HTML bodies containing
    structured key-value tables or labeled text rows.
    """

    def extract(
        self,
        email_dict: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Executes deterministic extraction for key-value formatted AR emails.

        Args:
            email_dict: Standardized email dictionary from MSGraphClient.
            params: Parameters dictionary from YAML config.

        Returns:
            Standardized record dictionary or None if extraction criteria not met.
        """
        html_body = email_dict.get("html_body", "")
        if not html_body:
            return None

        text = HTMLParser.html_to_text(html_body)
        if not text:
            return None

        # 1. Extract Customer Code
        code_regex = params.get(
            "code_regex",
            r"請求先コード|コード|Customer\s*ID|Account\s*No|Invoice\s*No",
        )
        customer_code = self._extract_customer_code(text, code_regex)

        # Apply optional prefix (e.g. '79' for Imoto)
        prefix = params.get("prefix_code", "")
        if customer_code and prefix and not customer_code.startswith(prefix):
            customer_code = f"{prefix}{customer_code}"

        # 2. Extract Payment Amount and Due Label
        amount_regex = params.get(
            "amount_regex",
            r"支払額|振込金額|入金額|支払予定|Payment\s*Amount|Total\s*Due",
        )
        payment_amount, due_label = self._extract_payment_amount(text, amount_regex)

        if not customer_code or payment_amount is None:
            return None

        currency = params.get("currency", "JPY")
        default_label = params.get("default_label", "Payment Due")
        customer_name = params.get("customer_name", "Unknown")

        return {
            "customer_name": customer_name,
            "customer_code": customer_code,
            "payment_amount": payment_amount,
            "payment_due_label": due_label or default_label,
            "currency": currency,
            "email_unique_id": email_dict.get("id", ""),
            "email_subject": email_dict.get("subject", ""),
            "email_sender": email_dict.get("email_sender", ""),
            "email_received_at": email_dict.get("received_at", ""),
        }

    @staticmethod
    def _extract_customer_code(text: str, pattern: str) -> str | None:
        """Extracts customer code adjacent to or below the code label."""
        match = re.search(
            rf"(?:{pattern})\s*[:：\s]*([A-Za-z0-9\-_]{{3,25}})",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Fallback: line-by-line inspection
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for idx, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1]
                    m_next = re.match(r"^([A-Za-z0-9\-_]{3,25})$", next_line)
                    if m_next:
                        return m_next.group(1).strip()

        return None

    @staticmethod
    def _extract_payment_amount(text: str, pattern: str) -> tuple[float | None, str | None]:
        """
        Locates the targeted amount line by matching the specific keyword,
        avoiding naive first-currency-symbol collisions with total invoice amounts.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for idx, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                # 1. Check if the line itself contains a currency amount
                m_curr = re.search(r"([$€£¥￥₹₩△▲\-]?\s*[\d,]{3,}(?:\.\d+)?|\b\d+(?:\.\d+)?\s*円)", line)
                if m_curr:
                    amt = CurrencyCleaner.clean(m_curr.group(0))
                    if amt is not None:
                        return amt, line

                # Check if there is a colon or delimiter followed by number/amount
                m_colon = re.search(r"[:：]\s*([$€£¥￥₹₩△▲\-]?\s*[\d,]+(?:\.\d+)?|\d+\s*円)", line)
                if m_colon:
                    amt = CurrencyCleaner.clean(m_colon.group(1))
                    if amt is not None:
                        return amt, line

                # 2. Check next line (for vertical KV or table row/cell pairs)
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1]
                    if not re.search(r"コード|日付|番号|ID|No|締日|明細|様", next_line, re.IGNORECASE):
                        amt = CurrencyCleaner.clean(next_line)
                        if amt is not None:
                            return amt, line

        # Fallback to general currency scan if specific keyword line not found
        for line in lines:
            m_fallback = re.search(r"([$€£¥￥₹₩△▲]\s*[\d,]{3,}(?:\.\d+)?)", line)
            if m_fallback:
                amt = CurrencyCleaner.clean(m_fallback.group(0))
                if amt is not None:
                    return amt, line

        return None, None
