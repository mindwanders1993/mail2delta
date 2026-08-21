"""
msgraph_email_core.html_tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generic HTML processing and table extraction tools for email bodies.
"""

import io
import logging

import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger("msgraph_email_core.html_tools")


class HTMLTableExtractor:
    """
    Extracts and normalizes HTML tables from email bodies into Pandas DataFrames.
    Robust against malformed HTML, nested tags, and varying table structures.
    """

    @staticmethod
    def get_plain_text(html: str) -> str:
        """Strips HTML tags and returns clean plain text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n").strip()

    @staticmethod
    def extract_all_tables(html: str, header_row: int | None = None) -> list[pd.DataFrame]:
        """
        Parses all <table> elements in the HTML body into Pandas DataFrames.

        Args:
            html: Raw HTML string.
            header_row: Row index to use as column headers (default: None for raw row indexing).

        Returns:
            List of non-empty cleaned pd.DataFrame objects.
        """
        if not html or "<table" not in html.lower():
            return []

        try:
            # StringIO avoids pandas future deprecation warnings
            tables = pd.read_html(io.StringIO(html), flavor="bs4", header=header_row)
            cleaned_tables: list[pd.DataFrame] = []

            for df in tables:
                # Drop rows and columns that are completely empty / all NaN
                df_clean = df.dropna(how="all").dropna(axis=1, how="all")
                if not df_clean.empty and len(df_clean) > 0:
                    # Reset indices for clean tabular access
                    df_clean = df_clean.reset_index(drop=True)
                    cleaned_tables.append(df_clean)

            return cleaned_tables
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to parse HTML tables: %s", e)
            return []

    @staticmethod
    def extract_table_by_index(
        html: str,
        index: int,
        header_row: int | None = None
    ) -> pd.DataFrame | None:
        """
        Retrieves the Nth table (0-indexed) from the HTML content.
        Returns None if index is out of bounds.
        """
        tables = HTMLTableExtractor.extract_all_tables(html, header_row=header_row)
        if 0 <= index < len(tables):
            return tables[index]
        return None

    @staticmethod
    def extract_table_by_header_keyword(
        html: str,
        keyword: str,
        header_row: int | None = None
    ) -> pd.DataFrame | None:
        """
        Finds the first table whose cells or headers contain a specific keyword.
        """
        tables = HTMLTableExtractor.extract_all_tables(html, header_row=header_row)
        kw_lower = keyword.lower()
        for df in tables:
            # Check column names
            for col in df.columns:
                if kw_lower in str(col).lower():
                    return df
            # Check cell values
            for col in df.columns:
                if df[col].astype(str).str.lower().str.contains(kw_lower).any():
                    return df
        return None
