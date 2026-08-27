"""
src.core
~~~~~~~~
Universal, reusable core modules for email ingestion, table extraction, and Delta Lake storage.
"""

from .ms_graph_client import MSGraphClient
from .delta_sink import DeltaSink
from .currency_cleaner import CurrencyCleaner
from .html_parser import HTMLParser

__all__ = [
    "MSGraphClient",
    "DeltaSink",
    "CurrencyCleaner",
    "HTMLParser",
]
