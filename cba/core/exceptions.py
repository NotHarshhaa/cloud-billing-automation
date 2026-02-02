"""
Custom exceptions for cloud billing automation.
"""


class CloudBillingError(Exception):
    """Base exception for all cloud billing automation errors."""
    pass


class ConfigurationError(CloudBillingError):
    """Raised when there's an issue with configuration."""
    pass


class CredentialError(CloudBillingError):
    """Raised when there's an issue with credentials."""
    pass


class CollectorError(CloudBillingError):
    """Raised when there's an issue with data collection."""
    pass


class AnalyzerError(CloudBillingError):
    """Raised when there's an issue with cost analysis."""
    pass


class AlertError(CloudBillingError):
    """Raised when there's an issue with alerting."""
    pass


class ReportError(CloudBillingError):
    """Raised when there's an issue with report generation."""
    pass


class ValidationError(CloudBillingError):
    """Raised when data validation fails."""
    pass


class APIError(CloudBillingError):
    """Raised when cloud API calls fail."""
    pass


class BudgetExceededError(CloudBillingError):
    """Raised when budget thresholds are exceeded."""
    pass


class TagComplianceError(CloudBillingError):
    """Raised when tag compliance checks fail."""
    pass
