"""
Configuration management for cloud billing automation.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from .exceptions import ConfigurationError


@dataclass
class CloudProviderConfig:
    """Configuration for a specific cloud provider."""
    name: str
    enabled: bool = True
    account_id: Optional[str] = None
    subscription_id: Optional[str] = None
    project_id: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    tags_required: List[str] = field(default_factory=list)
    cost_center_tag: str = "CostCenter"
    environment_tag: str = "Environment"


@dataclass
class BudgetConfig:
    """Budget configuration."""
    monthly_limit: float
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%
    currency: str = "USD"
    alert_emails: List[str] = field(default_factory=list)
    alert_webhooks: List[str] = field(default_factory=list)


@dataclass
class ReportConfig:
    """Report generation configuration."""
    output_dir: str = "reports"
    formats: List[str] = field(default_factory=lambda: ["json", "csv", "html"])
    schedule: str = "daily"  # daily, weekly, monthly
    include_charts: bool = True
    email_reports: bool = False
    email_recipients: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration class."""
    config_file: Optional[str] = None
    debug: bool = False
    log_level: str = "INFO"
    data_retention_days: int = 90
    
    # Provider configurations
    aws: CloudProviderConfig = field(default_factory=lambda: CloudProviderConfig("aws"))
    azure: CloudProviderConfig = field(default_factory=lambda: CloudProviderConfig("azure"))
    gcp: CloudProviderConfig = field(default_factory=lambda: CloudProviderConfig("gcp"))
    
    # Budget and reporting
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    reports: ReportConfig = field(default_factory=ReportConfig)
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            return cls.from_dict(config_data)
        
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()
        
        # Set basic config
        config.debug = config_data.get("debug", False)
        config.log_level = config_data.get("log_level", "INFO")
        config.data_retention_days = config_data.get("data_retention_days", 90)
        
        # Load provider configs
        if "providers" in config_data:
            providers = config_data["providers"]
            
            if "aws" in providers:
                config.aws = CloudProviderConfig(
                    name="aws",
                    enabled=providers["aws"].get("enabled", True),
                    account_id=providers["aws"].get("account_id"),
                    regions=providers["aws"].get("regions", []),
                    tags_required=providers["aws"].get("tags_required", []),
                    cost_center_tag=providers["aws"].get("cost_center_tag", "CostCenter"),
                    environment_tag=providers["aws"].get("environment_tag", "Environment"),
                )
            
            if "azure" in providers:
                config.azure = CloudProviderConfig(
                    name="azure",
                    enabled=providers["azure"].get("enabled", True),
                    subscription_id=providers["azure"].get("subscription_id"),
                    regions=providers["azure"].get("regions", []),
                    tags_required=providers["azure"].get("tags_required", []),
                    cost_center_tag=providers["azure"].get("cost_center_tag", "CostCenter"),
                    environment_tag=providers["azure"].get("environment_tag", "Environment"),
                )
            
            if "gcp" in providers:
                config.gcp = CloudProviderConfig(
                    name="gcp",
                    enabled=providers["gcp"].get("enabled", True),
                    project_id=providers["gcp"].get("project_id"),
                    regions=providers["gcp"].get("regions", []),
                    tags_required=providers["gcp"].get("tags_required", []),
                    cost_center_tag=providers["gcp"].get("cost_center_tag", "CostCenter"),
                    environment_tag=providers["gcp"].get("environment_tag", "Environment"),
                )
        
        # Load budget config
        if "budget" in config_data:
            budget_data = config_data["budget"]
            config.budget = BudgetConfig(
                monthly_limit=budget_data.get("monthly_limit", 1000.0),
                warning_threshold=budget_data.get("warning_threshold", 0.8),
                critical_threshold=budget_data.get("critical_threshold", 0.95),
                currency=budget_data.get("currency", "USD"),
                alert_emails=budget_data.get("alert_emails", []),
                alert_webhooks=budget_data.get("alert_webhooks", []),
            )
        
        # Load report config
        if "reports" in config_data:
            report_data = config_data["reports"]
            config.reports = ReportConfig(
                output_dir=report_data.get("output_dir", "reports"),
                formats=report_data.get("formats", ["json", "csv", "html"]),
                schedule=report_data.get("schedule", "daily"),
                include_charts=report_data.get("include_charts", True),
                email_reports=report_data.get("email_reports", False),
                email_recipients=report_data.get("email_recipients", []),
            )
        
        return config
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Basic config from environment
        config.debug = os.getenv("CBA_DEBUG", "false").lower() == "true"
        config.log_level = os.getenv("CBA_LOG_LEVEL", "INFO")
        config.data_retention_days = int(os.getenv("CBA_DATA_RETENTION_DAYS", "90"))
        
        # Budget from environment
        if os.getenv("CBA_BUDGET_MONTHLY_LIMIT"):
            config.budget.monthly_limit = float(os.getenv("CBA_BUDGET_MONTHLY_LIMIT"))
        if os.getenv("CBA_BUDGET_WARNING_THRESHOLD"):
            config.budget.warning_threshold = float(os.getenv("CBA_BUDGET_WARNING_THRESHOLD"))
        if os.getenv("CBA_BUDGET_CRITICAL_THRESHOLD"):
            config.budget.critical_threshold = float(os.getenv("CBA_BUDGET_CRITICAL_THRESHOLD"))
        
        return config
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.budget.monthly_limit <= 0:
            raise ConfigurationError("Budget monthly limit must be positive")
        
        if not 0 < self.budget.warning_threshold < 1:
            raise ConfigurationError("Budget warning threshold must be between 0 and 1")
        
        if not 0 < self.budget.critical_threshold < 1:
            raise ConfigurationError("Budget critical threshold must be between 0 and 1")
        
        if self.budget.warning_threshold >= self.budget.critical_threshold:
            raise ConfigurationError("Warning threshold must be less than critical threshold")
        
        # Validate enabled providers have required fields
        if self.aws.enabled and not self.aws.account_id:
            raise ConfigurationError("AWS account ID is required when AWS is enabled")
        
        if self.azure.enabled and not self.azure.subscription_id:
            raise ConfigurationError("Azure subscription ID is required when Azure is enabled")
        
        if self.gcp.enabled and not self.gcp.project_id:
            raise ConfigurationError("GCP project ID is required when GCP is enabled")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "debug": self.debug,
            "log_level": self.log_level,
            "data_retention_days": self.data_retention_days,
            "providers": {
                "aws": {
                    "enabled": self.aws.enabled,
                    "account_id": self.aws.account_id,
                    "regions": self.aws.regions,
                    "tags_required": self.aws.tags_required,
                    "cost_center_tag": self.aws.cost_center_tag,
                    "environment_tag": self.aws.environment_tag,
                },
                "azure": {
                    "enabled": self.azure.enabled,
                    "subscription_id": self.azure.subscription_id,
                    "regions": self.azure.regions,
                    "tags_required": self.azure.tags_required,
                    "cost_center_tag": self.azure.cost_center_tag,
                    "environment_tag": self.azure.environment_tag,
                },
                "gcp": {
                    "enabled": self.gcp.enabled,
                    "project_id": self.gcp.project_id,
                    "regions": self.gcp.regions,
                    "tags_required": self.gcp.tags_required,
                    "cost_center_tag": self.aws.cost_center_tag,
                    "environment_tag": self.aws.environment_tag,
                },
            },
            "budget": {
                "monthly_limit": self.budget.monthly_limit,
                "warning_threshold": self.budget.warning_threshold,
                "critical_threshold": self.budget.critical_threshold,
                "currency": self.budget.currency,
                "alert_emails": self.budget.alert_emails,
                "alert_webhooks": self.budget.alert_webhooks,
            },
            "reports": {
                "output_dir": self.reports.output_dir,
                "formats": self.reports.formats,
                "schedule": self.reports.schedule,
                "include_charts": self.reports.include_charts,
                "email_reports": self.reports.email_reports,
                "email_recipients": self.reports.email_recipients,
            },
        }
