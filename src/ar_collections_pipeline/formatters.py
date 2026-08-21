"""
ar_collections_pipeline.formatters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Formatters and value cleaners for Japanese financial amounts, dates, and accounting conventions.
"""

import re
from datetime import date, datetime, timezone
from typing import Any


class JapaneseCurrencyCleaner:
    """
    Cleans and converts Japanese currency and accounting strings into standard Python floats.

    Handles:
    - Standard yen: '¥1,234,567' -> 1234567.0
    - Fullwidth yen: '￥1,234,567' -> 1234567.0
    - Backslash yen variant: '\\1,234,567' -> 1234567.0
    - Negative triangle notation (Japanese accounting): '△25,226,790' or '▲25,226,790' -> -25226790.0
    - Negative signs: '¥-25,226,790' or '-¥25,226,790' -> -25226790.0
    - Parentheses negative: '(1,234)' -> -1234.0
    - Kanji yen suffix: '1,234円' -> 1234.0
    - Zero amounts: '¥0' or '0' -> 0.0
    - Excel errors & blanks: '#DIV/0!', '#N/A', '-', '', None -> None
    """

    @staticmethod
    def clean(value: Any) -> float | None:
        """Converts raw input to float, returning None if invalid or empty."""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            import math
            return None if math.isnan(value) else float(value)

        text = str(value).strip()
        if not text:
            return None

        # Check for Excel errors or empty markers
        if any(err in text for err in ["#DIV/0!", "#N/A", "#VALUE!", "#REF!", "None", "nan"]):
            return None

        if text in ["-", "―", "ー", "/"]:
            return None

        is_negative = False

        # Japanese accounting triangle notation for negative numbers
        if "△" in text or "▲" in text:
            is_negative = True

        # Parentheses notation (1,234)
        if text.startswith("(") and text.endswith(")"):
            is_negative = True

        if "-" in text:
            is_negative = True

        # Strip all currency symbols, commas, kanji, triangles, spaces, and signs
        cleaned_digits = re.sub(r"[¥￥\\,△▲\(\)\s円-]", "", text)

        if not cleaned_digits:
            return None

        try:
            num = float(cleaned_digits)
            return -num if is_negative else num
        except ValueError:
            return None

    @staticmethod
    def extract_date_from_label(label: str, default_year: int | None = None) -> date | None:
        """
        Extracts dates from headers or row labels such as:
        - '3/23 支払額' -> date(default_year, 3, 23)
        - '3/10払' -> date(default_year, 3, 10)
        - '2026/03/31' -> date(2026, 3, 31)
        - '2026年3月31日' -> date(2026, 3, 31)
        """
        if not label:
            return None

        # Format: YYYY/MM/DD or YYYY-MM-DD or YYYY年MM月DD日
        full_match = re.search(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})", label)
        if full_match:
            try:
                y, m, d = map(int, full_match.groups())
                return date(y, m, d)
            except ValueError:
                pass

        # Format: MM/DD or MM月DD日
        short_match = re.search(r"(\d{1,2})[月/](\d{1,2})", label)
        if short_match:
            try:
                m, d = map(int, short_match.groups())
                year = default_year or datetime.now(timezone.utc).year
                return date(year, m, d)
            except ValueError:
                pass

        return None
