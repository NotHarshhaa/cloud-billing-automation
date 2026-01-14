"""
Cloud Billing Automation Tool

A DevOps-centric cloud cost governance and automation project built for 
Cloud Engineers and DevOps Engineers to gain visibility, control, and 
automation over cloud billing.
"""

__version__ = "0.1.0"
__author__ = "H A R S H H A A"
__email__ = "contact@example.com"

from .core.config import Config
from .core.credentials import CredentialManager
from .collectors.base import BaseCollector
from .analyzers.cost import CostAnalyzer
from .alerts.budget import BudgetAlertManager
from .reports.generator import ReportGenerator

__all__ = [
    "Config",
    "CredentialManager", 
    "BaseCollector",
    "CostAnalyzer",
    "BudgetAlertManager",
    "ReportGenerator",
]
