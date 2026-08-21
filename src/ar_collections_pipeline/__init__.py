"""
ar_collections_pipeline
~~~~~~~~~~~~~~~~~~~~~~~
Declarative Accounts Receivable (AR) email parsing and transformation extension.
"""

from .formatters import JapaneseCurrencyCleaner
from .models import CollectionRecord
from .yaml_mapper import YamlMappingParser

__all__ = [
    "CollectionRecord",
    "JapaneseCurrencyCleaner",
    "YamlMappingParser",
]

__version__ = "0.1.0"
