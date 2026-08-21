import re
from typing import Any

import pandas as pd


class MetadataExtractor:
    """Extracts named metadata variables from text using regular expressions."""

    def __init__(self, extractor_configs: list[dict[str, Any]]):
        self.rules = []
        for item in extractor_configs:
            self.rules.append({
                "name": item.get("name"),
                "source": item.get("source", "subject_or_body"),
                "pattern": re.compile(item["regex"])
            })

    def extract(self, subject: str, body_text: str) -> dict[str, Any]:
        """Extracts all matched named groups across rules."""
        result = {}
        combined_text = f"{subject}\n{body_text}"

        for rule in self.rules:
            src = rule["source"]
            target = subject if src == "subject" else (body_text if src == "body" else combined_text)
            
            match = rule["pattern"].search(target)
            if match:
                result.update(match.groupdict())
        return result


class HTMLTableExtractor:
    """Extracts and cleans HTML tables from raw email HTML bodies."""

    def __init__(self, table_config: dict[str, Any] | None = None):
        self.config = table_config or {}
        self.enabled = self.config.get("enabled", True)
        self.header_row = self.config.get("header_row", 0)
        self.column_mapping = self.config.get("column_mapping", {})

    def extract_tables(self, html_content: str) -> list[pd.DataFrame]:
        """Parses HTML tables and applies column mappings."""
        if not self.enabled or not html_content or "<table" not in html_content.lower():
            return []

        try:
            tables = pd.read_html(html_content, flavor="bs4", header=self.header_row)
            cleaned_tables = []

            for df in tables:
                # Remove rows/columns that are entirely null (common in email formatting)
                df_clean = df.dropna(how="all").dropna(axis=1, how="all")
                if not df_clean.empty and len(df_clean) > 0:
                    if self.column_mapping:
                        df_clean = df_clean.rename(columns=self.column_mapping)
                    cleaned_tables.append(df_clean)
            return cleaned_tables
        except Exception:
            return []
