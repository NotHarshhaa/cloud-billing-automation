"""
Data collectors for cloud billing information.
"""

from .base import BaseCollector

# Import collectors with error handling
try:
    from .aws_collector import AWSCollector
except ImportError as e:
    AWSCollector = None
    print(f"Warning: AWS collector not available: {e}")

try:
    from .azure_collector import AzureCollector
except ImportError as e:
    AzureCollector = None
    print(f"Warning: Azure collector not available: {e}")

try:
    from .gcp_collector import GCPCollector
except ImportError as e:
    GCPCollector = None
    print(f"Warning: GCP collector not available: {e}")

__all__ = [
    "BaseCollector",
    "AWSCollector", 
    "AzureCollector",
    "GCPCollector",
]
