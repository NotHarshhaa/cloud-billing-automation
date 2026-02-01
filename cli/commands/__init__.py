"""
CLI command modules.
"""

# Import all command modules to register them
from . import analyze, budget, alerts, credentials, config, optimize

__all__ = [
    "analyze",
    "budget",
    "alerts", 
    "credentials",
    "config",
    "optimize",
]
