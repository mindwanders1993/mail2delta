"""
src.sinks
~~~~~~~~~
Data sinks and storage adapters for Databricks Lakehouse, databases, and warehouses.
"""

from .delta_sink import DeltaSink

__all__ = ["DeltaSink"]
