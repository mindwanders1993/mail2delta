"""
ar_collections_pipeline.yaml_mapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Declarative YAML-driven parser implementing matrix and key-value table extraction strategies.
"""

import logging
import re
from datetime import date, datetime, timezone
from typing import Any, ClassVar

import pandas as pd

from msgraph_email_core.html_tools import HTMLTableExtractor
from msgraph_email_core.models import EmailMessage

from .formatters import JapaneseCurrencyCleaner
from .models import CollectionRecord

logger = logging.getLogger("ar_collections_pipeline.yaml_mapper")


class YamlMappingParser:
    """
    Parses EmailMessage HTML bodies into structured CollectionRecord objects
    based on declarative YAML parsing rules.
    """

    STRATEGIES: ClassVar[list[str]] = [
        "vertical_key_value",
        "zip_columns_across_tables",
        "zip_headers_to_row",
        "zip_rows_in_same_table",
    ]

    def __init__(self, customers_config: dict[str, Any]):
        """
        Args:
            customers_config: Dictionary mapping customer names to their parsing configuration.
        """
        self.customers_config = customers_config or {}

    def _extract_subject_date_metadata(self, subject: str) -> tuple[int | None, int | None]:
        """Extracts report year and month from email subject if present."""
        year: int | None = None
        month: int | None = None

        # Pattern: 2026年3月 or 2026/03 or 2026-03 or 26年3月
        match_full = re.search(r"(20\d{2})[年/\-](\d{1,2})", subject)
        if match_full:
            year = int(match_full.group(1))
            month = int(match_full.group(2))
        else:
            # Pattern: 3月度 or 3月分
            match_month = re.search(r"(\d{1,2})月[度分]", subject)
            if match_month:
                month = int(match_month.group(1))
                year = datetime.now(timezone.utc).year

        return year, month

    def _identify_customer(self, email: EmailMessage) -> tuple[str, dict[str, Any]] | None:
        """
        Iterates customer definitions top-to-bottom.
        Returns (customer_name, customer_config) on first match.
        """
        for cust_name, cust_conf in self.customers_config.items():
            match_rules = cust_conf.get("match", {})
            subject_regex = match_rules.get("subject_regex")
            sender_email = match_rules.get("sender_email")

            # Check subject regex
            if subject_regex and not re.search(subject_regex, email.subject, re.IGNORECASE):
                continue

            # Check sender email if configured
            if sender_email and sender_email.lower() not in email.sender.lower():
                continue

            return cust_name, cust_conf

        return None

    def parse(self, email: EmailMessage) -> list[CollectionRecord]:
        """
        Parses a single EmailMessage into one or more CollectionRecords.
        Never throws exceptions; returns FAILED record with error message on failure.
        """
        year, month = self._extract_subject_date_metadata(email.subject)
        match_result = self._identify_customer(email)

        if not match_result:
            return [
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    report_year=year,
                    report_month=month,
                    parse_status="FAILED",
                    parse_error="No matching customer parsing rule found for email.",
                )
            ]

        customer_name, cust_conf = match_result
        strategy = cust_conf.get("strategy", "vertical_key_value")

        tables = HTMLTableExtractor.extract_all_tables(email.body_html)
        if not tables:
            return [
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    customer_name=customer_name,
                    report_year=year,
                    report_month=month,
                    parse_status="FAILED",
                    parse_error="No HTML tables found in email body.",
                )
            ]

        try:
            if strategy == "vertical_key_value":
                return self._strategy_vertical_key_value(tables, cust_conf, email, customer_name, year, month)
            elif strategy == "zip_columns_across_tables":
                return self._strategy_zip_columns_across_tables(tables, cust_conf, email, customer_name, year, month)
            elif strategy == "zip_headers_to_row":
                return self._strategy_zip_headers_to_row(tables, cust_conf, email, customer_name, year, month)
            elif strategy == "zip_rows_in_same_table":
                return self._strategy_zip_rows_in_same_table(tables, cust_conf, email, customer_name, year, month)
            else:
                return [
                    CollectionRecord(
                        message_id=email.id,
                        email_received_at=email.received_at,
                        email_subject=email.subject,
                        email_sender=email.sender,
                        customer_name=customer_name,
                        report_year=year,
                        report_month=month,
                        parse_status="FAILED",
                        parse_error=f"Unknown parsing strategy '{strategy}'",
                    )
                ]
        except Exception as e:
            logger.exception("Error parsing email %s for customer %s", email.id, customer_name)
            return [
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    customer_name=customer_name,
                    report_year=year,
                    report_month=month,
                    parse_status="FAILED",
                    parse_error=str(e),
                )
            ]

    def parse_batch(self, emails: list[EmailMessage]) -> list[CollectionRecord]:
        """Parses a list of emails, returning flattened CollectionRecords."""
        all_records: list[CollectionRecord] = []
        for email in emails:
            all_records.extend(self.parse(email))
        return all_records

    # ── Strategy 1: Vertical Key-Value (1 Record per email) ──────────────────

    def _strategy_vertical_key_value(
        self,
        tables: list[pd.DataFrame],
        conf: dict[str, Any],
        email: EmailMessage,
        customer_name: str,
        year: int | None,
        month: int | None,
    ) -> list[CollectionRecord]:
        code_src = conf.get("code_source", {})
        amt_src = conf.get("amount_source", {})

        code_tbl_idx = code_src.get("table_index", 0)
        amt_tbl_idx = amt_src.get("table_index", 0)

        billing_code: str | None = None
        payment_amount: float | None = None
        payment_date: date | None = None

        # 1. Extract Code
        if code_tbl_idx < len(tables):
            df_code = tables[code_tbl_idx]
            target_regex = code_src.get("target_regex", "請求先コード")
            for _, row in df_code.iterrows():
                row_vals = [str(x).strip() for x in row if pd.notna(x)]
                for idx, cell in enumerate(row_vals):
                    if re.search(target_regex, cell):
                        if idx + 1 < len(row_vals):
                            billing_code = row_vals[idx + 1]
                        break

        # 2. Extract Amount
        if amt_tbl_idx < len(tables):
            df_amt = tables[amt_tbl_idx]
            target_regex = amt_src.get("target_regex", ".*(支払額|入金額|振込).*")
            for _, row in df_amt.iterrows():
                row_vals = [str(x).strip() for x in row if pd.notna(x)]
                for idx, cell in enumerate(row_vals):
                    if re.search(target_regex, cell):
                        if idx + 1 < len(row_vals):
                            payment_amount = JapaneseCurrencyCleaner.clean(row_vals[idx + 1])
                        # Check if label contains payment date
                        payment_date = JapaneseCurrencyCleaner.extract_date_from_label(cell, default_year=year)
                        break

        status = "SUCCESS" if (billing_code and payment_amount is not None) else "PARTIAL"
        return [
            CollectionRecord(
                message_id=email.id,
                email_received_at=email.received_at,
                email_subject=email.subject,
                email_sender=email.sender,
                customer_name=customer_name,
                billing_code=billing_code,
                payment_amount=payment_amount,
                payment_date=payment_date,
                report_year=year,
                report_month=month,
                parse_status=status,
            )
        ]

    # ── Strategy 2: Zip Columns Across Tables (N Records) ───────────────────

    def _strategy_zip_columns_across_tables(
        self,
        tables: list[pd.DataFrame],
        conf: dict[str, Any],
        email: EmailMessage,
        customer_name: str,
        year: int | None,
        month: int | None,
    ) -> list[CollectionRecord]:
        code_src = conf.get("code_source", {})
        amt_src = conf.get("amount_source", {})

        code_tbl_idx = code_src.get("table_index", 0)
        amt_tbl_idx = amt_src.get("table_index", 1)

        if code_tbl_idx >= len(tables) or amt_tbl_idx >= len(tables):
            raise IndexError("Required table index not found in email.")

        df_code = tables[code_tbl_idx]
        df_amt = tables[amt_tbl_idx]

        # Find code row
        code_regex = code_src.get("target_regex", "請求先コード")
        codes: list[str] = []
        for _, row in df_code.iterrows():
            row_vals = [str(x).strip() for x in row if pd.notna(x)]
            if any(re.search(code_regex, val) for val in row_vals):
                # Codes are the remaining cells in this row
                match_idx = next(i for i, val in enumerate(row_vals) if re.search(code_regex, val))
                codes = row_vals[match_idx + 1:]
                break

        # Find amount row
        amt_regex = amt_src.get("target_regex", ".*(振込金額|支払額|入金額).*")
        amounts: list[float | None] = []
        payment_date: date | None = None
        for _, row in df_amt.iterrows():
            row_vals = [str(x).strip() for x in row if pd.notna(x)]
            if any(re.search(amt_regex, val) for val in row_vals):
                match_idx = next(i for i, val in enumerate(row_vals) if re.search(amt_regex, val))
                payment_date = JapaneseCurrencyCleaner.extract_date_from_label(row_vals[match_idx], default_year=year)
                amounts = [JapaneseCurrencyCleaner.clean(v) for v in row_vals[match_idx + 1:]]
                break

        records: list[CollectionRecord] = []
        for code, amt in zip(codes, amounts):
            # Ignore empty codes / placeholders
            if not code or code == "-":
                continue
            records.append(
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    customer_name=customer_name,
                    billing_code=code,
                    payment_amount=amt,
                    payment_date=payment_date,
                    report_year=year,
                    report_month=month,
                    parse_status="SUCCESS" if amt is not None else "PARTIAL",
                )
            )

        return records

    # ── Strategy 3: Zip Headers to Row (N Records) ──────────────────────────

    def _strategy_zip_headers_to_row(
        self,
        tables: list[pd.DataFrame],
        conf: dict[str, Any],
        email: EmailMessage,
        customer_name: str,
        year: int | None,
        month: int | None,
    ) -> list[CollectionRecord]:
        amt_src = conf.get("amount_source", {})
        tbl_idx = amt_src.get("table_index", 1)

        if tbl_idx >= len(tables):
            raise IndexError(f"Table index {tbl_idx} not found in email.")

        df = tables[tbl_idx]
        # In this strategy, the first row or headers are the billing codes
        headers = [str(c).strip() for c in df.iloc[0] if pd.notna(c)]
        amt_regex = amt_src.get("target_regex", ".*(支払額|入金額).*")

        amounts: list[float | None] = []
        payment_date: date | None = None

        for idx in range(len(df)):
            row_vals = [str(x).strip() for x in df.iloc[idx] if pd.notna(x)]
            if any(re.search(amt_regex, val) for val in row_vals):
                match_idx = next(i for i, val in enumerate(row_vals) if re.search(amt_regex, val))
                payment_date = JapaneseCurrencyCleaner.extract_date_from_label(row_vals[match_idx], default_year=year)
                amounts = [JapaneseCurrencyCleaner.clean(v) for v in row_vals[match_idx + 1:]]
                break

        records: list[CollectionRecord] = []
        # Exclude the leading label column from headers
        code_headers = headers[1:] if len(headers) > len(amounts) else headers
        for code, amt in zip(code_headers, amounts):
            if not code or code in ["合計", "Total", "-"]:
                continue
            records.append(
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    customer_name=customer_name,
                    billing_code=code,
                    payment_amount=amt,
                    payment_date=payment_date,
                    report_year=year,
                    report_month=month,
                    parse_status="SUCCESS" if amt is not None else "PARTIAL",
                )
            )

        return records

    # ── Strategy 4: Zip Rows in Same Table (N Records) ──────────────────────

    def _strategy_zip_rows_in_same_table(
        self,
        tables: list[pd.DataFrame],
        conf: dict[str, Any],
        email: EmailMessage,
        customer_name: str,
        year: int | None,
        month: int | None,
    ) -> list[CollectionRecord]:
        amt_src = conf.get("amount_source", {})
        code_src = conf.get("code_source", {})
        tbl_idx = amt_src.get("table_index", 1)

        if tbl_idx >= len(tables):
            raise IndexError(f"Table index {tbl_idx} not found.")

        df = tables[tbl_idx]
        code_regex = code_src.get("target_regex", "^コード$")
        amt_regex = amt_src.get("target_regex", ".*(支払額|入金額).*")

        codes: list[str] = []
        amounts: list[float | None] = []
        payment_date: date | None = None

        for _, row in df.iterrows():
            row_vals = [str(x).strip() for x in row if pd.notna(x)]
            if any(re.search(code_regex, val) for val in row_vals):
                match_idx = next(i for i, val in enumerate(row_vals) if re.search(code_regex, val))
                codes = row_vals[match_idx + 1:]
            elif any(re.search(amt_regex, val) for val in row_vals):
                match_idx = next(i for i, val in enumerate(row_vals) if re.search(amt_regex, val))
                payment_date = JapaneseCurrencyCleaner.extract_date_from_label(row_vals[match_idx], default_year=year)
                amounts = [JapaneseCurrencyCleaner.clean(v) for v in row_vals[match_idx + 1:]]

        records: list[CollectionRecord] = []
        for code, amt in zip(codes, amounts):
            if not code or code in ["合計", "-"]:
                continue
            records.append(
                CollectionRecord(
                    message_id=email.id,
                    email_received_at=email.received_at,
                    email_subject=email.subject,
                    email_sender=email.sender,
                    customer_name=customer_name,
                    billing_code=code,
                    payment_amount=amt,
                    payment_date=payment_date,
                    report_year=year,
                    report_month=month,
                    parse_status="SUCCESS" if amt is not None else "PARTIAL",
                )
            )

        return records
