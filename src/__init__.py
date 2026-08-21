"""
Email Ingestion & Extraction Framework package.
"""

from .ar_collections_pipeline import (
    CollectionRecord,
    JapaneseCurrencyCleaner,
    YamlMappingParser,
)
from .engine import EmailPipelineEngine
from .msgraph_email_core import (
    AttachmentItem,
    EmailFilter,
    EmailMessage,
    HTMLTableExtractor,
    MSGraphEmailClient,
)

__all__ = [
    "AttachmentItem",
    "CollectionRecord",
    "EmailFilter",
    "EmailMessage",
    "EmailPipelineEngine",
    "HTMLTableExtractor",
    "JapaneseCurrencyCleaner",
    "MSGraphEmailClient",
    "YamlMappingParser",
]
