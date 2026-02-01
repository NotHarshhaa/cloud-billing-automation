"""
Cost analysis modules for cloud billing automation.
"""

from .cost import CostAnalyzer
from .anomaly import AnomalyDetector
from .trend import TrendAnalyzer

# Import forecaster with error handling
try:
    from .forecast import CostForecaster
except ImportError as e:
    CostForecaster = None
    print(f"Warning: CostForecaster not available: {e}")

__all__ = [
    "CostAnalyzer",
    "AnomalyDetector", 
    "TrendAnalyzer",
    "CostForecaster",
]
