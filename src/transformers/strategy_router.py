"""
src.transformers.strategy_router
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The Switchboard: Dynamically matches incoming emails against YAML rules
and dispatches them to the corresponding extraction strategy.
"""

import os
import re
from typing import Any
import yaml
from transformers.base import BaseEmailStrategy
from transformers.key_value_parser import KeyValueParser


class StrategyRouter:
    """
    Routes emails to designated extraction strategies based entirely on declarative YAML rules.
    """

    def __init__(self, config_source: str | dict[str, Any]):
        """
        Initializes the router with a YAML config file path, raw YAML string, or dictionary.

        Args:
            config_source: Filepath string, raw YAML string, or parsed dictionary.
        """
        self.config = self._load_config(config_source)
        self.strategies: dict[str, BaseEmailStrategy] = {
            "key_value_table": KeyValueParser(),
            "vertical_key_value": KeyValueParser(),
        }

    def register_strategy(self, name: str, strategy: BaseEmailStrategy) -> None:
        """
        Registers a new strategy handler dynamically (e.g. for Excel, PDF, etc.).

        Args:
            name: Strategy name matching the 'strategy' field in YAML.
            strategy: Concrete BaseEmailStrategy implementation instance.
        """
        self.strategies[name] = strategy

    def process_email(self, email_dict: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        """
        Matches an email's subject against customer rules and executes the appropriate strategy.

        Args:
            email_dict: Standardized email dictionary from MSGraphClient.

        Returns:
            Tuple of (extracted_record_dict, merge_keys_list).
            Returns (None, []) if email does not match any customer rule or fails extraction.
        """
        subject = email_dict.get("subject", "")
        customers = self.config.get("customers", {})

        for cust_name, rules in customers.items():
            subject_pattern = rules.get("subject_regex", "")
            if subject_pattern and re.search(subject_pattern, subject or "", re.IGNORECASE):
                strategy_name = rules.get("strategy", "key_value_table")
                strategy = self.strategies.get(strategy_name)

                if not strategy:
                    raise ValueError(f"Unknown extraction strategy registered in YAML: {strategy_name}")

                params = rules.get("params", {})
                params["customer_name"] = cust_name

                record = strategy.extract(email_dict, params)
                merge_keys = rules.get("merge_keys", ["customer_code", "payment_due_label"])

                if record:
                    return record, merge_keys

        return None, []

    @staticmethod
    def _load_config(source: str | dict[str, Any]) -> dict[str, Any]:
        """Loads YAML configuration from path, string, or returns existing dict."""
        if isinstance(source, dict):
            return source

        if os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        return yaml.safe_load(source)
