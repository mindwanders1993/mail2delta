"""
src.strategies
~~~~~~~~~~~~~~
Pluggable extraction strategies for email parsing.
"""

from .base_strategy import BaseEmailStrategy
from .key_value_strategy import KeyValueStrategy

__all__ = [
    "BaseEmailStrategy",
    "KeyValueStrategy",
]
