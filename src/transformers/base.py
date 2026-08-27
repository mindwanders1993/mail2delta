"""
src.transformers.base
~~~~~~~~~~~~~~~~~~~~~
Abstract Base Class defining the interface contract for all data extraction strategies.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseEmailStrategy(ABC):
    """
    Interface contract for all email extraction strategies.
    Every new parsing strategy (Key-Value, Excel attachment, PDF, etc.) must implement this interface.
    """

    @abstractmethod
    def extract(
        self,
        email_dict: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Extracts structured records from an email dictionary according to strategy parameters.

        Args:
            email_dict: Standardized email dictionary from MSGraphClient.
            params: Customer-specific strategy parameters from YAML.

        Returns:
            Extracted record dictionary or None if extraction criteria not met.
        """
        pass
