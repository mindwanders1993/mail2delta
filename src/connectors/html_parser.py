"""
src.connectors.html_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~
Universal HTML cleaning and table structure parsing tools.
Pure DOM parsing without any domain-specific business logic.
"""

from typing import Any
import pandas as pd
from bs4 import BeautifulSoup


class HTMLParser:
    """
    Universal HTML cleaner and DOM table extraction utility.
    """

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """
        Converts HTML markup into normalized, readable multi-line plain text.

        Args:
            html_content: Raw HTML string.

        Returns:
            Normalized plain text with consistent line breaks.
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        # Ensure explicit line breaks on block and table elements
        for tag in soup.find_all(["br", "p", "tr", "div"]):
            tag.append("\n")

        text = soup.get_text(separator=" ")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    @staticmethod
    def extract_tables(html_content: str) -> list[pd.DataFrame]:
        """
        Parses all HTML <table> tags into a list of 2D pandas DataFrames.

        Args:
            html_content: Raw HTML string containing table tags.

        Returns:
            List of DataFrames representing extracted tables.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        tables = []

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

        # Fallback for pipe-separated ASCII tables
        if not tables and "|" in html_content:
            plain_text = soup.get_text(separator="\n").strip()
            lines = [
                l.strip()
                for l in plain_text.split("\n")
                if "|" in l and not all(c in "-| \t\xa0" for c in l)
            ]
            if len(lines) >= 2:
                raw_rows = [[c.strip() for c in l.split("|") if c.strip()] for l in lines]
                max_cols = max(len(r) for r in raw_rows)
                norm_rows = [r + [""] * (max_cols - len(r)) for r in raw_rows]
                tables.append(pd.DataFrame(norm_rows))

        return tables
