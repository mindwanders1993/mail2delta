"""
src.connectors
~~~~~~~~~~~~~~
Universal I/O connectors and parsing tools for external systems.
"""

from .ms_graph_client import MSGraphClient
from .html_parser import HTMLParser

__all__ = [
    "MSGraphClient",
    "HTMLParser",
]
