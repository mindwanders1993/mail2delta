"""
src.transformers.currency_cleaner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sanitizes global financial currency strings and accounting representations into standard floats.
"""

import re
from typing import Any


class CurrencyCleaner:
    """
    Sanitizes international and Japanese financial strings into standard Python floats.
    Handles:
      - Currencies: ¥, ￥, $, €, £, ₹, ₩, 円
      - Negative notations: -500, (500), △500, ▲500, ¥-500
      - Special values: null, -, nan, #DIV/0!, N/A
    """

    @staticmethod
    def clean(value: Any) -> float | None:
        """
        Converts raw currency input to float.

        Args:
            value: Raw string, integer, or float representation.

        Returns:
            Cleaned float value or None if invalid/empty.
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            import math
            return None if math.isnan(value) else float(value)

        text = str(value).strip()
        if not text or text in ["-", "―", "ー", "/", "#DIV/0!", "#N/A", "#VALUE!", "nan", "None", "null"]:
            return None

        is_negative = False
        if ("-" in text) or (text.startswith("(") and text.endswith(")")) or ("△" in text) or ("▲" in text):
            is_negative = True

        cleaned_digits = re.sub(r"[^\d.]", "", text)
        if not cleaned_digits:
            return None

        try:
            val = float(cleaned_digits)
            return -val if is_negative else val
        except ValueError:
            return None
