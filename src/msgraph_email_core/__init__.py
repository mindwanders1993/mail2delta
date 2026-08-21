"""
msgraph_email_core
~~~~~~~~~~~~~~~~~~
A generic, platform-agnostic Microsoft Graph API email ingestion library.
Works synchronously across Databricks, Airflow, serverless, and local environments.
"""

from .client import MSGraphEmailClient
from .filters import EmailFilter
from .html_tools import HTMLTableExtractor
from .models import AttachmentItem, EmailMessage

__all__ = [
    "AttachmentItem",
    "EmailFilter",
    "EmailMessage",
    "HTMLTableExtractor",
    "MSGraphEmailClient",
]

__version__ = "0.1.0"
