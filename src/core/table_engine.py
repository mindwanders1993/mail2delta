"""
src.core.table_engine
~~~~~~~~~~~~~~~~~~~~~
Simple, deterministic table extraction engine for 1 standard template type.
Supports:
  1. Vertical Key-Value layout (Key cell adjacent to Value cell)
  2. Column-Header Table layout (Column Headers matched with Data row)
"""

import logging
import re
from typing import Any
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger("core.table_engine")


class UniversalTableEngine:
    """
    Parses email HTML/text bodies for the single standard template format.
    """

    @staticmethod
    def extract_tables(html: str) -> list[pd.DataFrame]:
        """Parses HTML <table> elements or pipe-separated text into DataFrames."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        tables = []

        # Extract standard HTML tables
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and any(c != "" for c in cells):
                    rows.append(cells)
            if rows:
                max_cols = max(len(r) for r in rows)
                norm_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                tables.append(pd.DataFrame(norm_rows))

        # Fallback for pipe-separated plain text
        if not tables and "|" in html:
            text = soup.get_text(separator="\n").strip()
            lines = [l.strip() for l in text.split("\n") if "|" in l and not all(c in "-| \t\xa0" for c in l)]
            if len(lines) >= 2:
                raw_rows = [[c.strip() for c in l.split("|") if c.strip()] for l in lines]
                max_cols = max(len(r) for r in raw_rows)
                tables.append(pd.DataFrame([r + [""] * (max_cols - len(r)) for r in raw_rows]))

        return tables

    @classmethod
    def parse_standard_template(
        cls,
        html_body: str,
        code_key: str = "請求先コード",
        amount_key: str = r".*(支払額|入金額|振込).*",
        customer_name: str = "Unknown",
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        """
        Extracts Customer Code and Payment Amount from the standard template.
        """
        tables = cls.extract_tables(html_body)
        if not tables:
            return []

        billing_code = None
        raw_amount = None
        date_label = None

        for df in tables:
            # Check 1: Column Header Table (Headers on Row 0, Values on Row 1+)
            if len(df) >= 2:
                header_row = [str(x).strip() for x in df.iloc[0]]
                code_col_idx = next((i for i, h in enumerate(header_row) if re.search(code_key, h)), None)
                amt_col_idx = next((i for i, h in enumerate(header_row) if re.search(amount_key, h)), None)

                if code_col_idx is not None and amt_col_idx is not None:
                    data_row = [str(x).strip() for x in df.iloc[1]]
                    if code_col_idx < len(data_row) and amt_col_idx < len(data_row):
                        billing_code = data_row[code_col_idx]
                        raw_amount = data_row[amt_col_idx]
                        date_label = header_row[amt_col_idx]

            # Check 2: Vertical Key-Value (Key adjacent to Value in same row)
            if not billing_code or not raw_amount:
                for _, row in df.iterrows():
                    vals = [str(x).strip() for x in row if str(x).strip()]
                    for i, cell in enumerate(vals):
                        if not billing_code and re.search(code_key, cell) and i + 1 < len(vals):
                            billing_code = vals[i + 1]
                        if not raw_amount and re.search(amount_key, cell):
                            date_label = cell
                            if i + 1 < len(vals):
                                raw_amount = vals[i + 1]

        if billing_code and raw_amount:
            code = f"{prefix}{billing_code}" if prefix and not str(billing_code).startswith(prefix) else billing_code
            return [{
                "customer_name": customer_name,
                "customer_code": code,
                "payment_due_label": date_label,
                "raw_amount": raw_amount,
            }]

        return []
