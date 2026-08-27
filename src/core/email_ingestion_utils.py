"""
src.core.email_ingestion_utils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Universal, multi-currency email ingestion, YAML configuration & Delta storage utilities.
Fully configurable for ANY country, language, currency, or email template.
"""

import os
import re
import yaml
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timezone


class MSGraphUtility:
    """Handles Microsoft 365 OAuth2 authentication and email retrieval."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, mailbox: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.mailbox = mailbox
        self._token = None

    def get_token(self) -> str:
        """Retrieves or reuses OAuth2 access token."""
        if not self._token:
            resp = requests.post(
                f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"MS Auth Failed: {resp.text}")
            self._token = resp.json()["access_token"]
        return self._token

    def fetch_inbox_emails(self, top: int = 10) -> list:
        """Fetches the latest emails from the target inbox."""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{self.mailbox}/mailFolders/Inbox/messages",
            headers=headers,
            params={"$top": top, "$orderby": "receivedDateTime desc"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Fetch failed: {resp.text}")
        return resp.json().get("value", [])


class CurrencyUtility:
    """
    Universal financial string cleaner supporting all global currencies:
    USD ($), EUR (€), GBP (£), JPY (¥, ￥, 円), INR (₹), KRW (₩), CAD, AUD, CHF, etc.
    Handles negative signs (-), parentheses ((1,000)), and accounting triangles (△, ▲).
    """

    @staticmethod
    def clean(value) -> float | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text or text in ["-", "―", "ー", "/", "#DIV/0!", "#N/A", "#VALUE!", "nan", "None", "null"]:
            return None

        # Check negative notation across global conventions
        is_neg = False
        if "-" in text or text.startswith("(") and text.endswith(")") or "△" in text or "▲" in text:
            is_neg = True

        # Strip all currency symbols, letters, spaces, commas, and negative signs
        digits = re.sub(r"[^\d.]", "", text)
        if not digits:
            return None

        try:
            val = float(digits)
            return -val if is_neg else val
        except ValueError:
            return None


def _extract_customer_code(text: str, code_pattern: str) -> str | None:
    m_code = re.search(rf"(?:{code_pattern})\s*[:：\s]*([A-Za-z0-9\-_]{{3,25}})", text, re.IGNORECASE)
    if m_code:
        return m_code.group(1)
    fallback = re.findall(r"\b([A-Za-z0-9\-_]{4,25})\b", text)
    return fallback[0] if fallback else None


def _extract_payment_amount(text: str, amount_pattern: str) -> tuple[float | None, str | None]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for idx, line in enumerate(lines):
        if re.search(amount_pattern, line, re.IGNORECASE):
            m_curr = re.search(r"[$€£¥￥₹₩]\s*([\d,]+(?:\.\d+)?)", line)
            if m_curr:
                amt = CurrencyUtility.clean(m_curr.group(0))
                if amt is not None:
                    return amt, line
            if idx + 1 < len(lines):
                amt = CurrencyUtility.clean(lines[idx + 1])
                if amt is not None:
                    return amt, line

    m_amt = re.search(r"[$€£¥￥₹₩]\s*([\d,]+(?:\.\d+)?)", text)
    if m_amt:
        return CurrencyUtility.clean(m_amt.group(0)), "Payment Due"
    return None, None


def _extract_sender(email_dict: dict) -> str:
    from_obj = email_dict.get("from")
    if isinstance(from_obj, dict):
        addr_obj = from_obj.get("emailAddress")
        if isinstance(addr_obj, dict):
            addr = addr_obj.get("address", "")
            if addr:
                return addr
    return email_dict.get("email_sender", "")


class YamlConfigUtility:
    """
    Universal YAML configuration engine.
    Extracts customer data dynamically based entirely on declarative rules.
    """

    @staticmethod
    def load_config(file_path_or_yaml_str: str) -> dict:
        """Loads configuration from file or raw string."""
        if os.path.exists(file_path_or_yaml_str):
            with open(file_path_or_yaml_str, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return yaml.safe_load(file_path_or_yaml_str)

    @staticmethod
    def parse_email(email_dict: dict, config: dict) -> dict | None:
        """Extracts customer code, amount, currency, and label based entirely on YAML configuration."""
        subject = email_dict.get("subject", "")
        body = email_dict.get("body", {})
        html = ""
        if isinstance(body, dict):
            html = body.get("content", "")
        if not html:
            html = email_dict.get("html_body", "")

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n").strip()

        customers = config.get("customers", {})
        for cust_name, rules in customers.items():
            subject_pattern = rules.get("subject_regex", "")
            if subject_pattern and re.search(subject_pattern, subject or "", re.IGNORECASE):
                code_pattern = rules.get("code_regex", r"Customer\s*ID|Invoice\s*Number|Account|請求先コード|コード")
                amount_pattern = rules.get("amount_regex", r"Total\s*Paid|Payment\s*Amount|Amount|支払額|入金額|振込")

                code = _extract_customer_code(text, code_pattern)
                amount, label = _extract_payment_amount(text, amount_pattern)

                if code and amount is not None:
                    currency = rules.get("currency", "USD")
                    sender = _extract_sender(email_dict)
                    received = email_dict.get("receivedDateTime") or email_dict.get("received_at", "")

                    return {
                        "customer_name": cust_name,
                        "customer_code": code,
                        "payment_due_label": label or rules.get("default_label", "Payment Due"),
                        "payment_amount": amount,
                        "currency": currency,
                        "email_subject": subject,
                        "email_sender": sender,
                        "email_received_at": received,
                    }

        return None


class DeltaUtility:
    """Handles saving pandas dataframes into Databricks Delta Lake."""

    @staticmethod
    def save_to_delta(spark_session, df: pd.DataFrame, table_name: str = "ar_poc_reconciliation") -> None:
        spark_df = spark_session.createDataFrame(df)
        spark_df.write.format("delta").mode("append").saveAsTable(table_name)
        print(f"💾 Successfully saved {len(df)} records into `{table_name}` table!")
